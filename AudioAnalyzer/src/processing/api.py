"""
УСТАРЕВШИЙ фасад совместимости.

Назначение:
- Сохранить обратную совместимость публичного API ранних версий
- Переэкспортировать актуальные функции из processing.audio_ops

Рекомендация:
-------------
Для нового кода используйте прямые импорты:

>>> from processing import (
...     fwht_transform_and_mp3,
...     fft_transform_and_mp3,
...     standard_convert_to_mp3,
... )

или:

>>> from processing.audio_ops import fwht_transform_and_mp3
>>> from processing.transforms import FWHTTransform

Используемые библиотеки:
------------------------
- typing: подсказки типов
"""
from __future__ import annotations

from typing import Callable, Optional, Tuple, List, Dict

# Переэкспорт актуальных функций (сохраняем старые точки входа для внешнего кода)
from .audio_ops import (
    # Основные методы
    fwht_transform_and_mp3,
    fft_transform_and_mp3,
    dct_transform_and_mp3,
    wavelet_transform_and_mp3,
    huffman_like_transform_and_mp3,
    rosenbrock_like_transform_and_mp3,
    standard_convert_to_mp3,

    # Сравнение результатов
    compare_results,

    # Метрики (для удобства)
    compute_snr_db,
    compute_rmse,
    compute_si_sdr_db,
    compute_lsd_db,
)


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    "fwht_transform_and_mp3",
    "fft_transform_and_mp3",
    "dct_transform_and_mp3",
    "wavelet_transform_and_mp3",
    "huffman_like_transform_and_mp3",
    "rosenbrock_like_transform_and_mp3",
    "standard_convert_to_mp3",
    "compare_results",
    "compute_snr_db",
    "compute_rmse",
    "compute_si_sdr_db",
    "compute_lsd_db",
]
