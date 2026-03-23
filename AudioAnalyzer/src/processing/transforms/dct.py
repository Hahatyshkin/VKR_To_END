"""
DCT: Дискретное косинусное преобразование.

Назначение:
- Частотный анализ с использованием только косинусоид
- Энергетическое сжатие сигнала
- Кодирование восстановленного сигнала в MP3

Теоретические основы:
=====================
DCT (Discrete Cosine Transform) разлагает сигнал на косинусоиды.
В отличие от FFT, DCT работает только с действительными числами
и лучше подходит для сжатия, так как концентрирует энергию
в малом числе коэффициентов.

DCT-II (используемая в JPEG, MP3):
-----------------------------------
X[k] = sum_{n=0}^{N-1} x[n] * cos(pi*k*(2n+1)/(2N))

Это ортонормированное преобразование с хорошими свойствами
энергетической концентрации.

Реализация без SciPy:
---------------------
DCT-II вычисляется через rFFT чётного отражения сигнала:
1. Создаём массив 2N: y = [x, x_reversed]
2. Вычисляем rFFT(y)
3. Берём первые N коэффициентов с фазовым сдвигом
4. Нормируем для ортонормированности

IDCT-III:
---------
Обратное преобразование, парное к DCT-II.
Вычисляется аналогично через irFFT.

Отбор коэффициентов:
--------------------
Аналогично FFT:
- По энергии: сохраняем k% энергии
- Lowpass: сохраняем низкочастотные компоненты

Параметры:
----------
block_size : int
    Размер блока DCT (степень двойки)

select_mode : str
    Режим отбора: 'none', 'energy', 'lowpass'

keep_energy_ratio : float
    Доля энергии для сохранения (режим 'energy')

sequency_keep_ratio : float
    Доля низких частот (режим 'lowpass')

Примеры:
--------
>>> # Идеальная реконструкция
>>> dct_transform_and_mp3("audio.wav", "output/")

>>> # Сжатие с сохранением 70% энергии
>>> dct_transform_and_mp3("audio.wav", "output/",
...     select_mode="energy", keep_energy_ratio=0.7)

Внешние библиотеки:
-------------------
- numpy.fft: для вычисления через rFFT
- logging: диагностические сообщения
"""
from __future__ import annotations

import time
import logging
from typing import Callable, Optional, Tuple

import numpy as np

from .base import (
    BaseTransform,
    load_audio_safe,
    create_ola_window,
    finalize_ola,
    prepare_ola_buffers,
    get_output_path,
    SELECT_MODE_NONE,
    SELECT_MODE_ENERGY,
    SELECT_MODE_LOWPASS,
)
from ..codecs import ensure_ffmpeg_available, encode_pcm_to_mp3
from ..utils import normalize_ratio

logger = logging.getLogger("audio.processing.transforms.dct")


# =============================================================================
# ФУНКЦИИ ПРЕОБРАЗОВАНИЯ (низкий уровень)
# =============================================================================

def dct2(x: np.ndarray) -> np.ndarray:
    """DCT-II (ортонормированная) без SciPy через rFFT чётного отражения.

    Это стандартная DCT, используемая в JPEG и MP3.
    Реализация через rFFT позволяет использовать оптимизированный numpy.

    Параметры:
    ----------
    x : np.ndarray
        Входной массив (действительные значения)

    Возвращает:
    -----------
    np.ndarray
        Коэффициенты DCT-II (float32)

    Алгоритм:
    ---------
    1. Создаём отражённый массив y = [x, x[::-1]]
    2. Вычисляем rFFT(y)
    3. Умножаем на фазовый множитель exp(-j*pi*k/(2N))
    4. Нормируем для ортонормированности

    Примечание:
    -----------
    Коэффициент X[0] (DC) масштабируется отдельно,
    чтобы обеспечить ортонормированность.
    """
    N = int(x.shape[0])
    xr = x.astype(np.float64, copy=False)

    # Чётное отражение
    y = np.empty(2 * N, dtype=np.float64)
    y[:N] = xr
    y[N:] = xr[::-1]

    # FFT отражённого сигнала
    Y = np.fft.rfft(y)

    # Фазовый множитель для DCT-II
    k = np.arange(N, dtype=np.float64)
    W = np.exp(-1j * np.pi * k / (2.0 * N))

    # Берём первые N коэффициентов и применяем фазу
    C = (Y[:N] * W).real

    # Ортонормировка
    C *= np.sqrt(2.0 / N)
    C[0] /= np.sqrt(2.0)  # DC-компонента

    return C.astype(np.float32)


def idct3(X: np.ndarray) -> np.ndarray:
    """IDCT-III (ортонормированная), парная к dct2.

    Восстанавливает сигнал из коэффициентов DCT-II.

    Параметры:
    ----------
    X : np.ndarray
        Коэффициенты DCT-II

    Возвращает:
    -----------
    np.ndarray
        Восстановленный сигнал (float32)

    Алгоритм:
    ---------
    1. Масштабируем DC-коэффициент
    2. Умножаем на обратный фазовый множитель
    3. Дополняем до N+1 элементов
    4. Вычисляем irFFT
    5. Нормируем
    """
    N = int(X.shape[0])
    Xd = X.astype(np.float64, copy=False).copy()

    # Обратное масштабирование DC
    Xd[0] /= np.sqrt(2.0)

    # Фазовый множитель для IDCT-III
    k = np.arange(N, dtype=np.float64)
    W = np.exp(1j * np.pi * k / (2.0 * N))

    # Комплексный вектор для irFFT
    Z = Xd * W
    H = np.zeros(N + 1, dtype=np.complex128)
    H[:N] = Z
    H[N] = 0.0

    # Обратное FFT
    y = np.fft.irfft(H, n=2 * N)

    # Нормировка
    x = y[:N] * np.sqrt(2.0 / N)

    return x.astype(np.float32)


def apply_dct_coefficient_selection(
    coeffs: np.ndarray,
    select_mode: str,
    keep_energy_ratio: float,
    sequency_keep_ratio: float
) -> np.ndarray:
    """Применить отбор коэффициентов DCT.

    Параметры:
    ----------
    coeffs : np.ndarray
        Коэффициенты DCT (действительные)
    select_mode : str
        Режим отбора: 'none', 'energy', 'lowpass'
    keep_energy_ratio : float
        Доля энергии для сохранения (режим 'energy')
    sequency_keep_ratio : float
        Доля низких частот (режим 'lowpass')

    Возвращает:
    -----------
    np.ndarray
        Коэффициенты после отбора
    """
    if select_mode == SELECT_MODE_NONE:
        return coeffs

    if select_mode == SELECT_MODE_ENERGY and keep_energy_ratio < 1.0:
        # Энергия = коэффициент^2 (для действительных чисел)
        magsq = coeffs * coeffs
        order = np.argsort(magsq)[::-1]
        cumsum = np.cumsum(magsq[order])
        total_e = cumsum[-1] + 1e-12
        need = keep_energy_ratio * total_e
        keep_n = int(np.searchsorted(cumsum, need, side="left")) + 1

        keep_idx = order[:keep_n]
        mask = np.zeros_like(coeffs, dtype=bool)
        mask[keep_idx] = True
        mask[0] = True  # DC-компонента всегда сохраняется

        return np.where(mask, coeffs, 0.0)

    elif select_mode == SELECT_MODE_LOWPASS and sequency_keep_ratio < 1.0:
        k_lp = max(1, int(sequency_keep_ratio * len(coeffs)))
        mask = np.zeros_like(coeffs, dtype=bool)
        mask[:k_lp] = True
        return np.where(mask, coeffs, 0.0)

    return coeffs


# =============================================================================
# КЛАСС ТРАНСФОРМАЦИИ
# =============================================================================

class DCTTransform(BaseTransform):
    """DCT-трансформация с OLA и отбором коэффициентов.

    Выполняет блочную обработку DCT-II/IDCT-III с перекрытием-сложением.

    Атрибуты:
    ---------
    NAME : str
        Имя метода для логирования
    DESCRIPTION : str
        Краткое описание
    FILE_SUFFIX : str
        Суффикс выходного файла ('dct')

    Пример:
    -------
    >>> transform = DCTTransform(
    ...     block_size=2048,
    ...     select_mode="energy",
    ...     keep_energy_ratio=0.8
    ... )
    >>> out_path, time_sec = transform.process("audio.wav", "output/")
    """

    NAME = "DCT"
    DESCRIPTION = "Дискретное косинусное преобразование"
    FILE_SUFFIX = "dct"

    def __init__(
        self,
        block_size: int = 2048,
        bitrate: str = "192k",
        select_mode: str = SELECT_MODE_NONE,
        keep_energy_ratio: float = 1.0,
        sequency_keep_ratio: float = 1.0,
    ):
        """Инициализация DCT-трансформации.

        Параметры:
        ----------
        block_size : int
            Размер блока DCT (степень двойки)
        bitrate : str
            Битрейт MP3
        select_mode : str
            Режим отбора: 'none', 'energy', 'lowpass'
        keep_energy_ratio : float
            Доля энергии для сохранения
        sequency_keep_ratio : float
            Доля низких частот
        """
        super().__init__(
            block_size=block_size,
            bitrate=bitrate,
            select_mode=select_mode,
            keep_energy_ratio=keep_energy_ratio,
            sequency_keep_ratio=sequency_keep_ratio,
        )

    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """Применить DCT к одному блоку.

        Параметры:
        ----------
        block : np.ndarray
            Входной блок (умноженный на окно)

        Возвращает:
        -----------
        np.ndarray
            Восстановленный блок
        """
        # Прямое DCT
        C = dct2(block)

        # Отбор коэффициентов
        C = apply_dct_coefficient_selection(
            C,
            self.select_mode,
            self.keep_energy_ratio,
            self.sequency_keep_ratio,
        )

        # Обратное DCT
        return idct3(C)

    def process(
        self,
        wav_path: str,
        out_dir: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Полный пайплайн DCT обработки.

        Параметры:
        ----------
        wav_path : str
            Путь к исходному аудиофайлу
        out_dir : str
            Директория для сохранения MP3
        progress_cb : callable, optional
            Колбэк прогресса

        Возвращает:
        -----------
        Tuple[str, float]
            (путь к MP3, время обработки в секундах)
        """
        t0 = time.perf_counter()
        self.log_start(
            wav_path,
            block_size=self.block_size,
            mode=self.select_mode,
            keep_energy=self.keep_energy_ratio,
            seq_keep=self.sequency_keep_ratio,
        )
        ensure_ffmpeg_available()

        if progress_cb:
            progress_cb(0.0, "DCT: декодирование входа")

        # Загрузка аудио
        x, sr = load_audio_safe(wav_path)
        n = len(x)
        N = self.block_size

        # Подготовка OLA
        win = create_ola_window(N)
        frames, hop, total_len, y_accum, w_accum = prepare_ola_buffers(n, N)

        # Дополнение сигнала
        pad = total_len - n
        x_padded = np.pad(x, (0, pad), mode="constant")

        # Обработка блоков
        for fi in range(frames):
            i0 = fi * hop
            blk = x_padded[i0 : i0 + N]
            xb = blk * win

            # Проверка: нужно ли преобразование?
            identity = (
                self.select_mode == SELECT_MODE_NONE
                and self.keep_energy_ratio >= 1.0
                and self.sequency_keep_ratio >= 1.0
            )

            if identity:
                # Идеальная реконструкция без DCT
                rec = (xb * win).astype(np.float32)
            else:
                # DCT трансформация
                rec = self.transform_block(xb) * win

            # OLA накопление
            y_accum[i0 : i0 + N] += rec
            w_accum[i0 : i0 + N] += win * win

            if progress_cb:
                progress_cb(
                    min(0.95, 0.1 + 0.8 * (fi + 1) / frames),
                    f"DCT: блок {fi+1}/{frames}"
                )

        # Финализация OLA
        y = finalize_ola(y_accum, w_accum, n)
        out_mp3 = self.get_output_path(wav_path, out_dir)

        # Кодирование в MP3
        if progress_cb:
            progress_cb(0.97, "DCT: кодирование MP3")
        encode_pcm_to_mp3(y, sr, out_mp3, self.bitrate, profile="vbr")

        dt = time.perf_counter() - t0
        if progress_cb:
            progress_cb(1.0, "DCT: готово")

        self.log_done(out_mp3, dt)
        return out_mp3, dt


# =============================================================================
# ФУНКЦИЯ-ОБЁРТКА (обратная совместимость)
# =============================================================================

def dct_transform_and_mp3(
    wav_path: str,
    out_dir: str,
    *,
    block_size: int = 2048,
    bitrate: str = "192k",
    select_mode: str = "none",
    keep_energy_ratio: float = 1.0,
    sequency_keep_ratio: float = 1.0,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> Tuple[str, float]:
    """Блочная DCT-II/IDCT-III с OLA и отбором коэффициентов → MP3.

    Функция-обёртка над DCTTransform для обратной совместимости.

    Параметры:
    ----------
    wav_path : str
        Входной WAV/аудиофайл
    out_dir : str
        Каталог для сохранения MP3
    block_size : int
        Длина блока (степень двойки)
    bitrate : str
        Битрейт MP3
    select_mode : str
        'none' | 'energy' | 'lowpass'
    keep_energy_ratio : float
        Доля энергии для сохранения, 0..1
    sequency_keep_ratio : float
        Доля низких частот, 0..1
    progress_cb : callable
        Колбэк прогресса

    Возвращает:
    -----------
    Tuple[str, float]
        (путь к MP3, время в секундах)
    """
    transform = DCTTransform(
        block_size=block_size,
        bitrate=bitrate,
        select_mode=select_mode,
        keep_energy_ratio=keep_energy_ratio,
        sequency_keep_ratio=sequency_keep_ratio,
    )
    return transform.process(wav_path, out_dir, progress_cb)


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    "DCTTransform",
    "dct_transform_and_mp3",
    "dct2",
    "idct3",
    "apply_dct_coefficient_selection",
]
