"""
Базовые утилиты и абстракции для модуля трансформаций.

Назначение:
- Общие функции для всех методов обработки (OLA, окна, нормировка)
- Абстрактный базовый класс для единообразного интерфейса трансформаций
- Константы и типы данных

Метод OLA (Overlap-Add):
========================
OLA — стандартный метод обработки сигналов произвольной длины через
перекрывающиеся блоки. При 50% перекрытии и sqrt-Hann окне достигается
идеальная реконструкция (сумма квадратов окон = 1).

Алгоритм:
1. Сигнал разбивается на блоки длины N с перекрытием N/2
2. Каждый блок умножается на окно анализа (sqrt-Hann)
3. Применяется прямое преобразование
4. Применяется обратное преобразование
5. Результат умножается на окно синтеза (то же sqrt-Hann)
6. Блоки складываются с накоплением весов

Математическое обоснование:
- Окно Ханна: w[n] = 0.5 * (1 - cos(2*pi*n/N))
- sqrt-Hann: h[n] = sqrt(w[n])
- При 50% перекрытии: h^2[n] + h^2[n+N/2] = 1

Внешние библиотеки:
- numpy: численные операции
- logging: диагностические сообщения
- abc: абстрактные базовые классы
"""
from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Tuple, Any

import numpy as np

from ..utils import is_power_of_two, normalize_ratio
from ..codecs import (
    ensure_ffmpeg_available,
    decode_audio_to_mono,
    load_wav_mono,
    encode_pcm_to_mp3,
)

logger = logging.getLogger("audio.processing.transforms")


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

# Режимы отбора коэффициентов
SELECT_MODE_NONE = "none"       # Без отбора (идеальная реконструкция)
SELECT_MODE_ENERGY = "energy"   # По энергии (сжатие)
SELECT_MODE_LOWPASS = "lowpass" # По частоте (фильтрация)

VALID_SELECT_MODES = (SELECT_MODE_NONE, SELECT_MODE_ENERGY, SELECT_MODE_LOWPASS)


# =============================================================================
# УНИВЕРСАЛЬНЫЕ ФУНКЦИИ-УТИЛИТЫ
# =============================================================================

def load_audio_safe(wav_path: str) -> Tuple[np.ndarray, int]:
    """Безопасная загрузка аудио с fallback на soundfile.

    Пытается декодировать через ffmpeg (предпочтительно для exe),
    при ошибке падает на soundfile для локального окружения.

    Параметры:
    ----------
    wav_path : str
        Путь к аудиофайлу (WAV, MP3, FLAC и др.)

    Возвращает:
    -----------
    Tuple[np.ndarray, int]
        (pcm_data, sample_rate) — моно сигнал и частота дискретизации

    Пример:
    -------
    >>> x, sr = load_audio_safe("audio.wav")
    >>> print(f"Длительность: {len(x)/sr:.2f} сек")
    """
    try:
        return decode_audio_to_mono(wav_path)
    except Exception as e:
        logger.debug("decode_audio_to_mono failed (%s), falling back to load_wav_mono", e)
        return load_wav_mono(wav_path)


def create_ola_window(block_size: int) -> np.ndarray:
    """Создать sqrt-Hann окно для OLA с 50% перекрытием.

    Окно sqrt-Hann обеспечивает идеальную реконструкцию при 50% перекрытии:
    h^2[n] + h^2[n+N/2] = 1 для всех n в пределах блока.

    Параметры:
    ----------
    block_size : int
        Длина блока (должна быть степенью двойки)

    Возвращает:
    -----------
    np.ndarray
        Массив длины block_size с окном sqrt-Hann (float32)

    Примечание:
    -----------
    Добавление 1e-12 к окну Ханна предотвращает деление на ноль
    при вычислении квадратного корня.
    """
    return np.sqrt(np.hanning(block_size) + 1e-12).astype(np.float32)


def finalize_ola(
    y_accum: np.ndarray,
    w_accum: np.ndarray,
    original_len: int
) -> np.ndarray:
    """Завершить OLA: нормировка окна и обрезка до исходной длины.

    Выполняет нормализацию накопленного сигнала по накопленным весам окна,
    затем обрезает до исходной длины и защищает от клиппинга.

    Параметры:
    ----------
    y_accum : np.ndarray
        Накопленный сигнал после сложения всех блоков
    w_accum : np.ndarray
        Накопленные квадраты окна (веса нормализации)
    original_len : int
        Исходная длина сигнала до дополнения

    Возвращает:
    -----------
    np.ndarray
        Восстановленный сигнал длины original_len (float32)

    Примечание:
    -----------
    - Деление на max(w_accum, 1e-8) защищает от деления на ноль
    - Нормировка по пику защищает от клиппинга при кодировании
    """
    y = np.divide(y_accum, np.maximum(w_accum, 1e-8))[:original_len]
    peak = float(np.max(np.abs(y)) + 1e-9)
    if peak > 1.0:
        y = y / peak
    return y


def get_output_path(wav_path: str, out_dir: str, suffix: str) -> str:
    """Сформировать путь к выходному MP3 файлу.

    Параметры:
    ----------
    wav_path : str
        Путь к исходному аудиофайлу
    out_dir : str
        Директория для сохранения результата
    suffix : str
        Суффикс имени (например, 'fft', 'fwht', 'dct')

    Возвращает:
    -----------
    str
        Полный путь к выходному файлу: {out_dir}/{basename}_{suffix}.mp3
    """
    base = os.path.splitext(os.path.basename(wav_path))[0]
    return os.path.join(out_dir, f"{base}_{suffix}.mp3")


def prepare_ola_buffers(
    signal_length: int,
    block_size: int
) -> Tuple[int, int, int, np.ndarray, np.ndarray]:
    """Подготовить буферы для OLA обработки.

    Вычисляет параметры OLA (число фреймов, длина дополнения) и
    создаёт нулевые буферы для накопления сигнала.

    Параметры:
    ----------
    signal_length : int
        Длина исходного сигнала
    block_size : int
        Размер блока (степень двойки)

    Возвращает:
    -----------
    Tuple[int, int, int, np.ndarray, np.ndarray]
        (frames, hop, total_len, y_accum, w_accum)
        - frames: число фреймов
        - hop: шаг между фреймами (N/2 для 50% перекрытия)
        - total_len: полная длина с дополнением
        - y_accum: буфер накопления сигнала
        - w_accum: буфер накопления весов
    """
    hop = max(1, block_size // 2)  # 50% перекрытие
    frames = max(1, int(np.ceil(max(0, signal_length - block_size) / hop)) + 1)
    total_len = (frames - 1) * hop + block_size
    pad = total_len - signal_length

    y_accum = np.zeros(total_len, dtype=np.float32)
    w_accum = np.zeros(total_len, dtype=np.float32)

    return frames, hop, total_len, y_accum, w_accum


def select_coefficients_energy(
    coeffs: np.ndarray,
    keep_ratio: float
) -> np.ndarray:
    """Отбор коэффициентов по энергии.

    Сохраняет минимальное число наибольших по модулю коэффициентов,
    которые содержат заданную долю энергии сигнала.

    Параметры:
    ----------
    coeffs : np.ndarray
        Массив коэффициентов преобразования
    keep_ratio : float
        Доля энергии для сохранения (0.0-1.0)

    Возвращает:
    -----------
    np.ndarray
        Массив с обнулёнными коэффициентами

    Примечание:
    -----------
    DC-компонента (коэффициент 0) всегда сохраняется,
    так как содержит среднее значение сигнала.
    """
    if keep_ratio >= 1.0:
        return coeffs

    magsq = coeffs * coeffs
    order = np.argsort(magsq)[::-1]  # По убыванию энергии
    cumsum = np.cumsum(magsq[order])
    total_e = cumsum[-1] + 1e-12
    need = keep_ratio * total_e
    keep_n = int(np.searchsorted(cumsum, need, side="left")) + 1

    keep_idx = order[:keep_n]
    mask = np.zeros_like(coeffs, dtype=bool)
    mask[keep_idx] = True
    mask[0] = True  # DC-компонента всегда сохраняется

    return np.where(mask, coeffs, 0.0)


def select_coefficients_lowpass(
    coeffs: np.ndarray,
    keep_ratio: float
) -> np.ndarray:
    """Отбор коэффициентов по частоте (lowpass).

    Сохраняет первые коэффициенты в порядке Уолша/частоты,
    аналогично lowpass-фильтрации в частотной области.

    Параметры:
    ----------
    coeffs : np.ndarray
        Массив коэффициентов преобразования
    keep_ratio : float
        Доля коэффициентов для сохранения (0.0-1.0)

    Возвращает:
    -----------
    np.ndarray
        Массив с обнулёнными высокочастотными коэффициентами
    """
    if keep_ratio >= 1.0:
        return coeffs

    k_lp = max(1, int(keep_ratio * len(coeffs)))
    mask = np.zeros_like(coeffs, dtype=bool)
    mask[:k_lp] = True

    return np.where(mask, coeffs, 0.0)


# =============================================================================
# АБСТРАКТНЫЙ БАЗОВЫЙ КЛАСС
# =============================================================================

class BaseTransform(ABC):
    """Абстрактный базовый класс для всех методов трансформации.

    Определяет единый интерфейс для всех методов обработки аудио:
    - Стандартные параметры (block_size, bitrate, select_mode)
    - Прогресс-колбэки для UI
    - Общий паттерн OLA обработки

    Атрибуты класса:
    ----------------
    NAME : str
        Имя метода для логирования и имён файлов
    DESCRIPTION : str
        Краткое описание метода
    FILE_SUFFIX : str
        Суффикс для выходного файла

    Методы:
    -------
    transform_block : абстрактный
        Применить преобразование к одному блоку
    process : абстрактный
        Полный пайплайн обработки файла

    Пример реализации:
    ------------------
    class FFTTransform(BaseTransform):
        NAME = "FFT"
        DESCRIPTION = "Быстрое преобразование Фурье"
        FILE_SUFFIX = "fft"

        def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
            return np.fft.irfft(np.fft.rfft(block))
    """

    # Атрибуты класса (переопределяются в подклассах)
    NAME: str = "BaseTransform"
    DESCRIPTION: str = "Базовый класс трансформации"
    FILE_SUFFIX: str = "base"

    def __init__(
        self,
        block_size: int = 2048,
        bitrate: str = "192k",
        select_mode: str = SELECT_MODE_NONE,
        keep_energy_ratio: float = 1.0,
        sequency_keep_ratio: float = 1.0,
    ):
        """Инициализация трансформации.

        Параметры:
        ----------
        block_size : int
            Размер блока для OLA (степень двойки, обычно 1024-4096)
        bitrate : str
            Битрейт MP3 (например, '192k', '128k')
        select_mode : str
            Режим отбора: 'none', 'energy', 'lowpass'
        keep_energy_ratio : float
            Доля энергии для сохранения (режим 'energy')
        sequency_keep_ratio : float
            Доля низких частот для сохранения (режим 'lowpass')
        """
        self.block_size = int(block_size)
        self.bitrate = str(bitrate)
        self.select_mode = (select_mode or SELECT_MODE_NONE).lower()
        self.keep_energy_ratio = normalize_ratio(keep_energy_ratio)
        self.sequency_keep_ratio = normalize_ratio(sequency_keep_ratio)

        # Валидация
        if not is_power_of_two(self.block_size):
            raise ValueError(f"block_size должен быть степенью двойки, получено: {self.block_size}")

        if self.select_mode not in VALID_SELECT_MODES:
            raise ValueError(f"Недопустимый select_mode: {self.select_mode}. Допустимые: {VALID_SELECT_MODES}")

    @abstractmethod
    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """Применить преобразование к одному блоку.

        Параметры:
        ----------
        block : np.ndarray
            Входной блок сигнала (умноженный на окно)
        **params : dict
            Дополнительные параметры конкретного метода

        Возвращает:
        -----------
        np.ndarray
            Восстановленный блок (той же длины)
        """
        pass

    @abstractmethod
    def process(
        self,
        wav_path: str,
        out_dir: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Полный пайплайн обработки файла.

        Параметры:
        ----------
        wav_path : str
            Путь к исходному аудиофайлу
        out_dir : str
            Директория для сохранения результата
        progress_cb : callable, optional
            Колбэк прогресса: progress_cb(fraction: float, message: str)

        Возвращает:
        -----------
        Tuple[str, float]
            (путь к MP3, время обработки в секундах)
        """
        pass

    def get_output_path(self, wav_path: str, out_dir: str) -> str:
        """Сформировать путь к выходному файлу.

        Параметры:
        ----------
        wav_path : str
            Путь к исходному файлу
        out_dir : str
            Директория для сохранения

        Возвращает:
        -----------
        str
            Путь к выходному файлу с суффиксом метода
        """
        return get_output_path(wav_path, out_dir, self.FILE_SUFFIX)

    def log_start(self, wav_path: str, **extra_params) -> None:
        """Залогировать начало обработки.

        Параметры:
        ----------
        wav_path : str
            Путь к обрабатываемому файлу
        **extra_params : dict
            Дополнительные параметры для логирования
        """
        params_str = " ".join(f"{k}={v}" for k, v in extra_params.items())
        logger.info(f"{self.NAME}_start path={wav_path} {params_str}")

    def log_done(self, out_path: str, time_sec: float) -> None:
        """Залогировать завершение обработки.

        Параметры:
        ----------
        out_path : str
            Путь к выходному файлу
        time_sec : float
            Время обработки в секундах
        """
        logger.info(f"{self.NAME}_done out={out_path} dt={time_sec:.3f}")


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    # Константы
    "SELECT_MODE_NONE",
    "SELECT_MODE_ENERGY",
    "SELECT_MODE_LOWPASS",
    "VALID_SELECT_MODES",
    # Функции-утилиты
    "load_audio_safe",
    "create_ola_window",
    "finalize_ola",
    "get_output_path",
    "prepare_ola_buffers",
    "select_coefficients_energy",
    "select_coefficients_lowpass",
    # Базовый класс
    "BaseTransform",
]
