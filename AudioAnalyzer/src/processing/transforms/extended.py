"""
Расширенные методы преобразования: Daubechies DWT и MDCT.

Назначение:
- Daubechies DWT (db2-db10): более гладкие вейвлеты для лучшего частотного разрешения
- MDCT: Modified DCT для аудио кодирования (используется в MP3/AAC)

Теоретические основы:
=====================

Daubechies DWT:
---------------
Вейвлеты Добечи (dbN) - семейство ортогональных вейвлетов с компактным носителем.
В отличие от вейвлета Хаара, они обеспечивают:
- Более гладкие базисные функции
- Лучшую локализацию в частотной области
- Более высокую степень исчезающих моментов

Параметр N (db2, db4, db8, db10):
- db2: 2 коэффициента, минимальная гладкость
- db4: 4 коэффициента, хороший баланс гладкость/локализация
- db8: 8 коэффициентов, высокая гладкость
- db10: 10 коэффициентов, максимальная гладкость

MDCT (Modified Discrete Cosine Transform):
------------------------------------------
Используется в MP3, AAC, Ogg Vorbis для частотного кодирования.
Особенности:
- Перекрытие 50% между блоками для устранения граничных артефактов
- Критическая выборка (N коэффициентов для N отсчётов)
- Хорошее частотное разрешение

Формула MDCT:
X_k = sum_{n=0}^{2N-1} x_n * cos(pi/N * (n + 0.5 + N/2) * (k + 0.5))

Внешние библиотеки:
-------------------
- numpy: численные операции
- scipy.signal: вейвлет-фильтры
"""
from __future__ import annotations

import time
import logging
from typing import Callable, List, Optional, Tuple, Dict, Any

import numpy as np

try:
    from scipy.signal import dlti, dlsim
    from scipy.linalg import orth
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

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

logger = logging.getLogger("audio.processing.transforms.extended")


# =============================================================================
# DAUBECHIES WAVELET FILTERS
# =============================================================================

# Коэффициенты фильтров Добечи (low-pass decomposition, dec_lo)
# Источник: PyWavelets (pywt.Wavelet), подтверждённые эталонные значения
# Соответствуют: Daubechies, I. (1992). Ten Lectures on Wavelets

DAUBECHIES_FILTERS: Dict[str, np.ndarray] = {
    "db2": np.array([
        -0.1294095225512603,
         0.2241438680420134,
         0.8365163037378079,
         0.4829629131445342
    ]),
    "db4": np.array([
        -0.010597401784997278,
         0.03288301166688520,
         0.03084138183556076,
        -0.18703481171909309,
        -0.027983769416859854,
         0.63088076792985890,
         0.71484657055291570,
         0.23037781330889650
    ]),
    "db6": np.array([
        -0.001077301085308480,
         0.004777257510945511,
         0.000553842201161496,
        -0.03158203931748603,
         0.02752286553030573,
         0.09750160558732304,
        -0.12976686756726190,
        -0.22626469396543980,
         0.31525035170919760,
         0.75113390802109540,
         0.49462389039845310,
         0.11154074335010950
    ]),
    "db8": np.array([
        -0.000117476786002396,
         0.000675449406450569,
        -0.000391740373376947,
        -0.004870352993451574,
         0.008746094047405777,
         0.013981027917398280,
        -0.044088253930794750,
        -0.017369301001807550,
         0.12874742662047850,
         0.000472484573913283,
        -0.28401554296154690,
        -0.015829105256349310,
         0.58535468365420670,
         0.67563073629728980,
         0.31287159091429990,
         0.054415842243104010
    ]),
}

# Значения по умолчанию для уровней декомпозиции
DEFAULT_DWT_LEVELS: Dict[str, int] = {
    "db2": 6,
    "db4": 5,
    "db6": 4,
    "db8": 4,
}


def get_daubechies_filter(wavelet: str = "db4") -> np.ndarray:
    """Получить коэффициенты фильтра Добечи.
    
    Параметры:
    ----------
    wavelet : str
        Имя вейвлета ('db2', 'db4', 'db6', 'db8')
        
    Возвращает:
    -----------
    np.ndarray
        Коэффициенты low-pass фильтра декомпозиции
    """
    if wavelet not in DAUBECHIES_FILTERS:
        logger.warning(f"Unknown wavelet {wavelet}, using db4")
        wavelet = "db4"
    return DAUBECHIES_FILTERS[wavelet].astype(np.float64)


def make_qmf_pair(h0: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Создать квадруплет QMF фильтров.
    
    Из low-pass декомпозиции (h0) создаём:
    - g0: high-pass декомпозиция
    - h1: low-pass реконструкция
    - g1: high-pass реконструкция
    
    Параметры:
    ----------
    h0 : np.ndarray
        Low-pass декомпозиционный фильтр
        
    Возвращает:
    -----------
    Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
        (h0, g0, h1, g1) - квадруплет фильтров
    """
    # High-pass decomposition (dec_hi)
    # Правильная формула (верифицирована по pywt):
    # dec_hi[n] = (-1)^(n+1) * h0[N-1-n]
    # Ранее использовалась неверная формула: (-1)^(N-1-n) * h0[n]
    N = len(h0)
    g0 = np.array([((-1) ** (n + 1)) * h0[N - 1 - n] for n in range(N)], dtype=np.float64)

    # Low-pass reconstruction (rec_lo): h1 = h0 reversed
    h1 = h0[::-1].copy()

    # High-pass reconstruction (rec_hi): g1[n] = (-1)^n * h0[n]
    # Ключевое исправление: ранее использовалось g0[::-1], что давало неправильный знак
    g1 = np.array([((-1) ** n) * h0[n] for n in range(N)], dtype=np.float64)

    return h0, g0, h1, g1


def dwt_1level_daubechies(
    x: np.ndarray,
    h0: np.ndarray,
    g0: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Одноуровневое DWT с произвольным фильтром (numpy-оптимизация).
    
    Использует np.convolve + downsampling вместо Python-циклов.
    
    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал
    h0 : np.ndarray
        Low-pass фильтр
    g0 : np.ndarray
        High-pass фильтр
        
    Возвращает:
    -----------
    Tuple[np.ndarray, np.ndarray]
        (A, D) — аппроксимация и детали
    """
    # Свертка + downsampling через numpy (в ~100x быстрее Python-циклов)
    # Downsampling offset = 1 для корректного согласования с обратным преобразованием
    L = len(h0)
    conv_lo = np.convolve(x.astype(np.float64), h0.astype(np.float64))
    conv_hi = np.convolve(x.astype(np.float64), g0.astype(np.float64))
    # Берём каждый 2-й элемент начиная с offset=1 (без обрезки длины)
    a = conv_lo[1::2].astype(np.float32)
    d = conv_hi[1::2].astype(np.float32)
    return a, d


def idwt_1level_daubechies(
    a: np.ndarray,
    d: np.ndarray,
    h1: np.ndarray,
    g1: np.ndarray,
    orig_len: int
) -> np.ndarray:
    """Обратное одноуровневое DWT (numpy-оптимизация).
    
    Upsampling + свертка через numpy вместо Python-циклов.
    
    Параметры:
    ----------
    a : np.ndarray
        Аппроксимация
    d : np.ndarray
        Детали
    h1 : np.ndarray
        Low-pass реконструкционный фильтр
    g1 : np.ndarray
        High-pass реконструкционный фильтр
    orig_len : int
        Ожидаемая длина реконструкции
        
    Возвращает:
    -----------
    np.ndarray
        Восстановленный сигнал
    """
    # Upsampling: вставляем нули между отсчётами, затем свёртка
    # x[n] = sum_k a[k]*h1[n-2k] + d[k]*g1[n-2k] = conv(up_a, h1)[n] + conv(up_d, g1)[n]
    up_a = np.zeros(2 * len(a), dtype=np.float64)
    up_a[::2] = a.astype(np.float64)
    up_d = np.zeros(2 * len(d), dtype=np.float64)
    up_d[::2] = d.astype(np.float64)
    
    x = np.convolve(up_a, h1.astype(np.float64)) + np.convolve(up_d, g1.astype(np.float64))
    # Filter delay compensation: fwd_offset + inv_offset = L - 1
    # При fwd_offset = 1, inv_offset = L - 2
    L = len(h1)
    inv_offset = L - 2
    return x[inv_offset:inv_offset + orig_len].astype(np.float32)


def dwt_decompose_daubechies(
    x: np.ndarray,
    wavelet: str,
    levels: int
) -> List[np.ndarray]:
    """Многоуровневое DWT разложение Добечи.
    
    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал
    wavelet : str
        Имя вейвлета ('db2', 'db4', 'db6', 'db8')
    levels : int
        Число уровней
        
    Возвращает:
    -----------
    List[np.ndarray]
        [AL, DL, DL-1, ..., D1]
    """
    h0 = get_daubechies_filter(wavelet)
    h0, g0, h1, g1 = make_qmf_pair(h0)
    
    coeffs = []
    a = x.astype(np.float64)
    
    for _ in range(levels):
        if len(a) < len(h0) * 2:
            logger.warning("Signal too short for more levels")
            break
        a, d = dwt_1level_daubechies(a, h0, g0)
        coeffs.append(d.astype(np.float32))
    
    coeffs.append(a.astype(np.float32))
    return coeffs


def dwt_reconstruct_daubechies(
    coeffs: List[np.ndarray],
    wavelet: str,
    orig_len: int
) -> np.ndarray:
    """Реконструкция сигнала из коэффициентов DWT Добечи.
    
    Параметры:
    ----------
    coeffs : List[np.ndarray]
        Коэффициенты [AL, DL, ..., D1]
    wavelet : str
        Имя вейвлета
    orig_len : int
        Ожидаемая длина
        
    Возвращает:
    -----------
    np.ndarray
        Восстановленный сигнал
    """
    h0 = get_daubechies_filter(wavelet)
    _, _, h1, g1 = make_qmf_pair(h0)
    
    a = coeffs[-1].astype(np.float64)
    
    for i in range(len(coeffs) - 2, -1, -1):
        d = coeffs[i].astype(np.float64)
        
        # Выравнивание длин: дополняем нулями более короткий массив
        if len(a) != len(d):
            if len(d) < len(a):
                d = np.pad(d, (0, len(a) - len(d)))
            else:
                a = np.pad(a, (0, len(d) - len(a)))
        
        expected_len = len(a) * 2
        a = idwt_1level_daubechies(a, d, h1, g1, expected_len)
    
    return a[:orig_len].astype(np.float32)


# =============================================================================
# MDCT (Modified Discrete Cosine Transform)
# =============================================================================

def mdct_window(N: int) -> np.ndarray:
    """Создать окно синуса для MDCT.
    
    w[n] = sin(pi * (n + 0.5) / (2N))
    
    Параметры:
    ----------
    N : int
        Размер окна (длина MDCT блока)
        
    Возвращает:
    -----------
    np.ndarray
        Окно длиной 2N
    """
    n = np.arange(2 * N)
    return np.sin(np.pi * (n + 0.5) / (2 * N))


def mdct(x: np.ndarray, N: int = 1024) -> np.ndarray:
    """Modified Discrete Cosine Transform (numpy-оптимизация, O(N^2) вместо O(N^3)).
    
    MDCT с 50% перекрытием. Для блока длиной 2N возвращает N коэффициентов.
    
    Параметры:
    ----------
    x : np.ndarray
        Входной сигнал (длина должна быть кратна N)
    N : int
        Размер MDCT блока
        
    Возвращает:
    -----------
    np.ndarray
        MDCT коэффициенты (n_blocks x N)
    """
    L = len(x)
    n_blocks = max(1, (L + N - 1) // N)  # ceiling division
    # Паддинг: последний блок нужен длиной 2N, начинающийся с (n_blocks-1)*N
    padded_len = (n_blocks - 1) * N + 2 * N  # = (n_blocks + 1) * N
    if L < padded_len:
        x = np.pad(x, (0, padded_len - L))
        L = len(x)
    
    win = mdct_window(N)
    
    # Предвычисляем матрицу базисных функций MDCT (N x 2N)
    # M[k, n] = cos(pi/N * (n + 0.5 + N/2) * (k + 0.5))
    n_idx = np.arange(2 * N, dtype=np.float64)
    k_idx = np.arange(N, dtype=np.float64)
    M = np.cos(np.pi / N * np.outer(k_idx + 0.5, n_idx + 0.5 + N / 2))
    
    coeffs = np.zeros((n_blocks, N), dtype=np.float32)
    
    for b in range(n_blocks):
        start = b * N
        block = x[start:start + 2 * N].astype(np.float64) * win
        coeffs[b] = (M @ block).astype(np.float32)
    
    return coeffs


def imdct(coeffs: np.ndarray, N: int = 1024) -> np.ndarray:
    """Inverse Modified Discrete Cosine Transform (numpy-оптимизация, O(N^2) вместо O(N^3)).
    
    Параметры:
    ----------
    coeffs : np.ndarray
        MDCT коэффициенты (n_blocks x N)
    N : int
        Размер MDCT блока
        
    Возвращает:
    -----------
    np.ndarray
        Восстановленный сигнал
    """
    n_blocks = coeffs.shape[0]
    win = mdct_window(N)
    
    # Предвычисляем транспонированную матрицу базисных функций IMDCT
    n_idx = np.arange(2 * N, dtype=np.float64)
    k_idx = np.arange(N, dtype=np.float64)
    M_T = np.cos(np.pi / N * np.outer(n_idx + 0.5 + N / 2, k_idx + 0.5))  # 2N x N
    
    # Выходной массив с перекрытием
    out_len = (n_blocks + 1) * N
    x = np.zeros(out_len, dtype=np.float32)
    
    for b in range(n_blocks):
        # IMDCT: block = M_T @ coeffs[b] * (2.0/N)
        block = (M_T @ coeffs[b].astype(np.float64) * (2.0 / N)).astype(np.float32)
        
        # Применение окна и overlap-add
        block *= win
        
        start = b * N
        x[start:start + 2 * N] += block
    
    return x


# =============================================================================
# КЛАССЫ ТРАНСФОРМАЦИЙ
# =============================================================================

class DaubechiesDWTTransform(BaseTransform):
    """DWT с вейвлетами Добечи (db2, db4, db6, db8)."""

    NAME = "Daubechies DWT"
    DESCRIPTION = "Дискретное вейвлет-преобразование Добечи"
    FILE_SUFFIX = "daubechies"

    SUPPORTED_WAVELETS = ["db2", "db4", "db6", "db8"]

    def __init__(
        self,
        block_size: int = 2048,
        bitrate: str = "192k",
        select_mode: str = SELECT_MODE_NONE,
        keep_energy_ratio: float = 1.0,
        sequency_keep_ratio: float = 1.0,
        wavelet: str = "db4",
        levels: Optional[int] = None,
    ):
        """Инициализация.

        Параметры:
        ----------
        wavelet : str
            Тип вейвлета ('db2', 'db4', 'db6', 'db8')
        levels : int, optional
            Число уровней декомпозиции (авто, если None)
        """
        super().__init__(
            block_size=block_size,
            bitrate=bitrate,
            select_mode=select_mode,
            keep_energy_ratio=keep_energy_ratio,
            sequency_keep_ratio=sequency_keep_ratio,
        )

        # Валидация вейвлета
        if wavelet not in self.SUPPORTED_WAVELETS:
            logger.warning(f"Unsupported wavelet {wavelet}, using db4")
            wavelet = "db4"
        self.wavelet = wavelet

        # Автовыбор уровней
        if levels is None:
            levels = DEFAULT_DWT_LEVELS.get(wavelet, 4)
        self.levels = max(1, int(levels))

    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """Применить Daubechies DWT к блоку."""
        N = len(block)

        # Разложение
        coeffs = dwt_decompose_daubechies(block, self.wavelet, self.levels)

        # Сборка в вектор
        flat = np.concatenate(coeffs[::-1])

        # Отбор коэффициентов
        if self.select_mode == SELECT_MODE_ENERGY and self.keep_energy_ratio < 1.0:
            magsq = flat * flat
            order = np.argsort(magsq)[::-1]
            cumsum = np.cumsum(magsq[order])
            total_e = cumsum[-1] + 1e-12
            need = self.keep_energy_ratio * total_e
            keep_n = int(np.searchsorted(cumsum, need, side="left")) + 1
            mask = np.zeros_like(flat, dtype=bool)
            mask[order[:keep_n]] = True
            flat = np.where(mask, flat, 0.0)
        elif self.select_mode == SELECT_MODE_LOWPASS and self.sequency_keep_ratio < 1.0:
            k = max(1, int(self.sequency_keep_ratio * len(flat)))
            flat[k:] = 0.0

        # Реконструкция
        coeffs_back = []
        ptr = 0
        # Порядок: A, D_levels-1, ..., D0
        a_len = len(coeffs[-1])
        coeffs_back.append(flat[ptr:ptr + a_len].astype(np.float32))
        ptr += a_len
        for i in range(self.levels):
            d_len = len(coeffs[self.levels - 1 - i])
            coeffs_back.append(flat[ptr:ptr + d_len].astype(np.float32))
            ptr += d_len

        rec = dwt_reconstruct_daubechies(coeffs_back, self.wavelet, N)
        return rec

    def process(
        self,
        wav_path: str,
        out_dir: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Полный пайплайн обработки."""
        t0 = time.perf_counter()
        self.log_start(
            wav_path,
            wavelet=self.wavelet,
            levels=self.levels,
            mode=self.select_mode,
        )
        ensure_ffmpeg_available()

        if progress_cb:
            progress_cb(0.0, f"DWT-{self.wavelet}: загрузка")

        x, sr = load_audio_safe(wav_path)
        n = len(x)
        N = self.block_size

        win = create_ola_window(N)
        frames, hop, total_len, y_accum, w_accum = prepare_ola_buffers(n, N)

        pad = total_len - n
        x_padded = np.pad(x, (0, pad), mode="constant")

        for fi in range(frames):
            i0 = fi * hop
            blk = (x_padded[i0 : i0 + N] * win).astype(np.float32)
            rec = self.transform_block(blk) * win
            y_accum[i0 : i0 + N] += rec
            w_accum[i0 : i0 + N] += win * win

            if progress_cb:
                progress_cb(
                    min(0.95, 0.1 + 0.8 * (fi + 1) / frames),
                    f"DWT-{self.wavelet}: блок {fi+1}/{frames}"
                )

        y = finalize_ola(y_accum, w_accum, n)
        out_mp3 = get_output_path(wav_path, out_dir, f"{self.FILE_SUFFIX}_{self.wavelet}")

        if progress_cb:
            progress_cb(0.97, f"DWT-{self.wavelet}: кодирование")
        encode_pcm_to_mp3(y, sr, out_mp3, self.bitrate, profile="vbr")

        dt = time.perf_counter() - t0
        if progress_cb:
            progress_cb(1.0, f"DWT-{self.wavelet}: готово")

        self.log_done(out_mp3, dt)
        return out_mp3, dt


class MDCTTransform(BaseTransform):
    """MDCT (Modified DCT) трансформация.

    MDCT используется в MP3/AAC кодировании и обеспечивает
    хорошее частотное разрешение с критической выборкой.
    """

    NAME = "MDCT"
    DESCRIPTION = "Modified Discrete Cosine Transform"
    FILE_SUFFIX = "mdct"

    def __init__(
        self,
        block_size: int = 1024,
        bitrate: str = "192k",
        select_mode: str = SELECT_MODE_NONE,
        keep_energy_ratio: float = 1.0,
        sequency_keep_ratio: float = 1.0,
    ):
        """Инициализация MDCT.

        Параметры:
        ----------
        block_size : int
            Размер MDCT блока (типичные: 512, 1024, 2048)
        """
        super().__init__(
            block_size=block_size,
            bitrate=bitrate,
            select_mode=select_mode,
            keep_energy_ratio=keep_energy_ratio,
            sequency_keep_ratio=sequency_keep_ratio,
        )

        # MDCT block size должен быть степенью двойки
        N = block_size
        if N & (N - 1) != 0:
            # Найти ближайшую степень двойки
            N = 1 << (N - 1).bit_length()
            logger.info(f"MDCT block_size adjusted to {N}")
        self.mdct_size = N

    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """MDCT не использует блочную обработку как DWT.

        MDCT использует overlap-add с окнами 2N.
        """
        # Это заглушка - MDCT обрабатывается в process()
        return block

    def process(
        self,
        wav_path: str,
        out_dir: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Полный пайплайн MDCT обработки."""
        t0 = time.perf_counter()
        self.log_start(wav_path, mdct_size=self.mdct_size, mode=self.select_mode)
        ensure_ffmpeg_available()

        if progress_cb:
            progress_cb(0.0, "MDCT: загрузка")

        x, sr = load_audio_safe(wav_path)
        N = self.mdct_size

        # MDCT с overlap-add
        if progress_cb:
            progress_cb(0.1, "MDCT: прямое преобразование")

        coeffs = mdct(x, N)

        if progress_cb:
            progress_cb(0.4, "MDCT: отбор коэффициентов")

        # Отбор коэффициентов
        if self.select_mode == SELECT_MODE_ENERGY and self.keep_energy_ratio < 1.0:
            flat = coeffs.flatten()
            magsq = flat * flat
            order = np.argsort(magsq)[::-1]
            cumsum = np.cumsum(magsq[order])
            total_e = cumsum[-1] + 1e-12
            need = self.keep_energy_ratio * total_e
            keep_n = int(np.searchsorted(cumsum, need, side="left")) + 1
            mask = np.zeros_like(flat, dtype=bool)
            mask[order[:keep_n]] = True
            flat = np.where(mask, flat, 0.0)
            coeffs = flat.reshape(coeffs.shape)
        elif self.select_mode == SELECT_MODE_LOWPASS and self.sequency_keep_ratio < 1.0:
            k = max(1, int(self.sequency_keep_ratio * coeffs.shape[1]))
            coeffs[:, k:] = 0.0

        if progress_cb:
            progress_cb(0.6, "MDCT: обратное преобразование")

        # Обратное MDCT
        y = imdct(coeffs, N)

        # Нормализация
        if np.max(np.abs(y)) > 0:
            y = y / np.max(np.abs(y)) * 0.95

        out_mp3 = self.get_output_path(wav_path, out_dir)

        if progress_cb:
            progress_cb(0.9, "MDCT: кодирование")
        encode_pcm_to_mp3(y, sr, out_mp3, self.bitrate, profile="vbr")

        dt = time.perf_counter() - t0
        if progress_cb:
            progress_cb(1.0, "MDCT: готово")

        self.log_done(out_mp3, dt)
        return out_mp3, dt


# =============================================================================
# ФУНКЦИИ-ОБЁРТКИ
# =============================================================================

def daubechies_dwt_and_mp3(
    wav_path: str,
    out_dir: str,
    *,
    block_size: int = 2048,
    bitrate: str = "192k",
    select_mode: str = "none",
    keep_energy_ratio: float = 1.0,
    sequency_keep_ratio: float = 1.0,
    wavelet: str = "db4",
    levels: Optional[int] = None,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> Tuple[str, float]:
    """Daubechies DWT с OLA → MP3.

    Параметры:
    ----------
    wavelet : str
        Тип вейвлета ('db2', 'db4', 'db6', 'db8')
    levels : int, optional
        Число уровней декомпозиции (авто)

    Возвращает:
    -----------
    Tuple[str, float]
        (путь к MP3, время в секундах)
    """
    transform = DaubechiesDWTTransform(
        block_size=block_size,
        bitrate=bitrate,
        select_mode=select_mode,
        keep_energy_ratio=keep_energy_ratio,
        sequency_keep_ratio=sequency_keep_ratio,
        wavelet=wavelet,
        levels=levels,
    )
    return transform.process(wav_path, out_dir, progress_cb)


def mdct_and_mp3(
    wav_path: str,
    out_dir: str,
    *,
    block_size: int = 1024,
    bitrate: str = "192k",
    select_mode: str = "none",
    keep_energy_ratio: float = 1.0,
    sequency_keep_ratio: float = 1.0,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> Tuple[str, float]:
    """MDCT → MP3.

    Возвращает:
    -----------
    Tuple[str, float]
        (путь к MP3, время в секундах)
    """
    transform = MDCTTransform(
        block_size=block_size,
        bitrate=bitrate,
        select_mode=select_mode,
        keep_energy_ratio=keep_energy_ratio,
        sequency_keep_ratio=sequency_keep_ratio,
    )
    return transform.process(wav_path, out_dir, progress_cb)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "DaubechiesDWTTransform",
    "MDCTTransform",
    "daubechies_dwt_and_mp3",
    "mdct_and_mp3",
    "DAUBECHIES_FILTERS",
    "get_daubechies_filter",
    "mdct",
    "imdct",
]
