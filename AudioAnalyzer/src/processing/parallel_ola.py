"""
Многопоточная OLA (Overlap-Add) обработка.

Назначение:
- Параллельная обработка блоков сигнала
- Ускорение обработки на многоядерных процессорах
- Сохранение обратной совместимости с однопоточным режимом

Алгоритм многопоточной OLA:
===========================
1. Сигнал разбивается на блоки с 50% перекрытием
2. Блоки группируются в чанки по num_threads штук
3. Каждый чанк обрабатывается параллельно в отдельном потоке
4. Результаты собираются и складываются (overlap-add)

Особенности:
-----------
- Thread-safe накопление результатов через блокировки
- Динамическое распределение нагрузки между потоками
- Сохранение порядка блоков для корректного OLA

Использование:
-------------
from processing.parallel_ola import parallel_ola_process

def transform_block(block: np.ndarray) -> np.ndarray:
    # Ваше преобразование
    return np.fft.irfft(np.fft.rfft(block))

result = parallel_ola_process(
    signal=x,
    transform_func=transform_block,
    block_size=2048,
    num_workers=4
)
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Any

import numpy as np

logger = logging.getLogger("audio.processing.parallel_ola")


# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

# Минимальное число блоков для параллельной обработки
MIN_BLOCKS_FOR_PARALLEL = 8

# Размер чанка блоков для одного воркера
BLOCKS_PER_CHUNK = 16

# Число воркеров по умолчанию (None = автоопределение)
DEFAULT_NUM_WORKERS = None


# =============================================================================
# РЕЗУЛЬТАТ ОБРАБОТКИ БЛОКА
# =============================================================================

@dataclass
class BlockResult:
    """Результат обработки одного блока.
    
    Атрибуты:
    ----------
    frame_index : int
        Индекс фрейма (блока)
    start_pos : int
        Начальная позиция в сигнале
    data : np.ndarray
        Обработанные данные блока
    weights : np.ndarray
        Веса окна для OLA
    processing_time : float
        Время обработки блока в секундах
    """
    frame_index: int
    start_pos: int
    data: np.ndarray
    weights: np.ndarray
    processing_time: float = 0.0


# =============================================================================
# ПАРАЛЛЕЛЬНАЯ OLA ОБРАБОТКА
# =============================================================================

def parallel_ola_process(
    signal: np.ndarray,
    transform_func: Callable[[np.ndarray], np.ndarray],
    block_size: int = 2048,
    num_workers: Optional[int] = DEFAULT_NUM_WORKERS,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> np.ndarray:
    """Параллельная OLA обработка сигнала.
    
    Разбивает сигнал на блоки, обрабатывает параллельно и
    собирает результаты методом overlap-add.
    
    Параметры:
    ----------
    signal : np.ndarray
        Входной сигнал (моно, float32)
    transform_func : Callable
        Функция преобразования блока (block -> processed_block)
    block_size : int
        Размер блока (степень двойки)
    num_workers : int, optional
        Число рабочих потоков (None = авто)
    progress_cb : Callable, optional
        Колбэк прогресса (fraction, message)
    
    Возвращает:
    -----------
    np.ndarray
        Обработанный сигнал
    
    Пример:
    -------
    >>> def my_transform(block):
    ...     return np.fft.irfft(np.fft.rfft(block))
    >>> result = parallel_ola_process(x, my_transform, block_size=2048)
    """
    n = len(signal)
    
    # Определяем параметры OLA
    hop = block_size // 2  # 50% перекрытие
    frames = max(1, int(np.ceil(max(0, n - block_size) / hop)) + 1)
    total_len = (frames - 1) * hop + block_size
    
    # Дополнение сигнала
    pad = total_len - n
    x_padded = np.pad(signal, (0, pad), mode="constant")
    
    # Создаём окно
    win = np.sqrt(np.hanning(block_size) + 1e-12).astype(np.float32)
    
    # Определяем, нужно ли параллелить
    use_parallel = frames >= MIN_BLOCKS_FOR_PARALLEL and num_workers != 1
    
    if use_parallel and num_workers is None:
        num_workers = min(4, max(1, (frames // BLOCKS_PER_CHUNK)))
    
    if progress_cb:
        progress_cb(0.0, f"OLA: подготовка ({frames} блоков)")
    
    if use_parallel and num_workers and num_workers > 1:
        result = _process_parallel(
            x_padded, win, hop, frames, block_size, total_len, n,
            transform_func, num_workers, progress_cb
        )
    else:
        result = _process_sequential(
            x_padded, win, hop, frames, block_size, total_len, n,
            transform_func, progress_cb
        )
    
    return result


def _process_sequential(
    x_padded: np.ndarray,
    win: np.ndarray,
    hop: int,
    frames: int,
    block_size: int,
    total_len: int,
    original_len: int,
    transform_func: Callable,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> np.ndarray:
    """Последовательная OLA обработка (оригинальный алгоритм)."""
    y_accum = np.zeros(total_len, dtype=np.float32)
    w_accum = np.zeros(total_len, dtype=np.float32)
    
    for fi in range(frames):
        i0 = fi * hop
        block = (x_padded[i0:i0 + block_size] * win).astype(np.float32)
        
        try:
            processed = transform_func(block)
        except Exception as e:
            logger.warning(f"Transform failed for frame {fi}: {e}")
            processed = block  # Fallback: вернуть исходный блок
        
        # Проверка размера
        if len(processed) != block_size:
            if len(processed) < block_size:
                processed = np.pad(processed, (0, block_size - len(processed)))
            else:
                processed = processed[:block_size]
        
        # Накопление
        y_accum[i0:i0 + block_size] += processed * win
        w_accum[i0:i0 + block_size] += win * win
        
        if progress_cb and fi % 50 == 0:
            progress_cb(0.1 + 0.85 * fi / frames, f"OLA: блок {fi+1}/{frames}")
    
    # Финализация
    result = np.divide(y_accum, np.maximum(w_accum, 1e-8))[:original_len]
    
    # Защита от клиппинга
    peak = np.max(np.abs(result)) + 1e-9
    if peak > 1.0:
        result = result / peak
    
    if progress_cb:
        progress_cb(1.0, "OLA: завершено")
    
    return result.astype(np.float32)


def _process_parallel(
    x_padded: np.ndarray,
    win: np.ndarray,
    hop: int,
    frames: int,
    block_size: int,
    total_len: int,
    original_len: int,
    transform_func: Callable,
    num_workers: int,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> np.ndarray:
    """Параллельная OLA обработка с ThreadPoolExecutor."""
    
    # Буферы для накопления (thread-safe через блокировку)
    y_accum = np.zeros(total_len, dtype=np.float32)
    w_accum = np.zeros(total_len, dtype=np.float32)
    accum_lock = threading.Lock()
    
    # Счётчик прогресса
    processed_frames = [0]
    progress_lock = threading.Lock()
    
    def process_block(frame_index: int) -> BlockResult:
        """Обработка одного блока."""
        t_start = time.perf_counter()
        i0 = frame_index * hop
        
        block = (x_padded[i0:i0 + block_size] * win).astype(np.float32)
        
        try:
            processed = transform_func(block)
        except Exception as e:
            logger.warning(f"Transform failed for frame {frame_index}: {e}")
            processed = block
        
        # Проверка размера
        if len(processed) != block_size:
            if len(processed) < block_size:
                processed = np.pad(processed, (0, block_size - len(processed)))
            else:
                processed = processed[:block_size]
        
        elapsed = time.perf_counter() - t_start
        
        return BlockResult(
            frame_index=frame_index,
            start_pos=i0,
            data=processed * win,
            weights=win * win,
            processing_time=elapsed
        )
    
    def accumulate_result(result: BlockResult) -> None:
        """Thread-safe накопление результата."""
        with accum_lock:
            y_accum[result.start_pos:result.start_pos + block_size] += result.data
            w_accum[result.start_pos:result.start_pos + block_size] += result.weights
        
        # Обновление прогресса
        with progress_lock:
            processed_frames[0] += 1
            if progress_cb and processed_frames[0] % 50 == 0:
                progress_cb(
                    0.1 + 0.85 * processed_frames[0] / frames,
                    f"OLA: блок {processed_frames[0]}/{frames}"
                )
    
    if progress_cb:
        progress_cb(0.05, f"OLA: запуск {num_workers} воркеров")
    
    # Параллельная обработка
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {}
        
        for fi in range(frames):
            future = executor.submit(process_block, fi)
            futures[future] = fi
        
        for future in as_completed(futures):
            try:
                result = future.result()
                accumulate_result(result)
            except Exception as e:
                fi = futures[future]
                logger.error(f"Frame {fi} failed: {e}")
    
    # Финализация
    result = np.divide(y_accum, np.maximum(w_accum, 1e-8))[:original_len]
    
    # Защита от клиппинга
    peak = np.max(np.abs(result)) + 1e-9
    if peak > 1.0:
        result = result / peak
    
    if progress_cb:
        progress_cb(1.0, "OLA: завершено")
    
    return result.astype(np.float32)


# =============================================================================
# BATCH PARALLEL PROCESSING
# =============================================================================

def batch_parallel_ola(
    signal: np.ndarray,
    transform_funcs: Dict[str, Callable[[np.ndarray], np.ndarray]],
    block_size: int = 2048,
    num_workers: Optional[int] = None,
    progress_cb: Optional[Callable[[float, str, str], None]] = None,
) -> Dict[str, np.ndarray]:
    """Параллельная обработка сигнала несколькими методами одновременно.
    
    Полезно для сравнения разных преобразований на одном сигнале.
    
    Параметры:
    ----------
    signal : np.ndarray
        Входной сигнал
    transform_funcs : Dict[str, Callable]
        Словарь {имя_метода: функция_преобразования}
    block_size : int
        Размер блока
    num_workers : int, optional
        Число воркеров для каждого метода
    progress_cb : Callable, optional
        Колбэк прогресса (fraction, message, method_name)
    
    Возвращает:
    -----------
    Dict[str, np.ndarray]
        Словарь {имя_метода: обработанный_сигнал}
    
    Пример:
    -------
    >>> funcs = {
    ...     'fft': lambda b: np.fft.irfft(np.fft.rfft(b)),
    ...     'dct': lambda b: idct(dct(b)),
    ... }
    >>> results = batch_parallel_ola(x, funcs)
    """
    results = {}
    results_lock = threading.Lock()
    
    def process_method(name: str, func: Callable) -> Tuple[str, np.ndarray]:
        """Обработка одним методом."""
        
        def wrapped_progress(frac: float, msg: str):
            if progress_cb:
                progress_cb(frac, msg, name)
        
        result = parallel_ola_process(
            signal, func, block_size, num_workers, wrapped_progress
        )
        return name, result
    
    # Определяем число воркеров
    if num_workers is None:
        num_workers = min(2, max(1, len(transform_funcs)))
    
    with ThreadPoolExecutor(max_workers=len(transform_funcs)) as executor:
        futures = {}
        
        for name, func in transform_funcs.items():
            future = executor.submit(process_method, name, func)
            futures[future] = name
        
        for future in as_completed(futures):
            try:
                name, result = future.result()
                with results_lock:
                    results[name] = result
                logger.info(f"Method {name} completed")
            except Exception as e:
                name = futures[future]
                logger.error(f"Method {name} failed: {e}")
    
    return results


# =============================================================================
# ADAPTIVE PARALLELISM
# =============================================================================

def get_optimal_workers(
    signal_length: int,
    block_size: int = 2048,
    max_workers: int = 8,
) -> int:
    """Определить оптимальное число воркеров для сигнала.
    
    Учитывает:
    - Длину сигнала (число блоков)
    - Максимальное доступное число потоков
    - Overhead от многопоточности
    
    Параметры:
    ----------
    signal_length : int
        Длина сигнала в отсчётах
    block_size : int
        Размер блока
    max_workers : int
        Максимальное число воркеров
    
    Возвращает:
    -----------
    int
        Оптимальное число воркеров
    """
    hop = block_size // 2
    frames = max(1, int(np.ceil(max(0, signal_length - block_size) / hop)) + 1)
    
    # Мало блоков - не имеет смысла параллелить
    if frames < MIN_BLOCKS_FOR_PARALLEL:
        return 1
    
    # Определяем по числу блоков
    # Каждый воркер должен обрабатывать минимум BLOCKS_PER_CHUNK блоков
    optimal = max(1, frames // BLOCKS_PER_CHUNK)
    
    # Ограничиваем максимумом
    optimal = min(optimal, max_workers)
    
    return optimal


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "parallel_ola_process",
    "batch_parallel_ola",
    "get_optimal_workers",
    "BlockResult",
    "MIN_BLOCKS_FOR_PARALLEL",
    "BLOCKS_PER_CHUNK",
    "DEFAULT_NUM_WORKERS",
]
