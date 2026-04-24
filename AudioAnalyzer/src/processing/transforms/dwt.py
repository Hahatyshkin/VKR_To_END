"""
DWT: Дискретное вейвлет-преобразование (Хаар).

Назначение:
- Многоуровневое частотно-временное разложение сигнала
- Разделение на аппроксимацию (низкие частоты) и детали (высокие)
- Кодирование восстановленного сигнала в MP3

Теоретические основы:
=====================
DWT (Discrete Wavelet Transform) — многоуровневое разложение сигнала,
которое предоставляет информацию как о частотном содержании, так и
о его локализации во времени.

Вейвлет Хаара:
-------------
Простейший вейвлет, использует ступенчатые функции.
На каждом уровне сигнал разделяется на:
- Аппроксимацию (A): сглаженная версия сигнала
- Детали (D): высокочастотные компоненты

Формулы (одноуровневое DWT):
----------------------------
A[k] = (x[2k] + x[2k+1]) / sqrt(2)  — аппроксимация
D[k] = (x[2k] - x[2k+1]) / sqrt(2)  — детали

Обратное преобразование:
x[2k]   = (A[k] + D[k]) / sqrt(2)
x[2k+1] = (A[k] - D[k]) / sqrt(2)

Многоуровневое DWT:
-------------------
К аппроксимации применяется следующее разложение:
Level 1: A0 → A1, D1
Level 2: A1 → A2, D2
...
Level L: AL-1 → AL, DL

Результат: [AL, DL, DL-1, ..., D2, D1]
где AL — грубая аппроксимация, Di — детали на уровне i.

Отбор коэффициентов:
--------------------
1. По энергии: сохраняем наибольшие по |коэффициент| элементы
2. Lowpass: сохраняем аппроксимацию и первые уровни деталей

Параметры:
----------
block_size : int
    Размер блока (степень двойки)

levels : int
    Число уровней декомпозиции (1-log2(block_size))
    Типичные значения: 4-8

select_mode : str
    Режим отбора: 'none', 'energy', 'lowpass'

Примеры:
--------
>>> # Идеальная реконструкция
>>> wavelet_transform_and_mp3("audio.wav", "output/")

>>> # 6 уровней с сохранением 80% энергии
>>> wavelet_transform_and_mp3("audio.wav", "output/",
...     levels=6, select_mode="energy", keep_energy_ratio=0.8)

Внешние библиотеки:
-------------------
- numpy: численные операции
- logging: диагностические сообщения
"""
from __future__ import annotations

import time
import logging
from typing import Callable, List, Optional, Tuple

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

logger = logging.getLogger("audio.processing.transforms.dwt")


# =============================================================================
# ФУНКЦИИ ПРЕОБРАЗОВАНИЯ (низкий уровень)
# =============================================================================

def haar_dwt_1level(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Одноуровневое вейвлет-преобразование Хаара.

    Разделяет сигнал на аппроксимацию (низкие частоты)
    и детали (высокие частоты).

    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал

    Возвращает:
    -----------
    Tuple[np.ndarray, np.ndarray]
        (A, D) — аппроксимация и детали

    Примечание:
    -----------
    При нечётной длине сигнал дополняется нулём.
    """
    n = len(x)
    if n % 2 == 1:
        x = np.pad(x, (0, 1))
        n += 1

    # Аппроксимация: среднее соседних элементов
    a = (x[0:n:2] + x[1:n:2]) / np.sqrt(2.0)

    # Детали: разность соседних элементов
    d = (x[0:n:2] - x[1:n:2]) / np.sqrt(2.0)

    return a.astype(np.float32), d.astype(np.float32)


def haar_idwt_1level(a: np.ndarray, d: np.ndarray, orig_len: int) -> np.ndarray:
    """Обратное одноуровневое преобразование Хаара.

    Восстанавливает сигнал из аппроксимации и деталей.

    Параметры:
    ----------
    a : np.ndarray
        Коэффициенты аппроксимации
    d : np.ndarray
        Коэффициенты деталей
    orig_len : int
        Исходная длина сигнала (для обрезки)

    Возвращает:
    -----------
    np.ndarray
        Восстановленный сигнал
    """
    n = a.shape[0] + d.shape[0]
    x = np.empty(n, dtype=np.float32)

    # Чётные элементы
    x[0:n:2] = (a + d) / np.sqrt(2.0)
    # Нечётные элементы
    x[1:n:2] = (a - d) / np.sqrt(2.0)

    return x[:orig_len]


def dwt_decompose(x: np.ndarray, levels: int) -> List[np.ndarray]:
    """Многоуровневое DWT разложение.

    Применяет каскадное разложение Хаара.

    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал
    levels : int
        Число уровней декомпозиции

    Возвращает:
    -----------
    List[np.ndarray]
        Список [AL, DL, DL-1, ..., D1]
        AL — финальная аппроксимация
        Di — детали на уровне i
    """
    coeffs = []
    a = x.astype(np.float32)

    for _ in range(levels):
        a, d = haar_dwt_1level(a)
        coeffs.append(d)  # Сохраняем детали

    coeffs.append(a)  # Финальная аппроксимация

    return coeffs


def dwt_reconstruct(coeffs: List[np.ndarray], orig_len: int) -> np.ndarray:
    """Многоуровневое DWT восстановление.

    Собирает сигнал из коэффициентов DWT.

    Поддерживает два формата входных данных:
    1. Выход dwt_decompose: [D1, D2, ..., DL, AL]
    2. Выход unflatten: [AL, DL, DL-1, ..., D1]

    Автоматически определяет формат по длине первого элемента:
    если len(coeffs[0]) <= len(coeffs[-1]) — формат dwt_decompose,
    иначе — формат unflatten.

    Параметры:
    ----------
    coeffs : List[np.ndarray]
        Список коэффициентов DWT
    orig_len : int
        Исходная длина сигнала

    Возвращает:
    -----------
    np.ndarray
        Восстановленный сигнал
    """
    # Автоопределение формата: dwt_decompose возвращает [D1,...,DL,AL],
    # unflatten возвращает [AL,DL-1,...,D1].
    # У dwt_decompose первый элемент (D1) длиннее последнего (AL).
    if len(coeffs) >= 2 and len(coeffs[0]) <= len(coeffs[-1]):
        # Формат dwt_decompose: [D1, D2, ..., DL, AL]
        # Реверсируем: [AL, DL, ..., D2, D1]
        coeffs = coeffs[::-1]

    # Начинаем с аппроксимации (первый элемент = AL)
    a = coeffs[0].astype(np.float32)

    # Восстанавливаем по уровням (от грубого к детальному)
    for i in range(1, len(coeffs)):
        d = coeffs[i].astype(np.float32)

        # Выравниваем длины при необходимости
        min_len = min(len(a), len(d))
        if len(a) != len(d):
            d = np.pad(d, (0, len(a) - len(d))) if len(d) < len(a) else d[:len(a)]

        a = haar_idwt_1level(a, d, len(a) * 2)

    return a[:orig_len]


def flatten_dwt_coefficients(coeffs: List[np.ndarray]) -> np.ndarray:
    """Собрать коэффициенты DWT в единый вектор.

    Порядок: [AL | DL | DL-1 | ... | D1]

    Параметры:
    ----------
    coeffs : List[np.ndarray]
        Список коэффициентов DWT

    Возвращает:
    -----------
    np.ndarray
        Единый вектор коэффициентов
    """
    # Порядок: аппроксимация, затем детали от последнего к первому уровню
    return np.concatenate(coeffs[::-1])


def unflatten_dwt_coefficients(
    flat: np.ndarray,
    orig_len: int,
    levels: int
) -> List[np.ndarray]:
    """Разбить вектор обратно в список коэффициентов DWT.

    Параметры:
    ----------
    flat : np.ndarray
        Единый вектор коэффициентов
    orig_len : int
        Исходная длина сигнала
    levels : int
        Число уровней декомпозиции

    Возвращает:
    -----------
    List[np.ndarray]
        Список коэффициентов [AL, DL, DL-1, ..., D1]
    """
    coeffs = []
    ptr = 0

    # Длина аппроксимации
    a_len = int(np.ceil(orig_len / (2 ** levels)))
    # Используем доступные данные, не теряем их
    actual_a_len = min(a_len, max(0, len(flat) - ptr))
    if actual_a_len > 0:
        coeffs.append(flat[ptr:ptr + actual_a_len].astype(np.float32))
        # Если меньше ожидаемого, дополняем нулями
        if actual_a_len < a_len:
            coeffs[0] = np.pad(coeffs[0], (0, a_len - actual_a_len), mode='constant')
    else:
        coeffs.append(np.zeros(a_len, dtype=np.float32))
    ptr += a_len

    # Детали от последнего уровня к первому
    for level in range(levels):
        d_len = int(np.ceil(orig_len / (2 ** (levels - level))))
        # Используем доступные данные
        actual_d_len = min(d_len, max(0, len(flat) - ptr))
        if actual_d_len > 0:
            detail = flat[ptr:ptr + actual_d_len].astype(np.float32)
            # Если меньше ожидаемого, дополняем нулями
            if actual_d_len < d_len:
                detail = np.pad(detail, (0, d_len - actual_d_len), mode='constant')
            coeffs.append(detail)
        else:
            coeffs.append(np.zeros(d_len, dtype=np.float32))
        ptr += d_len

    return coeffs


def apply_dwt_coefficient_selection(
    coeffs: np.ndarray,
    select_mode: str,
    keep_energy_ratio: float,
    sequency_keep_ratio: float
) -> np.ndarray:
    """Применить отбор коэффициентов DWT.

    Параметры:
    ----------
    coeffs : np.ndarray
        Вектор коэффициентов DWT
    select_mode : str
        Режим отбора: 'none', 'energy', 'lowpass'
    keep_energy_ratio : float
        Доля энергии для сохранения
    sequency_keep_ratio : float
        Доля низкочастотных компонент

    Возвращает:
    -----------
    np.ndarray
        Коэффициенты после отбора
    """
    if select_mode == SELECT_MODE_NONE:
        return coeffs

    if select_mode == SELECT_MODE_ENERGY and keep_energy_ratio < 1.0:
        magsq = coeffs * coeffs
        order = np.argsort(magsq)[::-1]
        cumsum = np.cumsum(magsq[order])
        total_e = cumsum[-1] + 1e-12
        need = keep_energy_ratio * total_e
        keep_n = int(np.searchsorted(cumsum, need, side="left")) + 1

        mask = np.zeros_like(coeffs, dtype=bool)
        mask[order[:keep_n]] = True
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

class DWTTransform(BaseTransform):
    """DWT (Хаар) трансформация с OLA и многоуровневым разложением.

    Атрибуты:
    ---------
    NAME : str
        Имя метода
    DESCRIPTION : str
        Краткое описание
    FILE_SUFFIX : str
        Суффикс файла ('dwt')

    Дополнительные параметры:
    -------------------------
    levels : int
        Число уровней декомпозиции
    """

    NAME = "DWT"
    DESCRIPTION = "Дискретное вейвлет-преобразование (Хаар)"
    FILE_SUFFIX = "dwt"

    def __init__(
        self,
        block_size: int = 2048,
        bitrate: str = "192k",
        select_mode: str = SELECT_MODE_NONE,
        keep_energy_ratio: float = 1.0,
        sequency_keep_ratio: float = 1.0,
        levels: int = 4,
    ):
        """Инициализация DWT-трансформации.

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
            Доля низких частот
        levels : int
            Число уровней декомпозиции (1-12)
        """
        super().__init__(
            block_size=block_size,
            bitrate=bitrate,
            select_mode=select_mode,
            keep_energy_ratio=keep_energy_ratio,
            sequency_keep_ratio=sequency_keep_ratio,
        )

        # Парсинг levels с защитой
        try:
            self.levels = int(max(1, int(levels)))
        except (TypeError, ValueError) as e:
            logger.debug("levels_parse_error: %s, using default 4", e)
            self.levels = 4

    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """Применить DWT к одному блоку.

        Параметры:
        ----------
        block : np.ndarray
            Входной блок

        Возвращает:
        -----------
        np.ndarray
            Восстановленный блок
        """
        N = len(block)

        # Многоуровневое разложение
        coeffs = dwt_decompose(block, self.levels)

        # Собираем в единый вектор
        flat = flatten_dwt_coefficients(coeffs)

        # Отбор коэффициентов
        flat = apply_dwt_coefficient_selection(
            flat,
            self.select_mode,
            self.keep_energy_ratio,
            self.sequency_keep_ratio,
        )

        # Восстановление
        coeffs_back = unflatten_dwt_coefficients(flat, N, self.levels)
        rec = dwt_reconstruct(coeffs_back, N)

        return rec

    def process(
        self,
        wav_path: str,
        out_dir: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Полный пайплайн DWT обработки.

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
        t0 = time.perf_counter()
        self.log_start(
            wav_path,
            block_size=self.block_size,
            mode=self.select_mode,
            keep_energy=self.keep_energy_ratio,
            seq_keep=self.sequency_keep_ratio,
            levels=self.levels,
        )
        ensure_ffmpeg_available()

        if progress_cb:
            progress_cb(0.0, "DWT: декодирование входа")

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
            blk = (x_padded[i0 : i0 + N] * win).astype(np.float32)

            # DWT трансформация
            rec = self.transform_block(blk) * win

            # OLA накопление
            y_accum[i0 : i0 + N] += rec
            w_accum[i0 : i0 + N] += win * win

            if progress_cb:
                progress_cb(
                    min(0.95, 0.1 + 0.8 * (fi + 1) / frames),
                    f"DWT: блок {fi+1}/{frames}"
                )

        # Финализация OLA
        y = finalize_ola(y_accum, w_accum, n)
        out_mp3 = self.get_output_path(wav_path, out_dir)

        # Кодирование в MP3
        if progress_cb:
            progress_cb(0.97, "DWT: кодирование MP3")
        encode_pcm_to_mp3(y, sr, out_mp3, self.bitrate, profile="vbr")

        dt = time.perf_counter() - t0
        if progress_cb:
            progress_cb(1.0, "DWT: готово")

        self.log_done(out_mp3, dt)
        return out_mp3, dt


# =============================================================================
# ФУНКЦИЯ-ОБЁРТКА (обратная совместимость)
# =============================================================================

def wavelet_transform_and_mp3(
    wav_path: str,
    out_dir: str,
    *,
    block_size: int = 2048,
    bitrate: str = "192k",
    select_mode: str = "none",
    keep_energy_ratio: float = 1.0,
    sequency_keep_ratio: float = 1.0,
    levels: int = 4,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> Tuple[str, float]:
    """Многоуровневое DWT (Хаар) с OLA → MP3.

    Функция-обёртка над DWTTransform для обратной совместимости.

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
        Доля энергии, 0..1
    sequency_keep_ratio : float
        Доля низких частот, 0..1
    levels : int
        Число уровней декомпозиции
    progress_cb : callable
        Колбэк прогресса

    Возвращает:
    -----------
    Tuple[str, float]
        (путь к MP3, время в секундах)
    """
    transform = DWTTransform(
        block_size=block_size,
        bitrate=bitrate,
        select_mode=select_mode,
        keep_energy_ratio=keep_energy_ratio,
        sequency_keep_ratio=sequency_keep_ratio,
        levels=levels,
    )
    return transform.process(wav_path, out_dir, progress_cb)


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    "DWTTransform",
    "wavelet_transform_and_mp3",
    "haar_dwt_1level",
    "haar_idwt_1level",
    "dwt_decompose",
    "dwt_reconstruct",
    "flatten_dwt_coefficients",
    "unflatten_dwt_coefficients",
    "apply_dwt_coefficient_selection",
]
