"""
Аудио-пайплайны обработки.

Назначение:
- Стандартное MP3 кодирование через ffmpeg
- Переэкспорт трансформаций из transforms/ для обратной совместимости
- Пакетный расчёт метрик качества

Обзор методов обработки:
========================

1. Стандартный MP3 - прямое кодирование WAV в MP3 через ffmpeg.
   Это базовый метод для сравнения.

2. FFT (Быстрое преобразование Фурье) - классический метод частотного анализа.
   Разлагает сигнал на синусоидальные компоненты.
   - Преимущества: хорошая частотная локализация, широкий спектр применения
   - Недостатки: требует комплексных вычислений

3. FWHT (Быстрое преобразование Уолша-Адамара) - использует только сложения/вычитания.
   Разлагает сигнал на функции Уолша (прямоугольные волны).
   - Преимущества: быстрые вычисления, хорош для бинарных сигналов

4. DCT (Дискретное косинусное преобразование) - используется в JPEG, MP3.
   - Преимущества: хорошее энергетическое сжатие

5. DWT (Дискретное вейвлет-преобразование, Хаар) - многоуровневое разложение.
   - Преимущества: хорошее временное и частотное разрешение

6. Huffman-like (μ-law компандирование) - нелинейное сжатие динамического диапазона.
   Сжимает громкие звуки меньше чем тихие.

7. Rosenbrock-like - эвристическое нелинейное преобразование для сглаживания.

Структура модуля:
=================
- audio_ops.py: стандартный MP3 + переэкспорт
- transforms/: реализации всех трансформаций
  - base.py: базовый класс и утилиты OLA
  - fft.py: FFT трансформация
  - dct.py: DCT трансформация
  - dwt.py: DWT (Хаар) трансформация
  - fwht.py: FWHT трансформация
  - huffman.py: Huffman-like трансформация
  - rosenbrock.py: Rosenbrock-like трансформация
- codecs.py: FFmpeg взаимодействия
- metrics.py: метрики качества
- utils.py: вспомогательные функции
- api.py: устаревший фасад совместимости

Использование:
==============
>>> from processing.audio_ops import (
...     standard_convert_to_mp3,
...     fft_transform_and_mp3,
...     fwht_transform_and_mp3,
... )
>>>
>>> # Стандартное MP3
>>> out_path, time_sec = standard_convert_to_mp3("audio.wav", "output/")
>>>
>>> # FFT с отбором по энергии
>>> out_path, time_sec = fft_transform_and_mp3(
...     "audio.wav", "output/",
...     select_mode="energy",
...     keep_energy_ratio=0.8
... )

Внешние библиотеки:
-------------------
- numpy: численные операции
- logging: диагностические сообщения
"""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

# Импорт из codecs для Standard MP3
from .codecs import (
    ensure_ffmpeg_available,
    load_wav_mono,
    decode_audio_to_mono,
    standard_convert_to_mp3 as _standard_convert_to_mp3,
    get_audio_meta,
)

# Импорт метрик
from .metrics import compute_metrics_batch as _compute_metrics_batch_internal

# Переэкспорт всех трансформаций из transforms/
from .transforms import (
    # Классы трансформаций
    FFTTransform,
    DCTTransform,
    DWTTransform,
    FWHTTransform,
    HuffmanLikeTransform,
    RosenbrockLikeTransform,
    DaubechiesDWTTransform,
    MDCTTransform,

    # Функции-обёртки
    fft_transform_and_mp3,
    dct_transform_and_mp3,
    wavelet_transform_and_mp3,
    fwht_transform_and_mp3,
    huffman_like_transform_and_mp3,
    rosenbrock_like_transform_and_mp3,
    daubechies_dwt_and_mp3,
    mdct_and_mp3,

    # Утилиты (для совместимости)
    load_audio_safe,
    create_ola_window,
    finalize_ola,
)

# Переэкспорт метрик для обратной совместимости
from .metrics import (
    compute_snr_db,
    compute_rmse,
    compute_si_sdr_db,
    compute_lsd_db,
    compute_spectral_convergence,
    compute_spectral_centroid_diff_hz,
    compute_spectral_cosine_similarity,
)

logger = logging.getLogger("audio.processing")


# =============================================================================
# СТАНДАРТНОЕ ПРЕОБРАЗОВАНИЕ MP3
# =============================================================================

def standard_convert_to_mp3(
    wav_path: str,
    out_dir: str,
    bitrate: str = "192k"
) -> Tuple[str, float]:
    """Обёртка над codecs.standard_convert_to_mp3 с логированием.

    Прямое кодирование WAV в MP3 через FFmpeg без предварительной обработки.
    Используется как базовый метод для сравнения с другими трансформациями.

    Параметры:
    ----------
    wav_path : str
        Путь к исходному WAV файлу
    out_dir : str
        Директория для сохранения MP3
    bitrate : str
        Битрейт MP3 (например, '192k', '128k', '320k')

    Возвращает:
    -----------
    Tuple[str, float]
        (путь к MP3, время обработки в секундах)

    Пример:
    -------
    >>> out_path, time_sec = standard_convert_to_mp3("audio.wav", "output/")
    >>> print(f"Сохранено в {out_path} за {time_sec:.2f} сек")
    """
    logger.info("standard_convert_to_mp3 start path=%s bitrate=%s", wav_path, bitrate)
    out, dt = _standard_convert_to_mp3(wav_path, out_dir, bitrate)
    logger.info("standard_convert_to_mp3 done path=%s out=%s dt=%.3f", wav_path, out, dt)
    return out, dt


# =============================================================================
# ПАКЕТНЫЙ РАСЧЁТ МЕТРИК
# =============================================================================

def _compute_metrics_batch(
    original_wav: str,
    items: List[Tuple[str, str, float]],
    progress_cb=None,
    weights=None,
) -> List[Dict]:
    """Посчитать метрики качества для набора результатов.

    Для каждого обработанного файла вычисляет:
    - Размер файла
    - SNR, RMSE, SI-SDR, LSD, Spectral Convergence
    - Spectral Centroid Difference, Cosine Similarity
    - STOI, PESQ, MOS
    - Общий score (взвешенный)

    Параметры:
    ----------
    original_wav : str
        Путь к исходному WAV (референс)
    items : List[Tuple[str, str, float]]
        Список кортежей (variant, path_to_mp3, time_sec)
    progress_cb : callable(i, total, msg) или None
        Callback для отображения прогресса расчёта метрик
    weights : dict или None
        Словарь весов метрик. Если None — используются веса по умолчанию.

    Возвращает:
    -----------
    List[Dict]
        Список словарей с полями размера, метрик, времени и score
    """
    return _compute_metrics_batch_internal(
        original_wav,
        items,
        load_wav_func=load_wav_mono,
        decode_audio_func=decode_audio_to_mono,
        get_meta_func=get_audio_meta,
        progress_cb=progress_cb,
        weights=weights,
    )


def compare_results(
    original_wav: str,
    std_mp3: str,
    fwht_mp3: str,
    t_std: float,
    t_fwht: float,
    fft_mp3: str = None,
    t_fft: float = None,
) -> List[Dict]:
    """СОВМЕСТИМОСТЬ: старая сигнатура для сравнения результатов.

    Сохраняет обратную совместимость с кодом, использующим
    старую сигнатуру функции compare_results.

    Параметры:
    ----------
    original_wav : str
        Путь к исходному WAV
    std_mp3 : str
        Путь к стандартному MP3
    fwht_mp3 : str
        Путь к FWHT MP3
    t_std : float
        Время обработки стандартного MP3
    t_fwht : float
        Время обработки FWHT MP3
    fft_mp3 : str, optional
        Путь к FFT MP3
    t_fft : float, optional
        Время обработки FFT MP3

    Возвращает:
    -----------
    List[Dict]
        Список результатов с метриками

    Примечание:
    -----------
    Рекомендуется использовать _compute_metrics_batch напрямую
    для произвольного числа методов.
    """
    items: List[Tuple[str, str, float]] = [
        ("Стандартный MP3", std_mp3, float(t_std)),
        ("FWHT MP3", fwht_mp3, float(t_fwht)),
    ]
    if fft_mp3 is not None:
        items.append(("FFT MP3", fft_mp3, float(t_fft or float("nan"))))
    return _compute_metrics_batch(original_wav, items)


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    # Стандартный MP3
    "standard_convert_to_mp3",

    # Трансформации (переэкспорт из transforms/)
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

    # Метрики (переэкспорт)
    "compute_snr_db",
    "compute_rmse",
    "compute_si_sdr_db",
    "compute_lsd_db",
    "compute_spectral_convergence",
    "compute_spectral_centroid_diff_hz",
    "compute_spectral_cosine_similarity",

    # Пакетный расчёт
    "_compute_metrics_batch",
    "compare_results",
]
