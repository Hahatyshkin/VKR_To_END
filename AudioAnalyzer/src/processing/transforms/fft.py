"""
FFT: Быстрое преобразование Фурье.

Назначение:
- Частотный анализ и обработка аудиосигналов
- Отбор коэффициентов по энергии или частоте
- Кодирование восстановленного сигнала в MP3

Теоретические основы:
=====================
Преобразование Фурье разлагает сигнал на синусоидальные компоненты.
FFT (Fast Fourier Transform) — быстрый алгоритм вычисления DFT
за O(N log N) операций вместо O(N^2).

rFFT (Real FFT):
----------------
Для действительных сигналов используется rFFT, который вычисляет
только неотрицательные частоты (N/2+1 комплексных коэффициентов
вместо N). Это экономит память и время вычисления.

Формулы:
--------
X[k] = sum_{n=0}^{N-1} x[n] * exp(-j*2*pi*k*n/N)

x[n] = (1/N) * sum_{k=0}^{N-1} X[k] * exp(j*2*pi*k*n/N)

Отбор коэффициентов:
--------------------
1. По энергии (energy): сохраняем k% энергии сигнала
   - Сортируем коэффициенты по |X[k]|^2
   - Оставляем минимальное число, дающее нужную долю энергии

2. Lowpass: сохраняем низкие частоты
   - Обнуляем коэффициенты выше заданной частоты среза
   - Аналог ФНЧ в частотной области

Параметры:
----------
block_size : int
    Размер блока FFT (степень двойки). Типичные значения:
    - 1024: высокое временное разрешение, низкое частотное
    - 2048: баланс (по умолчанию)
    - 4096: высокое частотное разрешение, низкое временное

select_mode : str
    Режим отбора коэффициентов:
    - 'none': без отбора (идеальная реконструкция)
    - 'energy': сохранение доли энергии (сжатие)
    - 'lowpass': сохранение низких частот (фильтрация)

keep_energy_ratio : float
    Доля энергии для сохранения (режим 'energy'), 0.0-1.0

sequency_keep_ratio : float
    Доля низких частот (режим 'lowpass'), 0.0-1.0

Примеры использования:
----------------------
>>> # Идеальная реконструкция
>>> fft_transform_and_mp3("audio.wav", "output/")

>>> # Сжатие с сохранением 80% энергии
>>> fft_transform_and_mp3("audio.wav", "output/",
...     select_mode="energy", keep_energy_ratio=0.8)

>>> # Lowpass фильтрация (первые 50% частот)
>>> fft_transform_and_mp3("audio.wav", "output/",
...     select_mode="lowpass", sequency_keep_ratio=0.5)

Внешние библиотеки:
-------------------
- numpy.fft: реализация FFT (оптимизирована на C/Fortran)
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
    select_coefficients_energy,
    select_coefficients_lowpass,
    get_output_path,
    SELECT_MODE_NONE,
    SELECT_MODE_ENERGY,
    SELECT_MODE_LOWPASS,
)
from ..codecs import ensure_ffmpeg_available, encode_pcm_to_mp3
from ..utils import normalize_ratio

logger = logging.getLogger("audio.processing.transforms.fft")


# =============================================================================
# ФУНКЦИИ ПРЕОБРАЗОВАНИЯ (низкий уровень)
# =============================================================================

def fft_forward(block: np.ndarray) -> np.ndarray:
    """Прямое rFFT преобразование.

    Вычисляет real FFT для действительного сигнала.
    Возвращает N/2+1 комплексных коэффициентов.

    Параметры:
    ----------
    block : np.ndarray
        Входной блок сигнала (действительные значения)

    Возвращает:
    -----------
    np.ndarray
        Комплексные коэффициенты FFT (N/2+1 элементов)
    """
    return np.fft.rfft(block)


def fft_inverse(coeffs: np.ndarray, n: int) -> np.ndarray:
    """Обратное irFFT преобразование.

    Восстанавливает действительный сигнал из коэффициентов FFT.

    Параметры:
    ----------
    coeffs : np.ndarray
        Комплексные коэффициенты FFT (N/2+1 элементов)
    n : int
        Длина восстанавливаемого сигнала

    Возвращает:
    -----------
    np.ndarray
        Восстановленный действительный сигнал длины n
    """
    return np.fft.irfft(coeffs, n=n).astype(np.float32)


def apply_fft_coefficient_selection(
    coeffs: np.ndarray,
    select_mode: str,
    keep_energy_ratio: float,
    sequency_keep_ratio: float
) -> np.ndarray:
    """Применить отбор коэффициентов FFT.

    Параметры:
    ----------
    coeffs : np.ndarray
        Комплексные коэффициенты FFT
    select_mode : str
        Режим отбора: 'none', 'energy', 'lowpass'
    keep_energy_ratio : float
        Доля энергии для сохранения (режим 'energy')
    sequency_keep_ratio : float
        Доля низких частот (режим 'lowpass')

    Возвращает:
    -----------
    np.ndarray
        Коэффициенты после отбора (с обнулёнными элементами)
    """
    if select_mode == SELECT_MODE_NONE:
        return coeffs

    if select_mode == SELECT_MODE_ENERGY:
        # Для комплексных чисел энергия = |X|^2
        magsq = coeffs.real * coeffs.real + coeffs.imag * coeffs.imag
        order = np.argsort(magsq)[::-1]
        cumsum = np.cumsum(magsq[order])
        total_e = cumsum[-1] + 1e-12
        need = keep_energy_ratio * total_e
        keep_n = int(np.searchsorted(cumsum, need, side="left")) + 1

        keep_idx = order[:keep_n]
        mask = np.zeros_like(coeffs, dtype=bool)
        mask[keep_idx] = True
        mask[0] = True  # DC-компонента всегда сохраняется

        return np.where(mask, coeffs, 0.0+0.0j)

    elif select_mode == SELECT_MODE_LOWPASS:
        k_lp = max(1, int(sequency_keep_ratio * len(coeffs)))
        mask = np.zeros_like(coeffs, dtype=bool)
        mask[:k_lp] = True
        return np.where(mask, coeffs, 0.0+0.0j)

    return coeffs


# =============================================================================
# КЛАСС ТРАНСФОРМАЦИИ
# =============================================================================

class FFTTransform(BaseTransform):
    """FFT-трансформация с OLA и отбором коэффициентов.

    Выполняет блочную обработку с перекрытием-сложением (OLA)
    и опциональным отбором коэффициентов по энергии или частоте.

    Атрибуты:
    ---------
    NAME : str
        Имя метода для логирования
    DESCRIPTION : str
        Краткое описание
    FILE_SUFFIX : str
        Суффикс выходного файла ('fft')

    Пример:
    -------
    >>> transform = FFTTransform(
    ...     block_size=2048,
    ...     select_mode="energy",
    ...     keep_energy_ratio=0.8
    ... )
    >>> out_path, time_sec = transform.process("audio.wav", "output/")
    """

    NAME = "FFT"
    DESCRIPTION = "Быстрое преобразование Фурье"
    FILE_SUFFIX = "fft"

    def __init__(
        self,
        block_size: int = 2048,
        bitrate: str = "192k",
        select_mode: str = SELECT_MODE_NONE,
        keep_energy_ratio: float = 1.0,
        sequency_keep_ratio: float = 1.0,
    ):
        """Инициализация FFT-трансформации.

        Параметры:
        ----------
        block_size : int
            Размер блока FFT (степень двойки)
        bitrate : str
            Битрейт MP3
        select_mode : str
            Режим отбора: 'none', 'energy', 'lowpass'
        keep_energy_ratio : float
            Доля энергии для сохранения (режим 'energy')
        sequency_keep_ratio : float
            Доля низких частот (режим 'lowpass')
        """
        super().__init__(
            block_size=block_size,
            bitrate=bitrate,
            select_mode=select_mode,
            keep_energy_ratio=keep_energy_ratio,
            sequency_keep_ratio=sequency_keep_ratio,
        )

    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """Применить FFT к одному блоку.

        Параметры:
        ----------
        block : np.ndarray
            Входной блок (умноженный на окно)

        Возвращает:
        -----------
        np.ndarray
            Восстановленный блок
        """
        # Прямое FFT
        coeffs = fft_forward(block)

        # Отбор коэффициентов
        coeffs = apply_fft_coefficient_selection(
            coeffs,
            self.select_mode,
            self.keep_energy_ratio,
            self.sequency_keep_ratio,
        )

        # Обратное FFT
        return fft_inverse(coeffs, len(block))

    def process(
        self,
        wav_path: str,
        out_dir: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Полный пайплайн FFT обработки.

        Параметры:
        ----------
        wav_path : str
            Путь к исходному аудиофайлу
        out_dir : str
            Директория для сохранения MP3
        progress_cb : callable, optional
            Колбэк прогресса progress_cb(frac, msg)

        Возвращает:
        -----------
        Tuple[str, float]
            (путь к MP3, время обработки в секундах)
        """
        t0_total = time.perf_counter()
        self.log_start(
            wav_path,
            block_size=self.block_size,
            mode=self.select_mode,
            keep_energy=self.keep_energy_ratio,
            seq_keep=self.sequency_keep_ratio,
        )
        ensure_ffmpeg_available()

        if progress_cb:
            progress_cb(0.0, "FFT: декодирование входа")

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

            # FFT трансформация
            rec = self.transform_block(xb) * win

            # OLA накопление
            y_accum[i0 : i0 + N] += rec
            w_accum[i0 : i0 + N] += win * win

            if progress_cb:
                progress_cb(
                    min(0.95, 0.1 + 0.8 * (fi + 1) / frames),
                    f"FFT: блок {fi+1}/{frames}"
                )

        # Финализация OLA
        y = finalize_ola(y_accum, w_accum, n)
        out_mp3 = self.get_output_path(wav_path, out_dir)

        # Кодирование в MP3
        if progress_cb:
            progress_cb(0.97, "FFT: кодирование MP3")
        encode_pcm_to_mp3(y, sr, out_mp3, self.bitrate, profile="vbr")

        total_dt = time.perf_counter() - t0_total
        if progress_cb:
            progress_cb(1.0, "FFT: готово")

        self.log_done(out_mp3, total_dt)
        return out_mp3, total_dt


# =============================================================================
# ФУНКЦИЯ-ОБЁРТКА (обратная совместимость)
# =============================================================================

def fft_transform_and_mp3(
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
    """Блочная rFFT/iFFT с OLA и отбором коэффициентов → MP3.

    Функция-обёртка над FFTTransform для обратной совместимости.

    Параметры:
    ----------
    wav_path : str
        Входной WAV/аудиофайл
    out_dir : str
        Каталог для сохранения MP3
    block_size : int
        Длина блока (2^n), типичные значения 1024-4096
    bitrate : str
        Битрейт MP3 (например, '192k')
    select_mode : str
        'none' | 'energy' | 'lowpass'
    keep_energy_ratio : float
        Доля энергии для сохранения (mode='energy'), 0..1
    sequency_keep_ratio : float
        Доля низких частот (mode='lowpass'), 0..1
    progress_cb : callable
        Колбэк прогресса progress_cb(frac, msg)

    Возвращает:
    -----------
    Tuple[str, float]
        (путь к MP3, общее время в секундах)

    Пример:
    -------
    >>> out_path, time_sec = fft_transform_and_mp3(
    ...     "audio.wav", "output/",
    ...     select_mode="energy",
    ...     keep_energy_ratio=0.8
    ... )
    """
    transform = FFTTransform(
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
    "FFTTransform",
    "fft_transform_and_mp3",
    "fft_forward",
    "fft_inverse",
    "apply_fft_coefficient_selection",
]
