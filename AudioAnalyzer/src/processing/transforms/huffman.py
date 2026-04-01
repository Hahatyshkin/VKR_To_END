"""
Huffman-like: μ-law компандирование с квантованием.

Назначение:
- Нелинейное сжатие динамического диапазона
- Имитация предобработки для энтропийного кодирования
- Кодирование обработанного сигнала в MP3

Теоретические основы:
=====================
Данный метод не является истинным кодированием Хаффмана, но
имитирует подготовительный этап для энтропийного кодирования
через μ-law компандирование.

μ-law компандирование:
----------------------
Нелинейное преобразование, которое сжимает динамический диапазон
сигнала по логарифмическому закону. Широко используется в
телефонии (Северная Америка, Япония).

Формулы:
--------
Прямое преобразование:
y = sign(x) * ln(1 + μ|x|) / ln(1 + μ)

где μ — параметр сжатия (обычно 255 для телефонии)

Обратное преобразование:
x = sign(y) * ((1 + μ)^|y| - 1) / μ

Свойства:
- Большие значения сжимаются меньше
- Малые значения сжимаются больше
- Улучшается отношение сигнал/шум для тихих звуков

Квантование:
------------
После μ-law преобразования применяется равномерное квантование:
- Сигнал масштабируется в диапазон [0, Q-1]
- Округляется до целого
- Восстанавливается в [-1, 1]

Число уровней Q = 2^bits (bits = 8-16 типично)

Параметры:
----------
mu : float
    Параметр μ-law (1-255, больше = сильнее сжатие)
    - μ = 1: линейное преобразование
    - μ = 255: стандартное телефонное компандирование

bits : int
    Число бит квантования (1-16)
    - 8 бит: 256 уровней (телефония)
    - 16 бит: 65536 уровней (высокое качество)

block_size : int
    Размер блока (для совместимости с OLA, но не используется)

Примеры:
--------
>>> # Стандартное телефонное качество
>>> huffman_like_transform_and_mp3("audio.wav", "output/", mu=255, bits=8)

>>> # Высокое качество
>>> huffman_like_transform_and_mp3("audio.wav", "output/", mu=100, bits=14)

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

logger = logging.getLogger("audio.processing.transforms.huffman")


# =============================================================================
# ФУНКЦИИ ПРЕОБРАЗОВАНИЯ (низкий уровень)
# =============================================================================

def mulaw_compress(x: np.ndarray, mu: float = 255.0) -> np.ndarray:
    """Прямое μ-law компандирование.

    Сжимает динамический диапазон по логарифмическому закону.

    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал в диапазоне [-1, 1]
    mu : float
        Параметр сжатия (обычно 255)

    Возвращает:
    -----------
    np.ndarray
        Сжатый сигнал в диапазоне [-1, 1]

    Формула:
    --------
    y = sign(x) * ln(1 + μ|x|) / ln(1 + μ)
    """
    return np.sign(x) * (np.log1p(mu * np.abs(x)) / np.log1p(mu))


def mulaw_expand(y: np.ndarray, mu: float = 255.0) -> np.ndarray:
    """Обратное μ-law преобразование.

    Восстанавливает сигнал из сжатого представления.

    Параметры:
    ----------
    y : np.ndarray
        Сжатый сигнал в диапазоне [-1, 1]
    mu : float
        Параметр сжатия (должен совпадать с прямым преобразованием)

    Возвращает:
    -----------
    np.ndarray
        Восстановленный сигнал

    Формула:
    --------
    x = sign(y) * ((1 + μ)^|y| - 1) / μ
    """
    return np.sign(y) * ((1.0 + mu) ** np.abs(y) - 1.0) / mu


def quantize_uniform(x: np.ndarray, bits: int = 8) -> Tuple[np.ndarray, int]:
    """Равномерное квантование.

    Преобразует непрерывный сигнал в дискретный с заданным
    числом уровней.

    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал в диапазоне [-1, 1]
    bits : int
        Число бит (определяет число уровней Q = 2^bits)

    Возвращает:
    -----------
    Tuple[np.ndarray, int]
        (квантованный сигнал, число уровней Q)

    Примечание:
    -----------
    Квантование вносит шум, который тем меньше,
    чем больше bits.
    """
    Q = max(2, int(2 ** bits))

    # Масштабирование в [0, Q-1]
    xi = np.clip((x + 1.0) * 0.5 * (Q - 1), 0, Q - 1).astype(np.int32)

    # Обратное масштабирование в [-1, 1]
    x_rec = (xi.astype(np.float32) / (Q - 1)) * 2.0 - 1.0

    return x_rec, Q


def huffman_like_process(
    x: np.ndarray,
    mu: float = 255.0,
    bits: int = 8
) -> np.ndarray:
    """Полный цикл Huffman-like обработки.

    Последовательность:
    1. μ-law компандирование (сжатие динамического диапазона)
    2. Равномерное квантование (внесение шума квантования)
    3. Обратное μ-law (восстановление)

    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал
    mu : float
        Параметр μ-law
    bits : int
        Число бит квантования

    Возвращает:
    -----------
    np.ndarray
        Обработанный сигнал
    """
    # Прямое μ-law
    x_mu = mulaw_compress(x, mu)

    # Квантование
    x_q, _ = quantize_uniform(x_mu, bits)

    # Обратное μ-law
    return mulaw_expand(x_q, mu)


# =============================================================================
# КЛАСС ТРАНСФОРМАЦИИ
# =============================================================================

class HuffmanLikeTransform(BaseTransform):
    """Huffman-like трансформация (μ-law + квантование).

    Имитирует предобработку для энтропийного кодирования
    через нелинейное компандирование.

    Атрибуты:
    ---------
    NAME : str
        Имя метода
    DESCRIPTION : str
        Краткое описание
    FILE_SUFFIX : str
        Суффикс файла ('huffman')

    Дополнительные параметры:
    -------------------------
    mu : float
        Параметр μ-law компандирования
    bits : int
        Число бит квантования
    """

    NAME = "Huffman"
    DESCRIPTION = "μ-law компандирование с квантованием"
    FILE_SUFFIX = "huffman"

    def __init__(
        self,
        block_size: int = 2048,
        bitrate: str = "192k",
        mu: float = 255.0,
        bits: int = 8,
        select_mode: str = "none",
        keep_energy_ratio: float = 1.0,
        sequency_keep_ratio: float = 1.0,
    ):
        """Инициализация Huffman-like трансформации.

        Параметры:
        ----------
        block_size : int
            Размер блока (для совместимости, не используется)
        bitrate : str
            Битрейт MP3
        mu : float
            Параметр μ-law (1-255)
        bits : int
            Число бит квантования (1-16)
        """
        super().__init__(
            block_size=block_size,
            bitrate=bitrate,
            select_mode=select_mode,
            keep_energy_ratio=keep_energy_ratio,
            sequency_keep_ratio=sequency_keep_ratio,
        )

        # Параметр μ
        try:
            self.mu = float(max(1.0, mu))
        except (TypeError, ValueError) as e:
            logger.debug("mu_parse_error: %s, using default 255.0", e)
            self.mu = 255.0

        # Число бит
        try:
            self.bits = int(max(1, min(16, int(bits))))
        except (TypeError, ValueError) as e:
            logger.debug("bits_parse_error: %s, using default 8", e)
            self.bits = 8

    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """Применить Huffman-like обработку к блоку.

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
        return huffman_like_process(block, self.mu, self.bits)

    def process(
        self,
        wav_path: str,
        out_dir: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Полный пайплайн Huffman-like обработки.

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
        self.log_start(wav_path, mu=self.mu, bits=self.bits)
        ensure_ffmpeg_available()

        if progress_cb:
            progress_cb(0.0, "Huffman: декодирование входа")

        # Загрузка аудио
        x, sr = load_audio_safe(wav_path)

        if progress_cb:
            progress_cb(0.3, "Huffman: μ-law компандирование")

        # Huffman-like обработка
        y = self.transform_block(x)

        if progress_cb:
            progress_cb(0.7, "Huffman: кодирование MP3")

        out_mp3 = self.get_output_path(wav_path, out_dir)
        encode_pcm_to_mp3(y.astype(np.float32), sr, out_mp3, self.bitrate, profile="vbr")

        dt = time.perf_counter() - t0
        if progress_cb:
            progress_cb(1.0, "Huffman: готово")

        self.log_done(out_mp3, dt)
        return out_mp3, dt


# =============================================================================
# ФУНКЦИЯ-ОБЁРТКА (обратная совместимость)
# =============================================================================

def huffman_like_transform_and_mp3(
    wav_path: str,
    out_dir: str,
    *,
    block_size: int = 2048,
    bitrate: str = "192k",
    mu: float = 255.0,
    bits: int = 8,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> Tuple[str, float]:
    """Huffman-like (μ-law + квантование) → MP3.

    Функция-обёртка над HuffmanLikeTransform для обратной совместимости.

    Параметры:
    ----------
    wav_path : str
        Входной WAV/аудиофайл
    out_dir : str
        Каталог для сохранения MP3
    block_size : int
        Размер блока (не используется)
    bitrate : str
        Битрейт MP3
    mu : float
        Параметр μ-law (1-255)
    bits : int
        Число бит квантования (1-16)
    progress_cb : callable
        Колбэк прогресса

    Возвращает:
    -----------
    Tuple[str, float]
        (путь к MP3, время в секундах)

    Пример:
    -------
    >>> out_path, time_sec = huffman_like_transform_and_mp3(
    ...     "audio.wav", "output/", mu=255, bits=8
    ... )
    """
    transform = HuffmanLikeTransform(
        block_size=block_size,
        bitrate=bitrate,
        mu=mu,
        bits=bits,
    )
    return transform.process(wav_path, out_dir, progress_cb)


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    "HuffmanLikeTransform",
    "huffman_like_transform_and_mp3",
    "mulaw_compress",
    "mulaw_expand",
    "quantize_uniform",
    "huffman_like_process",
]
