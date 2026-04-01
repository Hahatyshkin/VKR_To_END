"""
FWHT: Быстрое преобразование Уолша-Адамара.

Назначение:
- Частотный анализ с использованием прямоугольных волн (функций Уолша)
- Эффективное вычисление (только сложения/вычитания)
- Кодирование восстановленного сигнала в MP3

Теоретические основы:
=====================
FWHT (Fast Walsh-Hadamard Transform) — аналог FFT для функций Уолша.
Функции Уолша — это прямоугольные волны, принимающие значения ±1.

Преимущества FWHT:
------------------
1. Вычислительная простота: только сложения/вычитания, нет умножений
2. O(N log N) операций (как у FFT)
3. Хорошо подходит для бинарных/ступенчатых сигналов
4. Ортонормированное преобразование (энергия сохраняется)

Функции Уолша:
--------------
WAL(k, t) — функция Уолша порядка k:
- Принимает значения +1 или -1
- k — номер функции в последовательности Уолша (sequency)
- Sequency — число пересечений нуля (аналог частоты для синусоид)

Матрица Адамара:
----------------
H = [1  1]   H_2n = [H_n  H_n ]
    [1 -1]          [H_n -H_n ]

Преобразование: y = H_n @ x / sqrt(n)

Алгоритм бабочки:
-----------------
FWHT вычисляется через структуру "бабочка", аналогичную FFT:
На каждом уровне h = 1, 2, 4, ..., N/2:
    a = x[i]
    b = x[i+h]
    x[i]   = a + b
    x[i+h] = a - b

Отбор коэффициентов:
--------------------
1. По энергии: сохраняем k% энергии (аналогично FFT)
2. Lowpass (sequency): сохраняем низкие sequency коэффициенты
3. Top-k: сохраняем k наибольших по модулю коэффициентов

Производительность:
-------------------
Теоретически FWHT должен быть быстрее FFT (нет умножений),
но numpy FFT оптимизирован на уровне C/Fortran.
Для достижения сопоставимой скорости используется векторизация.

Параметры:
----------
block_size : int
    Размер блока (степень двойки)

select_mode : str
    Режим отбора: 'none', 'energy', 'lowpass'

keep_energy_ratio : float
    Доля энергии для сохранения

sequency_keep_ratio : float
    Доля низких sequency коэффициентов

Примеры:
--------
>>> # Идеальная реконструкция
>>> fwht_transform_and_mp3("audio.wav", "output/")

>>> # Сжатие с сохранением 80% энергии
>>> fwht_transform_and_mp3("audio.wav", "output/",
...     select_mode="energy", keep_energy_ratio=0.8)

Внешние библиотеки:
-------------------
- numpy: векторизованные операции
- math: нормировка sqrt(N)
- logging: диагностические сообщения
"""
from __future__ import annotations

import math
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
from ..utils import normalize_ratio, is_power_of_two

logger = logging.getLogger("audio.processing.transforms.fwht")


# =============================================================================
# ФУНКЦИИ ПРЕОБРАЗОВАНИЯ (низкий уровень)
# =============================================================================

def fwht(x: np.ndarray) -> np.ndarray:
    """Векторизованное быстрое преобразование Уолша–Адамара (FWHT).

    Алгоритм использует бабочку Уолша-Адамара с O(N log N) операциями.
    В отличие от FFT, FWHT использует только сложения и вычитания.

    Параметры:
    ----------
    x : np.ndarray
        Входной массив (длина должна быть степенью двойки)

    Возвращает:
    -----------
    np.ndarray
        Коэффициенты Уолша-Адамара (без нормировки)

    Алгоритм:
    ---------
    На каждом уровне h = 1, 2, 4, ..., N/2:
        y = reshape(y, (N//(2h), 2, h))
        a = y[:, 0, :]  # первые элементы пар
        b = y[:, 1, :]  # вторые элементы пар
        y[:, 0, :] = a + b  # суммы
        y[:, 1, :] = a - b  # разности

    Примечание:
    -----------
    Векторизованная реализация в ~10-100 раз быстрее
    циклической версии на Python.
    """
    n = x.shape[0]
    if not is_power_of_two(n):
        raise ValueError(f"Длина FWHT должна быть степенью двойки, получено: {n}")

    y = np.asarray(x, dtype=np.float64).copy()

    # Векторизованный алгоритм бабочек
    h = 1
    while h < n:
        # Reshape для векторизации: (n // (2*h), 2, h)
        y = y.reshape(-1, 2, h)
        a = y[:, 0, :].copy()  # первые элементы каждой пары
        b = y[:, 1, :].copy()  # вторые элементы каждой пары
        y[:, 0, :] = a + b     # суммы (верхняя половина бабочки)
        y[:, 1, :] = a - b     # разности (нижняя половина бабочки)
        y = y.reshape(-1)      # обратно в плоский массив
        h *= 2

    return y.astype(np.float32)


def ifwht(x: np.ndarray) -> np.ndarray:
    """Обратное FWHT в небезопасной нормировке: повторный FWHT и деление на N.

    Параметры:
    ----------
    x : np.ndarray
        Коэффициенты FWHT

    Возвращает:
    -----------
    np.ndarray
        Восстановленный сигнал
    """
    n = x.shape[0]
    return fwht(x) / n


def fwht_ortho(x: np.ndarray) -> np.ndarray:
    """Ортонормированное FWHT (деление на sqrt(N)).

    При ортонормированном преобразовании:
    - Энергия сохраняется: ||y||^2 = ||x||^2
    - Обратное преобразование идентично прямому

    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал

    Возвращает:
    -----------
    np.ndarray
        Ортонормированные коэффициенты FWHT
    """
    n = x.shape[0]
    return fwht(x) / math.sqrt(n)


def ifwht_ortho(x: np.ndarray) -> np.ndarray:
    """Обратное ортонормированное FWHT.

    Для ортонормированного преобразования обратное
    идентично прямому (self-inverse property).

    Параметры:
    ----------
    x : np.ndarray
        Коэффициенты FWHT

    Возвращает:
    -----------
    np.ndarray
        Восстановленный сигнал
    """
    n = x.shape[0]
    return fwht(x) / math.sqrt(n)


def apply_fwht_coefficient_selection(
    coeffs: np.ndarray,
    select_mode: str,
    keep_energy_ratio: float,
    sequency_keep_ratio: float,
    keep_ratio: Optional[float] = None
) -> np.ndarray:
    """Применить отбор коэффициентов FWHT.

    Параметры:
    ----------
    coeffs : np.ndarray
        Коэффициенты FWHT
    select_mode : str
        Режим отбора: 'none', 'energy', 'lowpass'
    keep_energy_ratio : float
        Доля энергии для сохранения
    sequency_keep_ratio : float
        Доля низких sequency коэффициентов
    keep_ratio : float, optional
        Доля top-k коэффициентов (устаревший параметр)

    Возвращает:
    -----------
    np.ndarray
        Коэффициенты после отбора
    """
    # Устаревший режим top-k
    if keep_ratio is not None and 0.0 < keep_ratio < 1.0:
        N = len(coeffs)
        k = max(1, int(keep_ratio * N))
        thresh = np.partition(np.abs(coeffs), -k)[-k]
        return coeffs * (np.abs(coeffs) >= thresh)

    if select_mode == SELECT_MODE_NONE:
        return coeffs

    if select_mode == SELECT_MODE_ENERGY and keep_energy_ratio < 1.0:
        magsq = coeffs * coeffs
        order = np.argsort(magsq)[::-1]
        cumsum = np.cumsum(magsq[order])
        total_e = cumsum[-1] + 1e-12
        need = keep_energy_ratio * total_e
        keep_n = int(np.searchsorted(cumsum, need, side="left")) + 1

        keep_idx = order[:keep_n]
        mask = np.zeros_like(coeffs, dtype=bool)
        mask[keep_idx] = True
        mask[0] = True  # DC-компонента

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

class FWHTTransform(BaseTransform):
    """FWHT-трансформация с OLA и отбором коэффициентов.

    Атрибуты:
    ---------
    NAME : str
        Имя метода
    DESCRIPTION : str
        Краткое описание
    FILE_SUFFIX : str
        Суффикс файла ('fwht')

    Пример:
    -------
    >>> transform = FWHTTransform(
    ...     block_size=2048,
    ...     select_mode="energy",
    ...     keep_energy_ratio=0.8
    ... )
    >>> out_path, time_sec = transform.process("audio.wav", "output/")
    """

    NAME = "FWHT"
    DESCRIPTION = "Быстрое преобразование Уолша-Адамара"
    FILE_SUFFIX = "fwht"

    def __init__(
        self,
        block_size: int = 2048,
        bitrate: str = "192k",
        select_mode: str = SELECT_MODE_NONE,
        keep_energy_ratio: float = 1.0,
        sequency_keep_ratio: float = 1.0,
        keep_ratio: float = 0.0,
    ):
        """Инициализация FWHT-трансформации.

        Параметры:
        ----------
        block_size : int
            Размер блока (степень двойки)
        bitrate : str
            Битрейт MP3
        select_mode : str
            Режим отбора: 'none', 'energy', 'lowpass'
        keep_energy_ratio : float
            Доля энергии для сохранения
        sequency_keep_ratio : float
            Доля низких sequency коэффициентов
        keep_ratio : float
            Доля top-k (устаревший параметр)
        """
        super().__init__(
            block_size=block_size,
            bitrate=bitrate,
            select_mode=select_mode,
            keep_energy_ratio=keep_energy_ratio,
            sequency_keep_ratio=sequency_keep_ratio,
        )

        # Устаревший параметр keep_ratio
        try:
            self.keep_ratio = float(max(0.0, min(1.0, keep_ratio or 0.0)))
        except (TypeError, ValueError) as e:
            logger.debug("keep_ratio_parse_error: %s, using default 0.0", e)
            self.keep_ratio = 0.0

    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """Применить FWHT к одному блоку.

        Параметры:
        ----------
        block : np.ndarray
            Входной блок

        Возвращает:
        -----------
        np.ndarray
            Восстановленный блок
        """
        # Прямое FWHT
        coeffs = fwht_ortho(block)

        # Отбор коэффициентов
        coeffs = apply_fwht_coefficient_selection(
            coeffs,
            self.select_mode,
            self.keep_energy_ratio,
            self.sequency_keep_ratio,
            self.keep_ratio,
        )

        # Обратное FWHT
        return ifwht_ortho(coeffs)

    def process(
        self,
        wav_path: str,
        out_dir: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Полный пайплайн FWHT обработки.

        Параметры:
        ----------
        wav_path : str
            Путь к исходному файлу
        out_dir : str
            Директория для сохранения
        progress_cb : callable, optional
            Колбэк прогресса

        Возвращает:
        -----------
        Tuple[str, float]
            (путь к MP3, время в секундах)
        """
        t_total0 = time.perf_counter()
        self.log_start(
            wav_path,
            block_size=self.block_size,
            mode=self.select_mode,
            keep_ratio=self.keep_ratio,
            keep_energy=self.keep_energy_ratio,
            seq_keep=self.sequency_keep_ratio,
        )
        ensure_ffmpeg_available()

        if progress_cb:
            progress_cb(0.0, "FWHT: загрузка WAV")
            progress_cb(0.02, "FWHT: декодирование входа")

        # Загрузка аудио
        t_dec0 = time.perf_counter()
        x, sr = load_audio_safe(wav_path)
        t_dec = time.perf_counter() - t_dec0

        n = len(x)
        N = self.block_size

        # Подготовка OLA
        win = create_ola_window(N)
        frames, hop, total_len, y_accum, w_accum = prepare_ola_buffers(n, N)

        # Дополнение сигнала
        pad = total_len - n
        x_padded = np.pad(x, (0, pad), mode="constant")

        # Предварительные вычисления для режимов отбора
        use_topk = self.keep_ratio is not None and 0.0 < self.keep_ratio < 1.0

        # Обработка блоков
        t_proc0 = time.perf_counter()
        for fi in range(frames):
            i = fi * hop
            blk = x_padded[i : i + N]
            blk_w = blk * win

            # FWHT трансформация
            rec = self.transform_block(blk_w) * win

            # OLA накопление
            y_accum[i : i + N] += rec
            w_accum[i : i + N] += win * win

            if progress_cb:
                progress_cb(
                    min(0.95, 0.1 + 0.8 * (fi + 1) / frames),
                    f"FWHT: блок {fi+1}/{frames}"
                )

        # Финализация OLA
        y = finalize_ola(y_accum, w_accum, n)
        t_proc = time.perf_counter() - t_proc0

        out_mp3 = self.get_output_path(wav_path, out_dir)

        # Кодирование в MP3
        if progress_cb:
            progress_cb(0.97, "FWHT: кодирование MP3")

        t_enc0 = time.perf_counter()
        encode_pcm_to_mp3(y, sr, out_mp3, self.bitrate, profile="vbr")
        t_enc = time.perf_counter() - t_enc0

        if progress_cb:
            progress_cb(1.0, "FWHT: готово")

        total_dt = time.perf_counter() - t_total0
        logger.info(
            f"fwht_transform_and_mp3 done out={out_mp3} dt={total_dt:.3f} "
            f"t_decode={t_dec:.3f} t_process={t_proc:.3f} t_encode={t_enc:.3f}"
        )

        return out_mp3, total_dt


# =============================================================================
# ФУНКЦИЯ OLA (для использования без MP3 кодирования)
# =============================================================================

def fwht_ola(
    x: np.ndarray,
    *,
    block_size: int = 2048,
    window: Optional[np.ndarray] = None,
    select_mode: str = SELECT_MODE_NONE,
    keep_energy_ratio: float = 1.0,
    sequency_keep_ratio: float = 1.0,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> np.ndarray:
    """Блочная FWHT-обработка с OLA без кодирования в MP3.

    Полезна для промежуточной обработки или анализа.

    Параметры:
    ----------
    x : np.ndarray
        Входной PCM сигнал (float32, [-1, 1])
    block_size : int
        Размер блока (степень двойки)
    window : np.ndarray, optional
        Окно анализа (по умолчанию sqrt-Hann)
    select_mode : str
        Режим отбора: 'none', 'energy', 'lowpass'
    keep_energy_ratio : float
        Доля энергии
    sequency_keep_ratio : float
        Доля низких sequency
    progress_cb : callable
        Колбэк прогресса

    Возвращает:
    -----------
    np.ndarray
        Обработанный сигнал той же длины
    """
    N = int(block_size)
    if not is_power_of_two(N):
        raise ValueError("block_size должен быть степенью двойки")

    hop = N // 2  # 50% перекрытие

    # Окно
    if window is None:
        window = create_ola_window(N)
    elif len(window) != N:
        raise ValueError("длина окна должна совпадать с block_size")

    n = len(x)
    frames, _, total_len, y_accum, w_accum = prepare_ola_buffers(n, N)

    # Дополнение
    pad = total_len - n
    x_padded = np.pad(x, (0, pad), mode="constant")

    for fi in range(frames):
        i = fi * hop
        blk = x_padded[i : i + N]

        # FWHT трансформация
        blk_w = blk * window
        coeffs = fwht_ortho(blk_w)

        # Отбор
        coeffs = apply_fwht_coefficient_selection(
            coeffs, select_mode, keep_energy_ratio, sequency_keep_ratio
        )

        rec = ifwht_ortho(coeffs) * window

        # OLA
        y_accum[i : i + N] += rec
        w_accum[i : i + N] += window * window

        if progress_cb:
            progress_cb(min(0.95, (fi + 1) / frames), f"FWHT: блок {fi+1}/{frames}")

    # Нормировка
    y = np.divide(y_accum, np.maximum(w_accum, 1e-8))[:n]

    # Защита от клиппинга
    peak = float(np.max(np.abs(y)) + 1e-9)
    if peak > 1.0:
        y = y / peak

    if progress_cb:
        progress_cb(1.0, "FWHT: готово")

    logger.debug("fwht_ola done n=%d N=%d frames=%d", n, N, frames)
    return y


# =============================================================================
# ФУНКЦИЯ-ОБЁРТКА (обратная совместимость)
# =============================================================================

def fwht_transform_and_mp3(
    wav_path: str,
    out_dir: str,
    block_size: int = 2048,
    keep_ratio: float = 0.0,
    bitrate: str = "192k",
    progress_cb: Optional[Callable[[float, str], None]] = None,
    keep_energy_ratio: float = 1.0,
    select_mode: str = "none",
    sequency_keep_ratio: float = 1.0,
) -> Tuple[str, float]:
    """FWHT → MP3 с блочной OLA.

    Функция-обёртка над FWHTTransform для обратной совместимости.

    Параметры:
    ----------
    wav_path : str
        Путь к исходному файлу
    out_dir : str
        Директория для вывода
    block_size : int
        Размер блока (степень двойки)
    keep_ratio : float
        Доля коэффициентов top-k (устаревший)
    bitrate : str
        Битрейт MP3
    progress_cb : callable
        Колбэк прогресса
    keep_energy_ratio : float
        Доля энергии (mode='energy')
    select_mode : str
        'none' | 'energy' | 'lowpass'
    sequency_keep_ratio : float
        Доля низких sequency (mode='lowpass')

    Возвращает:
    -----------
    Tuple[str, float]
        (путь к MP3, время в секундах)
    """
    transform = FWHTTransform(
        block_size=block_size,
        bitrate=bitrate,
        select_mode=select_mode,
        keep_energy_ratio=keep_energy_ratio,
        sequency_keep_ratio=sequency_keep_ratio,
        keep_ratio=keep_ratio,
    )
    return transform.process(wav_path, out_dir, progress_cb)


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    "FWHTTransform",
    "fwht_transform_and_mp3",
    "fwht_ola",
    "fwht",
    "ifwht",
    "fwht_ortho",
    "ifwht_ortho",
    "apply_fwht_coefficient_selection",
]
