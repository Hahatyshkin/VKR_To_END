"""
transforms: Модуль трансформаций аудиосигналов.

Назначение:
- Единая точка импорта всех методов обработки
- Консистентный интерфейс для всех трансформаций
- Подробная документация и аннотации типов

Структура модуля:
=================
- base.py: Базовый класс и общие утилиты OLA
- fft.py: Быстрое преобразование Фурье (FFT)
- dct.py: Дискретное косинусное преобразование (DCT)
- dwt.py: Дискретное вейвлет-преобразование (Хаар)
- fwht.py: Быстрое преобразование Уолша-Адамара (FWHT)
- huffman.py: μ-law компандирование с квантованием
- rosenbrock.py: Нелинейное сглаживающее преобразование

Доступные методы обработки:
===========================
1. Standard MP3 - прямое кодирование (в audio_ops.py)
2. FFT - Быстрое преобразование Фурье
3. DCT - Дискретное косинусное преобразование
4. DWT - Вейвлет Хаара
5. FWHT - Преобразование Уолша-Адамара
6. Huffman-like - μ-law компандирование
7. Rosenbrock-like - Нелинейное сглаживание
8. Daubechies DWT - Вейвлеты Добеши (db2, db4, db6, db8)
9. MDCT - Modified Discrete Cosine Transform

Использование:
==============
>>> from processing.transforms import FFTTransform, DCTTransform
>>>
>>> # Через классы
>>> fft = FFTTransform(block_size=2048, select_mode="energy", keep_energy_ratio=0.8)
>>> out_path, time_sec = fft.process("audio.wav", "output/")
>>>
>>> # Через функции-обёртки
>>> from processing.transforms import fft_transform_and_mp3
>>> out_path, time_sec = fft_transform_and_mp3("audio.wav", "output/")

Базовый класс:
==============
>>> from processing.transforms import BaseTransform
>>> help(BaseTransform)

Общие утилиты:
==============
>>> from processing.transforms import (
...     load_audio_safe,
...     create_ola_window,
...     finalize_ola,
...     SELECT_MODE_NONE,
...     SELECT_MODE_ENERGY,
...     SELECT_MODE_LOWPASS,
... )

Режимы отбора коэффициентов:
=============================
- 'none': Без отбора (идеальная реконструкция)
- 'energy': Сохранение доли энергии (сжатие)
- 'lowpass': Сохранение низких частот (фильтрация)
"""
from __future__ import annotations

# =============================================================================
# БАЗОВЫЙ МОДУЛЬ
# =============================================================================

from .base import (
    # Базовый класс
    BaseTransform,

    # Константы
    SELECT_MODE_NONE,
    SELECT_MODE_ENERGY,
    SELECT_MODE_LOWPASS,
    VALID_SELECT_MODES,

    # Утилиты
    load_audio_safe,
    create_ola_window,
    finalize_ola,
    get_output_path,
    prepare_ola_buffers,
    select_coefficients_energy,
    select_coefficients_lowpass,
)


# =============================================================================
# ТРАНСФОРМАЦИИ
# =============================================================================

# FFT: Быстрое преобразование Фурье
from .fft import (
    FFTTransform,
    fft_transform_and_mp3,
    fft_forward,
    fft_inverse,
    apply_fft_coefficient_selection,
)

# DCT: Дискретное косинусное преобразование
from .dct import (
    DCTTransform,
    dct_transform_and_mp3,
    dct2,
    idct3,
    apply_dct_coefficient_selection,
)

# DWT: Вейвлет Хаара
from .dwt import (
    DWTTransform,
    wavelet_transform_and_mp3,
    haar_dwt_1level,
    haar_idwt_1level,
    dwt_decompose,
    dwt_reconstruct,
    flatten_dwt_coefficients,
    unflatten_dwt_coefficients,
    apply_dwt_coefficient_selection,
)

# FWHT: Преобразование Уолша-Адамара
from .fwht import (
    FWHTTransform,
    fwht_transform_and_mp3,
    fwht_ola,
    fwht,
    ifwht,
    fwht_ortho,
    ifwht_ortho,
    apply_fwht_coefficient_selection,
)

# Huffman-like: μ-law компандирование
from .huffman import (
    HuffmanLikeTransform,
    huffman_like_transform_and_mp3,
    mulaw_compress,
    mulaw_expand,
    quantize_uniform,
    huffman_like_process,
)

# Rosenbrock-like: Нелинейное сглаживание
from .rosenbrock import (
    RosenbrockLikeTransform,
    rosenbrock_like_transform_and_mp3,
    rosenbrock_nonlinear,
    normalize_peak,
    rosenbrock_process,
)

# Расширенные методы: Daubechies DWT и MDCT
from .extended import (
    DaubechiesDWTTransform,
    MDCTTransform,
    daubechies_dwt_and_mp3,
    mdct_and_mp3,
)


# =============================================================================
# СПИСОК ВСЕХ ДОСТУПНЫХ ТРАНСФОРМАЦИЙ
# =============================================================================

# Словарь {имя: класс} для динамического выбора метода
TRANSFORM_CLASSES = {
    "fft": FFTTransform,
    "dct": DCTTransform,
    "dwt": DWTTransform,
    "fwht": FWHTTransform,
    "huffman": HuffmanLikeTransform,
    "rosenbrock": RosenbrockLikeTransform,
    "daubechies": DaubechiesDWTTransform,
    "mdct": MDCTTransform,
}

# Словарь {имя: функция} для обратной совместимости
TRANSFORM_FUNCTIONS = {
    "fft": fft_transform_and_mp3,
    "dct": dct_transform_and_mp3,
    "dwt": wavelet_transform_and_mp3,
    "fwht": fwht_transform_and_mp3,
    "huffman": huffman_like_transform_and_mp3,
    "rosenbrock": rosenbrock_like_transform_and_mp3,
    "daubechies": daubechies_dwt_and_mp3,
    "mdct": mdct_and_mp3,
}


def get_transform(name: str):
    """Получить класс трансформации по имени.

    Параметры:
    ----------
    name : str
        Имя метода: 'fft', 'dct', 'dwt', 'fwht', 'huffman', 'rosenbrock'

    Возвращает:
    -----------
    type
        Класс трансформации (наследник BaseTransform)

    Исключения:
    -----------
    KeyError
        Если имя не найдено

    Пример:
    -------
    >>> TransformClass = get_transform("fft")
    >>> transform = TransformClass(block_size=2048)
    >>> out_path, time_sec = transform.process("audio.wav", "output/")
    """
    if name.lower() not in TRANSFORM_CLASSES:
        raise KeyError(
            f"Неизвестная трансформация: {name}. "
            f"Доступные: {list(TRANSFORM_CLASSES.keys())}"
        )
    return TRANSFORM_CLASSES[name.lower()]


def get_transform_function(name: str):
    """Получить функцию-обёртку трансформации по имени.

    Параметры:
    ----------
    name : str
        Имя метода: 'fft', 'dct', 'dwt', 'fwht', 'huffman', 'rosenbrock'

    Возвращает:
    -----------
    callable
        Функция трансформации (wav_path, out_dir, **params) -> (path, time)

    Пример:
    -------
    >>> transform_func = get_transform_function("fwht")
    >>> out_path, time_sec = transform_func("audio.wav", "output/")
    """
    if name.lower() not in TRANSFORM_FUNCTIONS:
        raise KeyError(
            f"Неизвестная трансформация: {name}. "
            f"Доступные: {list(TRANSFORM_FUNCTIONS.keys())}"
        )
    return TRANSFORM_FUNCTIONS[name.lower()]


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    # Базовый класс и константы
    "BaseTransform",
    "SELECT_MODE_NONE",
    "SELECT_MODE_ENERGY",
    "SELECT_MODE_LOWPASS",
    "VALID_SELECT_MODES",

    # Утилиты
    "load_audio_safe",
    "create_ola_window",
    "finalize_ola",
    "get_output_path",
    "prepare_ola_buffers",
    "select_coefficients_energy",
    "select_coefficients_lowpass",

    # Классы трансформаций
    "FFTTransform",
    "DCTTransform",
    "DWTTransform",
    "FWHTTransform",
    "HuffmanLikeTransform",
    "RosenbrockLikeTransform",
    "DaubechiesDWTTransform",
    "MDCTTransform",

    # Функции-обёртки
    "fft_transform_and_mp3",
    "dct_transform_and_mp3",
    "wavelet_transform_and_mp3",
    "fwht_transform_and_mp3",
    "huffman_like_transform_and_mp3",
    "rosenbrock_like_transform_and_mp3",
    "daubechies_dwt_and_mp3",
    "mdct_and_mp3",

    # Низкоуровневые функции FFT
    "fft_forward",
    "fft_inverse",
    "apply_fft_coefficient_selection",

    # Низкоуровневые функции DCT
    "dct2",
    "idct3",
    "apply_dct_coefficient_selection",

    # Низкоуровневые функции DWT
    "haar_dwt_1level",
    "haar_idwt_1level",
    "dwt_decompose",
    "dwt_reconstruct",
    "flatten_dwt_coefficients",
    "unflatten_dwt_coefficients",
    "apply_dwt_coefficient_selection",

    # Низкоуровневые функции FWHT
    "fwht",
    "ifwht",
    "fwht_ortho",
    "ifwht_ortho",
    "fwht_ola",
    "apply_fwht_coefficient_selection",

    # Низкоуровневые функции Huffman
    "mulaw_compress",
    "mulaw_expand",
    "quantize_uniform",
    "huffman_like_process",

    # Низкоуровневые функции Rosenbrock
    "rosenbrock_nonlinear",
    "normalize_peak",
    "rosenbrock_process",

    # Расширенные методы (Daubechies DWT и MDCT)
    "DaubechiesDWTTransform",
    "MDCTTransform",
    "daubechies_dwt_and_mp3",
    "mdct_and_mp3",

    # Утилиты выбора трансформации
    "TRANSFORM_CLASSES",
    "TRANSFORM_FUNCTIONS",
    "get_transform",
    "get_transform_function",
]
