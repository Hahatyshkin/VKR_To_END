"""
processing: пакет вычислительной части и кодеков.

Назначение:
- Предоставляет унифицированный API для обработки аудио
- Экспортирует все методы трансформаций
- Экспортирует метрики качества

Структура модуля:
=================
processing/
├── __init__.py          # Этот файл - публичный API
├── audio_ops.py         # Standard MP3 + переэкспорт трансформаций
├── codecs.py            # FFmpeg взаимодействия
├── metrics.py           # Метрики качества
├── utils.py             # Вспомогательные функции
├── api.py               # Устаревший фасад совместимости
└── transforms/          # Реализации трансформаций
    ├── __init__.py      # Экспорт всех трансформаций
    ├── base.py          # Базовый класс и утилиты OLA
    ├── fft.py           # FFT
    ├── dct.py           # DCT
    ├── dwt.py           # DWT (Хаар)
    ├── fwht.py          # FWHT
    ├── huffman.py       # Huffman-like (μ-law)
    └── rosenbrock.py    # Rosenbrock-like

Доступные методы обработки:
===========================
1. Standard MP3 - прямое кодирование WAV→MP3 через ffmpeg
2. FFT - Быстрое преобразование Фурье
3. DCT - Дискретное косинусное преобразование
4. DWT - Вейвлет Хаара
5. FWHT - Преобразование Уолша-Адамара
6. Huffman-like - μ-law компандирование
7. Rosenbrock-like - Нелинейное сглаживание

Использование:
==============
>>> from processing import (
...     # Методы обработки
...     standard_convert_to_mp3,
...     fft_transform_and_mp3,
...     fwht_transform_and_mp3,
...
...     # Метрики
...     compute_snr_db,
...     compute_metrics_batch,
... )

Быстрый старт:
--------------
>>> # Стандартное MP3
>>> out, t = standard_convert_to_mp3("audio.wav", "output/")
>>>
>>> # FFT с отбором по энергии
>>> out, t = fft_transform_and_mp3("audio.wav", "output/",
...     select_mode="energy", keep_energy_ratio=0.8)
>>>
>>> # FWHT
>>> out, t = fwht_transform_and_mp3("audio.wav", "output/")

Метрики качества:
=================
- SNR (dB): Signal-to-Noise Ratio
- RMSE: Root Mean Square Error
- SI-SDR (dB): Scale-Invariant SDR
- LSD (dB): Log-Spectral Distance
- Spectral Convergence: мера сходства спектров
- Spectral Centroid Δ: разница центроидов
- Cosine Similarity: косинусное сходство спектров

>>> from processing import compute_metrics_batch
>>> results = compute_metrics_batch("original.wav", [
...     ("MP3", "output.mp3", 1.5),
...     ("FWHT", "output_fwht.mp3", 2.3),
... ])
"""
from __future__ import annotations

# =============================================================================
# ОСНОВНЫЕ МЕТОДЫ ОБРАБОТКИ
# =============================================================================

from .audio_ops import (
    # Стандартный MP3
    standard_convert_to_mp3,

    # Трансформации (переэкспорт)
    FFTTransform,
    DCTTransform,
    DWTTransform,
    FWHTTransform,
    HuffmanLikeTransform,
    RosenbrockLikeTransform,

    # Функции-обёртки
    fft_transform_and_mp3,
    dct_transform_and_mp3,
    wavelet_transform_and_mp3,
    fwht_transform_and_mp3,
    huffman_like_transform_and_mp3,
    rosenbrock_like_transform_and_mp3,

    # Пакетный расчёт
    _compute_metrics_batch,
    compare_results,
)


# =============================================================================
# МЕТРИКИ КАЧЕСТВА
# =============================================================================

from .metrics import (
    compute_snr_db,
    compute_rmse,
    compute_si_sdr_db,
    compute_lsd_db,
    compute_spectral_convergence,
    compute_spectral_centroid_diff_hz,
    compute_spectral_cosine_similarity,
    compute_metrics_batch,
)


# =============================================================================
# УТИЛИТЫ
# =============================================================================

from .utils import (
    is_power_of_two,
    normalize_ratio,
    parse_int,
    parse_float,
)


# =============================================================================
# КОНСТАНТЫ ИЗ TRANSFORMS
# =============================================================================

from .transforms import (
    SELECT_MODE_NONE,
    SELECT_MODE_ENERGY,
    SELECT_MODE_LOWPASS,
    VALID_SELECT_MODES,
    TRANSFORM_CLASSES,
    TRANSFORM_FUNCTIONS,
    get_transform,
    get_transform_function,
)


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    # Стандартный MP3
    "standard_convert_to_mp3",

    # Классы трансформаций
    "FFTTransform",
    "DCTTransform",
    "DWTTransform",
    "FWHTTransform",
    "HuffmanLikeTransform",
    "RosenbrockLikeTransform",

    # Функции-обёртки
    "fft_transform_and_mp3",
    "dct_transform_and_mp3",
    "wavelet_transform_and_mp3",
    "fwht_transform_and_mp3",
    "huffman_like_transform_and_mp3",
    "rosenbrock_like_transform_and_mp3",

    # Метрики
    "compute_snr_db",
    "compute_rmse",
    "compute_si_sdr_db",
    "compute_lsd_db",
    "compute_spectral_convergence",
    "compute_spectral_centroid_diff_hz",
    "compute_spectral_cosine_similarity",
    "compute_metrics_batch",

    # Пакетный расчёт
    "compare_results",
    "_compute_metrics_batch",

    # Утилиты
    "is_power_of_two",
    "normalize_ratio",
    "parse_int",
    "parse_float",

    # Константы
    "SELECT_MODE_NONE",
    "SELECT_MODE_ENERGY",
    "SELECT_MODE_LOWPASS",
    "VALID_SELECT_MODES",

    # Утилиты выбора трансформации
    "TRANSFORM_CLASSES",
    "TRANSFORM_FUNCTIONS",
    "get_transform",
    "get_transform_function",
]
