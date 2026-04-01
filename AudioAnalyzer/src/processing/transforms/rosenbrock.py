"""
Rosenbrock-like: Нелинейное сглаживающее преобразование.

Назначение:
- Эвристическое сглаживание аудиосигнала
- Мягкое сжатие динамики
- Кодирование обработанного сигнала в MP3

Теоретические основы:
=====================
Данный метод назван "Rosenbrock-like" по аналогии с функцией Розенброка,
используемой в оптимизации. Однако здесь применяется простое нелинейное
сглаживающее преобразование.

Преобразование:
---------------
y = x / (1 + α(x - β)²)

где:
- x — входной сигнал
- α (alpha) — параметр сглаживания
- β (beta) — параметр сдвига

Свойства преобразования:
------------------------
1. При α = 0: y = x (тождественное преобразование)
2. При α > 0: сигнал сглаживается около точки β
3. Чем больше α, тем сильнее сжатие динамики

Графическая интерпретация:
--------------------------
Преобразование создаёт "седловину" в точке x = β:
- При x ≈ β: y ≈ x (мало изменений)
- При x >> β или x << β: y < x (сжатие)

Это создаёт эффект мягкого лимитера/компрессора.

Параметры:
----------
alpha : float
    Параметр сглаживания (0-10)
    - α = 0: без изменений
    - α = 0.2: мягкое сжатие (по умолчанию)
    - α = 1-10: сильное сжатие

beta : float
    Параметр сдвига (-5...+5)
    - β = 0: симметричное сжатие вокруг нуля
    - β > 0: асимметрия в сторону положительных значений
    - β < 0: асимметрия в сторону отрицательных значений

block_size : int
    Размер блока (для совместимости, не используется)

Примеры:
--------
>>> # Мягкое сглаживание
>>> rosenbrock_like_transform_and_mp3("audio.wav", "output/", alpha=0.2, beta=1.0)

>>> # Сильное сжатие
>>> rosenbrock_like_transform_and_mp3("audio.wav", "output/", alpha=2.0, beta=0.5)

Внешние библиотеки:
-------------------
- numpy: численные операции
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
    get_output_path,
)
from ..codecs import ensure_ffmpeg_available, encode_pcm_to_mp3

logger = logging.getLogger("audio.processing.transforms.rosenbrock")


# =============================================================================
# ФУНКЦИИ ПРЕОБРАЗОВАНИЯ (низкий уровень)
# =============================================================================

def rosenbrock_nonlinear(
    x: np.ndarray,
    alpha: float = 0.2,
    beta: float = 1.0
) -> np.ndarray:
    """Нелинейное Rosenbrock-подобное преобразование.

    Применяет сглаживающую нелинейность к сигналу.

    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал в диапазоне [-1, 1]
    alpha : float
        Параметр сглаживания (0-10)
    beta : float
        Параметр сдвига (-5...+5)

    Возвращает:
    -----------
    np.ndarray
        Преобразованный сигнал

    Формула:
    --------
    y = x / (1 + α(x - β)²)
    """
    x_f = x.astype(np.float32)
    return x_f / (1.0 + alpha * (x_f - beta) ** 2)


def normalize_peak(x: np.ndarray) -> np.ndarray:
    """Нормализация по пиковому значению.

    Масштабирует сигнал так, чтобы максимальное
    абсолютное значение не превышало 1.0.

    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал

    Возвращает:
    -----------
    np.ndarray
        Нормализованный сигнал
    """
    peak = float(np.max(np.abs(x)) + 1e-9)
    if peak > 1.0:
        return x / peak
    return x


def rosenbrock_process(
    x: np.ndarray,
    alpha: float = 0.2,
    beta: float = 1.0
) -> np.ndarray:
    """Полный цикл Rosenbrock-like обработки.

    Последовательность:
    1. Нелинейное преобразование
    2. Нормировка по пику (защита от клиппинга)

    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал
    alpha : float
        Параметр сглаживания
    beta : float
        Параметр сдвига

    Возвращает:
    -----------
    np.ndarray
        Обработанный сигнал
    """
    # Нелинейное преобразование
    y = rosenbrock_nonlinear(x, alpha, beta)

    # Нормировка
    return normalize_peak(y)


# =============================================================================
# КЛАСС ТРАНСФОРМАЦИИ
# =============================================================================

class RosenbrockLikeTransform(BaseTransform):
    """Rosenbrock-like трансформация (нелинейное сглаживание).

    Применяет эвристическое нелинейное преобразование
    для мягкого сжатия динамики сигнала.

    Атрибуты:
    ---------
    NAME : str
        Имя метода
    DESCRIPTION : str
        Краткое описание
    FILE_SUFFIX : str
        Суффикс файла ('rosenbrock')

    Дополнительные параметры:
    -------------------------
    alpha : float
        Параметр сглаживания
    beta : float
        Параметр сдвига
    """

    NAME = "Rosenbrock"
    DESCRIPTION = "Нелинейное сглаживающее преобразование"
    FILE_SUFFIX = "rosenbrock"

    def __init__(
        self,
        block_size: int = 2048,
        bitrate: str = "192k",
        alpha: float = 0.2,
        beta: float = 1.0,
        select_mode: str = "none",
        keep_energy_ratio: float = 1.0,
        sequency_keep_ratio: float = 1.0,
    ):
        """Инициализация Rosenbrock-like трансформации.

        Параметры:
        ----------
        block_size : int
            Размер блока (для совместимости, не используется)
        bitrate : str
            Битрейт MP3
        alpha : float
            Параметр сглаживания (0-10)
        beta : float
            Параметр сдвига (-5...+5)
        """
        super().__init__(
            block_size=block_size,
            bitrate=bitrate,
            select_mode=select_mode,
            keep_energy_ratio=keep_energy_ratio,
            sequency_keep_ratio=sequency_keep_ratio,
        )

        # Параметр alpha
        try:
            self.alpha = float(max(0.0, min(10.0, alpha)))
        except (TypeError, ValueError) as e:
            logger.debug("alpha_parse_error: %s, using default 0.2", e)
            self.alpha = 0.2

        # Параметр beta
        try:
            self.beta = float(max(-5.0, min(5.0, beta)))
        except (TypeError, ValueError) as e:
            logger.debug("beta_parse_error: %s, using default 1.0", e)
            self.beta = 1.0

    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """Применить Rosenbrock-like обработку к блоку.

        Примечание: для этого метода OLA не используется,
        обработка применяется ко всему сигналу целиком.

        Параметры:
        ----------
        block : np.ndarray
            Входной сигнал

        Возвращает:
        -----------
        np.ndarray
            Обработанный сигнал
        """
        return rosenbrock_process(block, self.alpha, self.beta)

    def process(
        self,
        wav_path: str,
        out_dir: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Полный пайплайн Rosenbrock-like обработки.

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
        self.log_start(wav_path, alpha=self.alpha, beta=self.beta)
        ensure_ffmpeg_available()

        if progress_cb:
            progress_cb(0.0, "Rosenbrock: декодирование входа")

        # Загрузка аудио
        x, sr = load_audio_safe(wav_path)

        if progress_cb:
            progress_cb(0.3, "Rosenbrock: нелинейное преобразование")

        # Rosenbrock-like обработка
        y = self.transform_block(x)

        if progress_cb:
            progress_cb(0.7, "Rosenbrock: кодирование MP3")

        out_mp3 = self.get_output_path(wav_path, out_dir)
        encode_pcm_to_mp3(y.astype(np.float32), sr, out_mp3, self.bitrate, profile="vbr")

        dt = time.perf_counter() - t0
        if progress_cb:
            progress_cb(1.0, "Rosenbrock: готово")

        self.log_done(out_mp3, dt)
        return out_mp3, dt


# =============================================================================
# ФУНКЦИЯ-ОБЁРТКА (обратная совместимость)
# =============================================================================

def rosenbrock_like_transform_and_mp3(
    wav_path: str,
    out_dir: str,
    *,
    alpha: float = 0.2,
    beta: float = 1.0,
    bitrate: str = "192k",
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> Tuple[str, float]:
    """Rosenbrock-like (нелинейное сглаживание) → MP3.

    Функция-обёртка над RosenbrockLikeTransform для обратной совместимости.

    Параметры:
    ----------
    wav_path : str
        Входной WAV/аудиофайл
    out_dir : str
        Каталог для сохранения MP3
    alpha : float
        Параметр сглаживания (0-10)
    beta : float
        Параметр сдвига (-5...+5)
    bitrate : str
        Битрейт MP3
    progress_cb : callable
        Колбэк прогресса

    Возвращает:
    -----------
    Tuple[str, float]
        (путь к MP3, время в секундах)

    Пример:
    -------
    >>> out_path, time_sec = rosenbrock_like_transform_and_mp3(
    ...     "audio.wav", "output/", alpha=0.5, beta=0.0
    ... )
    """
    transform = RosenbrockLikeTransform(
        bitrate=bitrate,
        alpha=alpha,
        beta=beta,
    )
    return transform.process(wav_path, out_dir, progress_cb)


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    "RosenbrockLikeTransform",
    "rosenbrock_like_transform_and_mp3",
    "rosenbrock_nonlinear",
    "normalize_peak",
    "rosenbrock_process",
]
