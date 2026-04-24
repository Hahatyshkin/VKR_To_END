"""
Фоновый обработчик аудио для UI.

Назначение:
- Выполнение пайплайнов обработки аудио в отдельном потоке.
- Сбор метрик качества для всех методов.
- Прогресс и ETA для пользовательского интерфейса.
- Поддержка параллельной обработки методов.

Внешние зависимости: PySide6 (QObject, Signal, Slot), processing.audio_ops.
"""
from __future__ import annotations

import logging
import os
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Protocol
from abc import ABC, abstractmethod

from PySide6.QtCore import QObject, Signal, Slot

# Импорт констант прогресса
from .services.config import (
    PROGRESS_RANGES,
    PROGRESS_BASE,
    PROGRESS_RANGE,
    SPECTRUM_MAX_POINTS,
)

# Импорт функций обработки с поддержкой разных режимов запуска
try:
    from processing.audio_ops import (
        fwht_transform_and_mp3,
        fft_transform_and_mp3,
        dct_transform_and_mp3,
        wavelet_transform_and_mp3,
        huffman_like_transform_and_mp3,
        rosenbrock_like_transform_and_mp3,
        _compute_metrics_batch,
        standard_convert_to_mp3,
    )
except ImportError:
    from src.processing.audio_ops import (
        fwht_transform_and_mp3,
        fft_transform_and_mp3,
        dct_transform_and_mp3,
        wavelet_transform_and_mp3,
        huffman_like_transform_and_mp3,
        rosenbrock_like_transform_and_mp3,
        _compute_metrics_batch,
        standard_convert_to_mp3,
    )


logger = logging.getLogger("ui_new.worker")


# =============================================================================
# РЕЗУЛЬТАТ ОБРАБОТКИ
# =============================================================================

@dataclass
class ResultRow:
    """Структурированный результат обработки одного метода."""
    source: str
    genre: Optional[str]
    variant: str
    path: str
    size_bytes: int
    lsd_db: float
    snr_db: float
    spec_conv: float
    rmse: float
    si_sdr_db: float
    spec_centroid_diff_hz: float
    spec_cosine: float
    stoi: float
    pesq: float
    mos: float
    score: float
    time_sec: float

    @property
    def size_mb(self) -> float:
        """Размер файла в мегабайтах."""
        return self.size_bytes / (1024 * 1024)


# =============================================================================
# ПРОТОКОЛ И БАЗОВЫЙ КЛАСС МЕТОДА
# =============================================================================

class TransformMethod(Protocol):
    """Протокол для метода трансформации."""
    
    name: str
    display_name: str
    stage_index: int
    
    def execute(
        self,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Выполнить трансформацию.
        
        Возвращает: (путь к MP3, время в секундах)
        """
        ...


@dataclass
class MethodResult:
    """Результат выполнения метода."""
    method_name: str
    mp3_path: str
    time_sec: float
    success: bool
    error_message: Optional[str] = None


# =============================================================================
# РЕЕСТР МЕТОДОВ (MethodRegistry)
# =============================================================================

class MethodRegistry:
    """Централизованный реестр методов трансформации.
    
    Позволяет:
    - Регистрировать методы трансформации
    - Динамически добавлять/удалять методы
    - Получать список всех методов
    - Выполнять методы по имени
    
    Пример использования:
    --------------------
    >>> registry = MethodRegistry()
    >>> registry.register("fwht", fwht_method)
    >>> methods = registry.get_all_methods()
    >>> result = registry.execute("fwht", wav_path, out_dir, settings)
    """
    
    def __init__(self):
        """Инициализация реестра."""
        self._methods: Dict[str, TransformMethod] = {}
        self._order: List[str] = []  # Порядок выполнения
        
    def register(self, name: str, method: TransformMethod) -> None:
        """Зарегистрировать метод.
        
        Параметры:
        ----------
        name : str
            Уникальное имя метода
        method : TransformMethod
            Объект метода, реализующий протокол
        """
        if name in self._methods:
            logger.warning(f"Метод '{name}' уже зарегистрирован, перезаписываем")
        else:
            self._order.append(name)
        self._methods[name] = method
        logger.debug(f"Зарегистрирован метод: {name}")
        
    def unregister(self, name: str) -> bool:
        """Удалить метод из реестра.
        
        Параметры:
        ----------
        name : str
            Имя метода для удаления
            
        Возвращает:
        -----------
        bool
            True если метод был удалён, False если не найден
        """
        if name in self._methods:
            del self._methods[name]
            self._order.remove(name)
            logger.debug(f"Удалён метод: {name}")
            return True
        return False
        
    def get_method(self, name: str) -> Optional[TransformMethod]:
        """Получить метод по имени."""
        return self._methods.get(name)
        
    def get_all_methods(self) -> List[Tuple[str, TransformMethod]]:
        """Получить все методы в порядке регистрации.
        
        Возвращает:
        -----------
        List[Tuple[str, TransformMethod]]
            Список кортежей (имя, метод)
        """
        return [(name, self._methods[name]) for name in self._order]
        
    def get_method_names(self) -> List[str]:
        """Получить имена всех методов."""
        return list(self._order)
        
    def has_method(self, name: str) -> bool:
        """Проверить наличие метода."""
        return name in self._methods
        
    def count(self) -> int:
        """Количество зарегистрированных методов."""
        return len(self._methods)
        
    def clear(self) -> None:
        """Очистить реестр."""
        self._methods.clear()
        self._order.clear()


# =============================================================================
# КОНКРЕТНЫЕ МЕТОДЫ ТРАНСФОРМАЦИИ
# =============================================================================

@dataclass
class FWHTMethod:
    """Метод FWHT трансформации."""
    name: str = "fwht"
    display_name: str = "FWHT"
    stage_index: int = 0
    
    def execute(
        self,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        return fwht_transform_and_mp3(
            wav_path, out_dir,
            block_size=settings.get('block_size', 2048),
            select_mode=settings.get('select_mode', 'none'),
            keep_energy_ratio=settings.get('keep_energy_ratio', 1.0),
            sequency_keep_ratio=settings.get('sequency_keep_ratio', 1.0),
            bitrate=settings.get('bitrate', '192k'),
            progress_cb=progress_cb,
        )


@dataclass
class FFTMethod:
    """Метод FFT трансформации."""
    name: str = "fft"
    display_name: str = "FFT"
    stage_index: int = 1
    
    def execute(
        self,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        return fft_transform_and_mp3(
            wav_path, out_dir,
            block_size=settings.get('block_size', 2048),
            select_mode=settings.get('select_mode', 'none'),
            keep_energy_ratio=settings.get('keep_energy_ratio', 1.0),
            sequency_keep_ratio=settings.get('sequency_keep_ratio', 1.0),
            bitrate=settings.get('bitrate', '192k'),
            progress_cb=progress_cb,
        )


@dataclass
class DCTMethod:
    """Метод DCT трансформации."""
    name: str = "dct"
    display_name: str = "DCT"
    stage_index: int = 2
    
    def execute(
        self,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        return dct_transform_and_mp3(
            wav_path, out_dir,
            block_size=settings.get('block_size', 2048),
            select_mode=settings.get('select_mode', 'none'),
            keep_energy_ratio=settings.get('keep_energy_ratio', 1.0),
            sequency_keep_ratio=settings.get('sequency_keep_ratio', 1.0),
            bitrate=settings.get('bitrate', '192k'),
            progress_cb=progress_cb,
        )


@dataclass
class DWTMethod:
    """Метод DWT (вейвлет Хаара) трансформации."""
    name: str = "dwt"
    display_name: str = "DWT"
    stage_index: int = 3
    
    def execute(
        self,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        return wavelet_transform_and_mp3(
            wav_path, out_dir,
            block_size=settings.get('block_size', 2048),
            select_mode=settings.get('select_mode', 'none'),
            keep_energy_ratio=settings.get('keep_energy_ratio', 1.0),
            sequency_keep_ratio=settings.get('sequency_keep_ratio', 1.0),
            levels=settings.get('levels', 4),
            bitrate=settings.get('bitrate', '192k'),
            progress_cb=progress_cb,
        )


@dataclass
class HuffmanMethod:
    """Метод Huffman-like трансформации."""
    name: str = "huffman"
    display_name: str = "Хаффман"
    stage_index: int = 4
    
    def execute(
        self,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        return huffman_like_transform_and_mp3(
            wav_path, out_dir,
            block_size=settings.get('block_size', 2048),
            bitrate=settings.get('bitrate', '192k'),
            mu=settings.get('mu', 255.0),
            bits=settings.get('bits', 8),
            progress_cb=progress_cb,
        )


@dataclass
class RosenbrockMethod:
    """Метод Rosenbrock-like трансформации."""
    name: str = "rosenbrock"
    display_name: str = "Розенброк"
    stage_index: int = 5
    
    def execute(
        self,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        return rosenbrock_like_transform_and_mp3(
            wav_path, out_dir,
            alpha=settings.get('rosen_alpha', 0.2),
            beta=settings.get('rosen_beta', 1.0),
            bitrate=settings.get('bitrate', '192k'),
            progress_cb=progress_cb,
        )


@dataclass
class StandardMethod:
    """Стандартный метод (простая конвертация в MP3)."""
    name: str = "standard"
    display_name: str = "Стандартный"
    stage_index: int = 6
    
    def execute(
        self,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        return standard_convert_to_mp3(
            wav_path, out_dir,
            bitrate=settings.get('bitrate', '192k'),
        )


@dataclass
class DaubechiesMethod:
    """Метод Daubechies DWT (db2, db4, db6, db8)."""
    name: str = "daubechies"
    display_name: str = "Daubechies DWT"
    stage_index: int = 7
    
    def execute(
        self,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        try:
            from processing.transforms.extended import daubechies_dwt_and_mp3
        except ImportError:
            from src.processing.transforms.extended import daubechies_dwt_and_mp3
        
        logger.info("daubechies_start_parallel", extra={"file": wav_path})
        return daubechies_dwt_and_mp3(
            wav_path, out_dir,
            block_size=settings.get('block_size', 2048),
            bitrate=settings.get('bitrate', '192k'),
            select_mode=settings.get('select_mode', 'none'),
            keep_energy_ratio=settings.get('keep_energy_ratio', 1.0),
            sequency_keep_ratio=settings.get('sequency_keep_ratio', 1.0),
            wavelet=settings.get('wavelet', 'db4'),
            levels=settings.get('levels', None),
            progress_cb=progress_cb,
        )


@dataclass
class MDCTMethod:
    """Метод MDCT (Modified Discrete Cosine Transform)."""
    name: str = "mdct"
    display_name: str = "MDCT"
    stage_index: int = 8
    
    def execute(
        self,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        try:
            from processing.transforms.extended import mdct_and_mp3
        except ImportError:
            from src.processing.transforms.extended import mdct_and_mp3
        
        logger.info("mdct_start_parallel", extra={"file": wav_path})
        return mdct_and_mp3(
            wav_path, out_dir,
            block_size=settings.get('block_size', 1024),
            bitrate=settings.get('bitrate', '192k'),
            select_mode=settings.get('select_mode', 'none'),
            keep_energy_ratio=settings.get('keep_energy_ratio', 1.0),
            sequency_keep_ratio=settings.get('sequency_keep_ratio', 1.0),
            progress_cb=progress_cb,
        )


def create_default_registry() -> MethodRegistry:
    """Создать реестр с методами по умолчанию.
    
    Возвращает:
    -----------
    MethodRegistry
        Реестр со всеми стандартными методами
    """
    registry = MethodRegistry()
    
    # Регистрируем методы в порядке выполнения
    registry.register("fwht", FWHTMethod())
    registry.register("fft", FFTMethod())
    registry.register("dct", DCTMethod())
    registry.register("dwt", DWTMethod())
    registry.register("huffman", HuffmanMethod())
    registry.register("rosenbrock", RosenbrockMethod())
    registry.register("standard", StandardMethod())
    # Новые методы
    registry.register("daubechies", DaubechiesMethod())
    registry.register("mdct", MDCTMethod())
    
    return registry


# =============================================================================
# РАБОЧИЙ ПОТОК
# =============================================================================

class Worker(QObject):
    """Фоновая обработка WAV-файлов с запуском всех методов и сбором метрик.

    Сигналы:
    - result(object): результат обработки файла
    - error(str): сообщение об ошибке
    - status(str): строка статуса с ETA
    - progress_file(int): прогресс текущего файла (0-100)
    - progress_total(int): прогресс всего набора (0-100)
    - finished(): завершение всех задач
    """

    # Сигналы
    result = Signal(str)        # payload as JSON string for thread-safe delivery
    error = Signal(str)           # сообщение об ошибке
    status = Signal(str)          # статус с ETA
    progress_file = Signal(int)   # 0-100 по текущему файлу
    progress_total = Signal(int)  # 0-100 по набору
    finished = Signal()           # завершение
    log = Signal(str)             # лог-сообщение (thread-safe через QueuedConnection)

    def __init__(
        self,
        wav_paths: List[str],
        out_dir: str,
        dataset_root: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        parallel: bool = False,
        max_workers: int = 4,
    ):
        """Инициализация Worker.

        Параметры:
        - wav_paths: список путей к WAV-файлам
        - out_dir: директория для вывода MP3
        - dataset_root: корень набора (для определения жанров) или None
        - settings: параметры пайплайнов
        - parallel: включить параллельную обработку методов
        - max_workers: максимальное число параллельных потоков
        """
        super().__init__()
        self.wav_paths = wav_paths
        self.out_dir = out_dir
        self.dataset_root = dataset_root
        self.settings = settings or {}
        self._total = max(1, len(wav_paths))
        self._is_batch = bool(dataset_root)
        self._parallel = parallel
        self._max_workers = max_workers

        # Логирование - используем print() для debug, сигнал log для UI
        self._log = logging.getLogger("ui_new.worker")
        
        # Флаг отмены
        self._cancelled = False
        
        # Время
        self._batch_t0: Optional[float] = None
        self._cur_file_t0: Optional[float] = None

        # Реестр методов (инициализируем первым для получения количества)
        self._registry = create_default_registry()
        
        # Статистика для ETA (динамическое количество методов)
        self._stage_total = self._registry.count()
        self._stage_stats: Dict[int, Tuple[float, int]] = {}
        
        # Прогресс методов для параллельного режима (thread-safe)
        self._method_progress: Dict[str, float] = {}
        self._method_progress_lock = threading.Lock()

    def _ui_log(self, message: str) -> None:
        """Отправить лог-сообщение в UI через сигнал (thread-safe)."""
        try:
            self.log.emit(message)
        except RuntimeError:
            pass  # Qt объект уничтожен

    def cancel(self) -> None:
        """Запросить отмену обработки."""
        self._cancelled = True
        self._log.info("cancel_requested")

    def is_cancelled(self) -> bool:
        """Проверить, был ли запрошен отмену."""
        return self._cancelled
    
    # =========================================================================
    # СЕРИАЛИЗАЦИЯ ДЛЯ JSON
    # =========================================================================
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Рекурсивно конвертировать numpy типы в нативные Python типы."""
        import numpy as np
        import math
        
        if obj is None:
            return None
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            # Конвертируем numpy float в Python float
            val = float(obj)
            # Проверяем на NaN/Inf
            if math.isnan(val) or math.isinf(val):
                return None
            return val
        elif isinstance(obj, np.ndarray):
            return self._make_json_serializable(obj.tolist())
        elif isinstance(obj, float):
            # Проверяем Python float на NaN/Inf
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        elif isinstance(obj, int):
            return obj
        elif isinstance(obj, str):
            return obj
        else:
            # Для прочих типов пробуем преобразовать в строку
            try:
                return str(obj)
            except Exception:
                return None
                
    # =========================================================================
    # ETA ФОРМАТИРОВАНИЕ
    # =========================================================================

    def _fmt_eta(self, seconds: float) -> str:
        """Форматировать секунды в строку ETA (H:MM:SS или MM:SS)."""
        try:
            if seconds != seconds or seconds < 0:  # NaN check
                return "—"
            s = int(seconds + 0.5)
            h = s // 3600
            m = (s % 3600) // 60
            sec = s % 60
            if h > 0:
                return f"{h}:{m:02d}:{sec:02d}"
            else:
                return f"{m:02d}:{sec:02d}"
        except Exception:
            return "—"

    def _status_with_eta(
        self,
        base: str,
        file_frac: float,
        processed_done: int,
        total_files: int,
    ) -> str:
        """Строка статуса с ETA (упрощённый API)."""
        try:
            return self._status_with_eta_cycle(base, 0, file_frac, processed_done, total_files)
        except Exception:
            return base

    def _status_with_eta_cycle(
        self,
        base: str,
        stage_idx: int,
        stage_frac: float,
        processed_done: int,
        total_files: int,
    ) -> str:
        """Расчёт ETA на основе статистики стадий."""
        try:
            n = max(1, self._stage_total)
            sf = max(0.0, min(1.0, float(stage_frac)))
            si = max(0, min(n - 1, int(stage_idx)))

            # Средние длительности стадий
            avg = []
            for i in range(n):
                s = self._stage_stats.get(i)
                if s and s[1] > 0:
                    avg.append(max(1e-6, s[0] / float(s[1])))
                else:
                    avg.append(float('nan'))

            # Фоллбек: равномерная оценка из текущего elapsed
            now = time.perf_counter()
            t_file_elapsed = max(1e-6, (now - (self._cur_file_t0 or now)))

            if not any(v == v for v in avg):
                base_unit = t_file_elapsed / max(1.0, (si + max(sf, 1e-3)))
                avg = [base_unit for _ in range(n)]
            else:
                known = [v for v in avg if v == v]
                fill = (sum(known) / len(known)) if known else t_file_elapsed / max(1.0, si + max(sf, 1e-3))
                avg = [v if v == v else fill for v in avg]

            # Остаток по файлу
            rem_file = max(0.0, (1.0 - sf) * avg[si]) + sum(avg[si + 1:])
            t_file_left = rem_file

            # ETA по набору (только в пакетном режиме)
            tail = ""
            if self._is_batch:
                total = max(1, int(total_files))
                done_files = max(0, int(processed_done))
                avg_per_file = sum(avg)
                rem_batch = rem_file + max(0, total - (done_files + 1)) * avg_per_file
                tail = f", набор ~ {self._fmt_eta(rem_batch)}"

            return f"{base} | Осталось: файл ~ {self._fmt_eta(t_file_left)}{tail}"
        except Exception:
            return base

    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================

    def _genre_of(self, wav_path: str) -> Optional[str]:
        """Определить жанр как первую подпапку относительно dataset_root."""
        if not self.dataset_root:
            return None
        try:
            rel = os.path.relpath(os.path.dirname(wav_path), self.dataset_root)
            parts = rel.split(os.sep)
            return parts[0] if parts and parts[0] not in ('.', '') else None
        except Exception:
            return None

    def _parse_settings(self) -> Tuple:
        """Разобрать настройки с значениями по умолчанию."""
        s = self.settings

        bs = int(s.get('block_size', 2048) or 2048)
        sel_mode = str(s.get('select_mode', 'none') or 'none')
        keep_energy = float(s.get('keep_energy_ratio', 1.0) or 1.0)
        seq_keep = float(s.get('sequency_keep_ratio', 1.0) or 1.0)
        bitrate = str(s.get('bitrate', '192k') or '192k')
        levels = int(s.get('levels', 4) or 4)
        mu = float(s.get('mu', 255.0) or 255.0)
        bits = int(s.get('bits', 8) or 8)
        alpha = float(s.get('rosen_alpha', 0.2) or 0.2)
        beta = float(s.get('rosen_beta', 1.0) or 1.0)

        return bs, sel_mode, keep_energy, seq_keep, bitrate, levels, mu, bits, alpha, beta
    
    def _get_settings_dict(self) -> Dict[str, Any]:
        """Получить словарь настроек для методов."""
        bs, sel_mode, keep_energy, seq_keep, bitrate, levels, mu, bits, alpha, beta = self._parse_settings()
        # Получаем список включённых методов из настроек (по умолчанию все)
        enabled_methods = self.settings.get('enabled_methods', None)
        
        return {
            'block_size': bs,
            'select_mode': sel_mode,
            'keep_energy_ratio': keep_energy,
            'sequency_keep_ratio': seq_keep,
            'bitrate': bitrate,
            'levels': levels,
            'mu': mu,
            'bits': bits,
            'rosen_alpha': alpha,
            'rosen_beta': beta,
            'enabled_methods': enabled_methods,
        }

    # =========================================================================
    # ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА МЕТОДОВ
    # =========================================================================

    def _execute_method_with_progress(
        self,
        method: TransformMethod,
        wav_path: str,
        out_dir: str,
        settings: Dict[str, Any],
        processed: int,
        total: int,
    ) -> MethodResult:
        """Выполнить один метод с отслеживанием прогресса.
        
        Параметры:
        ----------
        method : TransformMethod
            Метод для выполнения
        wav_path : str
            Путь к исходному файлу
        out_dir : str
            Директория для вывода
        settings : Dict[str, Any]
            Настройки
        processed : int
            Число обработанных файлов
        total : int
            Общее число файлов
            
        Возвращает:
        -----------
        MethodResult
            Результат выполнения метода
        """
        method_name = method.name
        stage_idx = method.stage_index
        
        def progress_cb(frac: float, msg: str):
            if not self._cancelled:
                # Thread-safe обновление прогресса
                with self._method_progress_lock:
                    self._method_progress[method_name] = frac
                    # Защита от деления на ноль
                    if self._method_progress:
                        total_progress = sum(self._method_progress.values()) / len(self._method_progress)
                    else:
                        total_progress = 0.0
                p = 5 + int(total_progress * 90)
                self.progress_file.emit(p)
                self.status.emit(self._status_with_eta_cycle(msg, stage_idx, frac, processed, total))
        
        try:
            t_start = time.perf_counter()
            mp3_path, time_sec = method.execute(wav_path, out_dir, settings, progress_cb)
            elapsed = time.perf_counter() - t_start
            
            # Обновляем статистику стадии
            self._stage_stats[stage_idx] = (
                self._stage_stats.get(stage_idx, (0.0, 0))[0] + elapsed,
                self._stage_stats.get(stage_idx, (0.0, 0))[1] + 1
            )
            
            return MethodResult(
                method_name=method_name,
                mp3_path=mp3_path,
                time_sec=time_sec,
                success=True,
            )
        except Exception as e:
            self._log.error(f"method_error: {method_name}", extra={"error": str(e)})
            return MethodResult(
                method_name=method_name,
                mp3_path="",
                time_sec=0.0,
                success=False,
                error_message=str(e),
            )

    def _process_file_parallel(
        self,
        wav_path: str,
        processed: int,
        total: int,
    ) -> Dict[str, MethodResult]:
        """Параллельная обработка всех методов для одного файла.
        
        Параметры:
        ----------
        wav_path : str
            Путь к исходному файлу
        processed : int
            Число обработанных файлов
        total : int
            Общее число файлов
            
        Возвращает:
        -----------
        Dict[str, MethodResult]
            Словарь результатов по имени метода
        """
        settings = self._get_settings_dict()
        results = {}
        
        # Инициализируем прогресс (thread-safe)
        with self._method_progress_lock:
            for name, _ in self._registry.get_all_methods():
                self._method_progress[name] = 0.0
        
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {}
            
            for name, method in self._registry.get_all_methods():
                if self._cancelled:
                    break
                    
                future = executor.submit(
                    self._execute_method_with_progress,
                    method, wav_path, self.out_dir, settings, processed, total
                )
                futures[future] = name
            
            # Собираем результаты
            for future in as_completed(futures):
                if self._cancelled:
                    break
                    
                name = futures[future]
                try:
                    result = future.result()
                    results[name] = result
                    self._log.info(f"{name}_done", extra={
                        "file": wav_path,
                        "out": result.mp3_path,
                        "time_s": result.time_sec
                    })
                except Exception as e:
                    results[name] = MethodResult(
                        method_name=name,
                        mp3_path="",
                        time_sec=0.0,
                        success=False,
                        error_message=str(e),
                    )
        
        return results

    def _process_file_sequential(
        self,
        wav_path: str,
        processed: int,
        total: int,
    ) -> Dict[str, MethodResult]:
        """Последовательная обработка всех методов для одного файла (оригинальный код).
        
        Параметры:
        ----------
        wav_path : str
            Путь к исходному файлу
        processed : int
            Число обработанных файлов
        total : int
            Общее число файлов
            
        Возвращает:
        -----------
        Dict[str, MethodResult]
            Словарь результатов по имени метода
        """
        results = {}
        settings = self._get_settings_dict()
        
        # Получаем список включённых методов (None означает все методы)
        enabled_methods = settings.get('enabled_methods', None)
        
        def is_method_enabled(method_name: str) -> bool:
            """Проверить, включён ли метод для обработки."""
            if enabled_methods is None:
                return True
            return method_name in enabled_methods
        
        # =====================================================================
        # FWHT
        # =====================================================================
        if self._cancelled:
            return results
        
        if is_method_enabled('fwht'):
            def cb_fwht(frac: float, msg: str):
                if not self._cancelled:
                    start, end = PROGRESS_RANGES['fwht']
                    p = start + int(max(0.0, min(1.0, frac)) * (end - start))
                    self.progress_file.emit(p)
                    self.status.emit(self._status_with_eta_cycle(msg, 0, frac, processed, total))
                self._log.debug("progress", extra={"file": wav_path, "stage": 0, "frac": frac})

            t_s0 = time.perf_counter()
            fwht_mp3, t_fwht = fwht_transform_and_mp3(
                wav_path, self.out_dir,
                block_size=settings['block_size'],
                select_mode=settings['select_mode'],
                keep_energy_ratio=settings['keep_energy_ratio'],
                sequency_keep_ratio=settings['sequency_keep_ratio'],
                bitrate=settings['bitrate'],
                progress_cb=cb_fwht,
            )
            self._stage_stats[0] = (
                self._stage_stats.get(0, (0.0, 0))[0] + (time.perf_counter() - t_s0),
                self._stage_stats.get(0, (0.0, 0))[1] + 1
            )
            results['fwht'] = MethodResult('fwht', fwht_mp3, t_fwht, True)
            self.progress_file.emit(PROGRESS_RANGES['fft'][0])  # Переход к следующей стадии
            self._log.info("fwht_done", extra={"file": wav_path, "out": fwht_mp3, "time_s": t_fwht})
            self._ui_log(f"  ✓ FWHT: {t_fwht:.2f}с")

        # =====================================================================
        # FFT
        # =====================================================================
        if self._cancelled:
            return results
        
        if is_method_enabled('fft'):
            def cb_fft(frac: float, msg: str):
                if not self._cancelled:
                    start, end = PROGRESS_RANGES['fft']
                    p = start + int(max(0.0, min(1.0, frac)) * (end - start))
                    self.progress_file.emit(p)
                    self.status.emit(self._status_with_eta_cycle(msg, 1, frac, processed, total))

            t_s1 = time.perf_counter()
            fft_mp3, t_fft = fft_transform_and_mp3(
                wav_path, self.out_dir,
                block_size=settings['block_size'],
                select_mode=settings['select_mode'],
                keep_energy_ratio=settings['keep_energy_ratio'],
                sequency_keep_ratio=settings['sequency_keep_ratio'],
                bitrate=settings['bitrate'],
                progress_cb=cb_fft,
            )
            self._stage_stats[1] = (
                self._stage_stats.get(1, (0.0, 0))[0] + (time.perf_counter() - t_s1),
                self._stage_stats.get(1, (0.0, 0))[1] + 1
            )
            results['fft'] = MethodResult('fft', fft_mp3, t_fft, True)
            self.progress_file.emit(PROGRESS_RANGES['dct'][0])  # Переход к следующей стадии
            self._log.info("fft_done", extra={"file": wav_path, "out": fft_mp3, "time_s": t_fft})
            self._ui_log(f"  ✓ FFT: {t_fft:.2f}с")

        # =====================================================================
        # DCT
        # =====================================================================
        if self._cancelled:
            return results
        
        if is_method_enabled('dct'):
            def cb_dct(frac: float, msg: str):
                if not self._cancelled:
                    start, end = PROGRESS_RANGES['dct']
                    p = start + int(max(0.0, min(1.0, frac)) * (end - start))
                    self.progress_file.emit(p)
                    self.status.emit(self._status_with_eta_cycle(msg, 2, frac, processed, total))

            t_s2 = time.perf_counter()
            dct_mp3, t_dct = dct_transform_and_mp3(
                wav_path, self.out_dir,
                block_size=settings['block_size'],
                select_mode=settings['select_mode'],
                keep_energy_ratio=settings['keep_energy_ratio'],
                sequency_keep_ratio=settings['sequency_keep_ratio'],
                bitrate=settings['bitrate'],
                progress_cb=cb_dct,
            )
            self._stage_stats[2] = (
                self._stage_stats.get(2, (0.0, 0))[0] + (time.perf_counter() - t_s2),
                self._stage_stats.get(2, (0.0, 0))[1] + 1
            )
            results['dct'] = MethodResult('dct', dct_mp3, t_dct, True)
            self.progress_file.emit(PROGRESS_RANGES['dwt'][0])  # Переход к следующей стадии
            self._log.info("dct_done", extra={"file": wav_path, "out": dct_mp3, "time_s": t_dct})
            self._ui_log(f"  ✓ DCT: {t_dct:.2f}с")

        # =====================================================================
        # DWT (Haar)
        # =====================================================================
        if self._cancelled:
            return results
        
        if is_method_enabled('dwt'):
            def cb_dwt(frac: float, msg: str):
                if not self._cancelled:
                    start, end = PROGRESS_RANGES['dwt']
                    p = start + int(max(0.0, min(1.0, frac)) * (end - start))
                    self.progress_file.emit(p)
                    self.status.emit(self._status_with_eta_cycle(msg, 3, frac, processed, total))

            t_s3 = time.perf_counter()
            dwt_mp3, t_dwt = wavelet_transform_and_mp3(
                wav_path, self.out_dir,
                block_size=settings['block_size'],
                select_mode=settings['select_mode'],
                keep_energy_ratio=settings['keep_energy_ratio'],
                sequency_keep_ratio=settings['sequency_keep_ratio'],
                levels=settings['levels'],
                bitrate=settings['bitrate'],
                progress_cb=cb_dwt,
            )
            self._stage_stats[3] = (
                self._stage_stats.get(3, (0.0, 0))[0] + (time.perf_counter() - t_s3),
                self._stage_stats.get(3, (0.0, 0))[1] + 1
            )
            results['dwt'] = MethodResult('dwt', dwt_mp3, t_dwt, True)
            self.progress_file.emit(PROGRESS_RANGES['huffman'][0])  # Переход к следующей стадии
            self._log.info("dwt_done", extra={"file": wav_path, "out": dwt_mp3, "time_s": t_dwt})
            self._ui_log(f"  ✓ DWT: {t_dwt:.2f}с")

        # =====================================================================
        # Huffman-like
        # =====================================================================
        if self._cancelled:
            return results
        
        if is_method_enabled('huffman'):
            def cb_huff(frac: float, msg: str):
                if not self._cancelled:
                    start, end = PROGRESS_RANGES['huffman']
                    p = start + int(max(0.0, min(1.0, frac)) * (end - start))
                    self.progress_file.emit(p)
                    self.status.emit(self._status_with_eta_cycle(msg, 4, frac, processed, total))

            t_s4 = time.perf_counter()
            huff_mp3, t_huff = huffman_like_transform_and_mp3(
                wav_path, self.out_dir,
                block_size=settings['block_size'],
                bitrate=settings['bitrate'],
                mu=settings['mu'],
                bits=settings['bits'],
                progress_cb=cb_huff,
            )
            self._stage_stats[4] = (
                self._stage_stats.get(4, (0.0, 0))[0] + (time.perf_counter() - t_s4),
                self._stage_stats.get(4, (0.0, 0))[1] + 1
            )
            results['huffman'] = MethodResult('huffman', huff_mp3, t_huff, True)
            self.progress_file.emit(PROGRESS_RANGES['rosenbrock'][0])  # Переход к следующей стадии
            self._log.info("huffman_done", extra={"file": wav_path, "out": huff_mp3, "time_s": t_huff})
            self._ui_log(f"  ✓ Хаффман: {t_huff:.2f}с")

        # =====================================================================
        # Rosenbrock-like
        # =====================================================================
        if self._cancelled:
            return results
        
        if is_method_enabled('rosenbrock'):
            def cb_rb(frac: float, msg: str):
                if not self._cancelled:
                    start, end = PROGRESS_RANGES['rosenbrock']
                    p = start + int(max(0.0, min(1.0, frac)) * (end - start))
                    self.progress_file.emit(p)
                    self.status.emit(self._status_with_eta_cycle(msg, 5, frac, processed, total))

            t_s5 = time.perf_counter()
            rb_mp3, t_rb = rosenbrock_like_transform_and_mp3(
                wav_path, self.out_dir,
                alpha=settings['rosen_alpha'],
                beta=settings['rosen_beta'],
                bitrate=settings['bitrate'],
                progress_cb=cb_rb,
            )
            self._stage_stats[5] = (
                self._stage_stats.get(5, (0.0, 0))[0] + (time.perf_counter() - t_s5),
                self._stage_stats.get(5, (0.0, 0))[1] + 1
            )
            results['rosenbrock'] = MethodResult('rosenbrock', rb_mp3, t_rb, True)
            self.progress_file.emit(PROGRESS_RANGES['standard'][0])  # Переход к последней стадии
            self._log.info("rosenbrock_done", extra={"file": wav_path, "out": rb_mp3, "time_s": t_rb})
            self._ui_log(f"  ✓ Розенброк: {t_rb:.2f}с")

        # =====================================================================
        # Стандартный MP3
        # =====================================================================
        if self._cancelled:
            return results
        
        if is_method_enabled('standard'):
            self.status.emit(self._status_with_eta_cycle("Стандартный: кодирование MP3", 6, 0.0, processed, total))
            t_s6 = time.perf_counter()
            std_mp3, t_std = standard_convert_to_mp3(wav_path, self.out_dir, bitrate=settings['bitrate'])
            self._stage_stats[6] = (
                self._stage_stats.get(6, (0.0, 0))[0] + (time.perf_counter() - t_s6),
                self._stage_stats.get(6, (0.0, 0))[1] + 1
            )
            results['standard'] = MethodResult('standard', std_mp3, t_std, True)
            self.progress_file.emit(PROGRESS_RANGES['daubechies'][0])  # Переход к Daubechies
            self._log.info("std_done", extra={"file": wav_path, "out": std_mp3, "time_s": t_std})
            self._ui_log(f"  ✓ Стандартный: {t_std:.2f}с")

        # =====================================================================
        # Daubechies DWT (db4)
        # =====================================================================
        if self._cancelled:
            return results
        
        if is_method_enabled('daubechies'):
            def cb_daub(frac: float, msg: str):
                if not self._cancelled:
                    start, end = PROGRESS_RANGES['daubechies']
                    p = start + int(max(0.0, min(1.0, frac)) * (end - start))
                    self.progress_file.emit(p)
                    self.status.emit(self._status_with_eta_cycle(msg, 7, frac, processed, total))

            try:
                from processing.transforms.extended import daubechies_dwt_and_mp3
            except ImportError:
                from src.processing.transforms.extended import daubechies_dwt_and_mp3

            self._ui_log(f"  ⏳ Daubechies DWT (db4): запуск...")
            self._log.info("daubechies_start", extra={"file": wav_path})
            t_s7 = time.perf_counter()
            try:
                daub_mp3, t_daub = daubechies_dwt_and_mp3(
                    wav_path, self.out_dir,
                    block_size=settings['block_size'],
                    bitrate=settings['bitrate'],
                    select_mode=settings['select_mode'],
                    keep_energy_ratio=settings['keep_energy_ratio'],
                    sequency_keep_ratio=settings['sequency_keep_ratio'],
                    wavelet='db4',
                    levels=settings.get('levels', None),
                    progress_cb=cb_daub,
                )
                self._stage_stats[7] = (
                    self._stage_stats.get(7, (0.0, 0))[0] + (time.perf_counter() - t_s7),
                    self._stage_stats.get(7, (0.0, 0))[1] + 1
                )
                results['daubechies'] = MethodResult('daubechies', daub_mp3, t_daub, True)
                self.progress_file.emit(PROGRESS_RANGES['mdct'][0])  # Переход к MDCT
                self._log.info("daubechies_done", extra={"file": wav_path, "out": daub_mp3, "time_s": t_daub})
                self._ui_log(f"  ✓ Daubechies DWT: {t_daub:.2f}с")
            except Exception as e:
                self._log.error(f"daubechies_error: {e}")
                results['daubechies'] = MethodResult('daubechies', "", 0.0, False, error_message=str(e))
                self._ui_log(f"  ⚠ Daubechies DWT: ошибка — {e}")

        # =====================================================================
        # MDCT
        # =====================================================================
        if self._cancelled:
            return results
        
        if is_method_enabled('mdct'):
            def cb_mdct(frac: float, msg: str):
                if not self._cancelled:
                    start, end = PROGRESS_RANGES['mdct']
                    p = start + int(max(0.0, min(1.0, frac)) * (end - start))
                    self.progress_file.emit(p)
                    self.status.emit(self._status_with_eta_cycle(msg, 8, frac, processed, total))

            try:
                from processing.transforms.extended import mdct_and_mp3
            except ImportError:
                from src.processing.transforms.extended import mdct_and_mp3

            self._ui_log(f"  ⏳ MDCT: запуск...")
            self._log.info("mdct_start", extra={"file": wav_path})
            t_s8 = time.perf_counter()
            try:
                mdct_mp3, t_mdct = mdct_and_mp3(
                    wav_path, self.out_dir,
                    block_size=1024,
                    bitrate=settings['bitrate'],
                    select_mode=settings['select_mode'],
                    keep_energy_ratio=settings['keep_energy_ratio'],
                    sequency_keep_ratio=settings['sequency_keep_ratio'],
                    progress_cb=cb_mdct,
                )
                self._stage_stats[8] = (
                    self._stage_stats.get(8, (0.0, 0))[0] + (time.perf_counter() - t_s8),
                    self._stage_stats.get(8, (0.0, 0))[1] + 1
                )
                results['mdct'] = MethodResult('mdct', mdct_mp3, t_mdct, True)
                self._log.info("mdct_done", extra={"file": wav_path, "out": mdct_mp3, "time_s": t_mdct})
                self._ui_log(f"  ✓ MDCT: {t_mdct:.2f}с")
            except Exception as e:
                self._log.error(f"mdct_error: {e}")
                results['mdct'] = MethodResult('mdct', "", 0.0, False, error_message=str(e))
                self._ui_log(f"  ⚠ MDCT: ошибка — {e}")

        self.progress_file.emit(99)
        return results

    # =========================================================================
    # АСИНХРОННЫЙ РАСЧЁТ МЕТРИК
    # =========================================================================

    def _compute_metrics_async(
        self,
        original_wav: str,
        items: List[Tuple[str, str, float]],
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> List[Dict]:
        """Вычислить метрики асинхронно через ThreadPoolExecutor.

        Каждый вариант (метод) рассчитывается в отдельном потоке.
        После сбора всех результатов выполняется нормализация и score.

        Параметры:
        ----------
        original_wav : str
            Путь к исходному WAV
        items : list of (variant, path, time_sec)
        progress_cb : callable(idx, total, msg) or None
        weights : dict or None

        Возвращает:
        --------
        list[dict] — результаты с метриками и score
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Импортируем функции для загрузки аудио
        try:
            from processing.codecs import load_wav_mono, decode_audio_to_mono, get_audio_meta
        except ImportError:
            from src.processing.codecs import load_wav_mono, decode_audio_to_mono, get_audio_meta

        try:
            from processing.metrics import compute_lsd_db, compute_snr_db, compute_rmse
            from processing.metrics import compute_si_sdr_db, compute_spectral_convergence
            from processing.metrics import compute_spectral_centroid_diff_hz, compute_spectral_cosine_similarity
            from processing.metrics import compute_stoi_simplified, compute_pesq_approx, compute_pesq_mos
        except ImportError:
            from src.processing.metrics import (
                compute_lsd_db, compute_snr_db, compute_rmse,
                compute_si_sdr_db, compute_spectral_convergence,
                compute_spectral_centroid_diff_hz, compute_spectral_cosine_similarity,
                compute_stoi_simplified, compute_pesq_approx, compute_pesq_mos,
            )

        # Загружаем референс один раз
        orig_meta = get_audio_meta(original_wav)
        ref, sr_ref = load_wav_mono(original_wav)

        total = len(items)
        if total == 0:
            return []

        # Функция расчёта метрик для одного варианта
        def compute_one(idx: int, variant: str, path: str, time_s: float) -> Dict:
            """Вычислить все метрики для одного варианта."""
            meta = get_audio_meta(path)
            sig, sr = decode_audio_to_mono(path)

            # 10 метрик с прогрессом
            metric_fns = [
                ('LSD',        lambda: float(compute_lsd_db(ref, sig, sr_ref, sr))),
                ('SNR',        lambda: float(compute_snr_db(ref, sig))),
                ('Spec Conv',  lambda: float(compute_spectral_convergence(ref, sig, sr_ref, sr))),
                ('RMSE',       lambda: float(compute_rmse(ref, sig))),
                ('SI-SDR',     lambda: float(compute_si_sdr_db(ref, sig))),
                ('Centroid Δ', lambda: float(compute_spectral_centroid_diff_hz(ref, sig, sr_ref, sr))),
                ('Cosine',     lambda: float(compute_spectral_cosine_similarity(ref, sig, sr_ref, sr))),
                ('STOI',       lambda: float(compute_stoi_simplified(ref, sig, sr_ref, sr))),
                ('PESQ',       lambda: float(compute_pesq_approx(ref, sig, sr_ref, sr))),
                ('MOS',        lambda: float(compute_pesq_mos(ref, sig, sr_ref, sr))),
            ]

            vals = {}
            for mname, fn in metric_fns:
                if self._cancelled:
                    break
                if progress_cb:
                    progress_cb(idx, total, f"{variant}: {mname}")
                try:
                    vals[mname] = fn()
                except Exception as e:
                    self._log.warning(f"metric_error", extra={
                        "variant": variant, "metric": mname, "error": str(e)
                    })
                    vals[mname] = float("nan")

            if progress_cb:
                progress_cb(idx, total, f"{variant}: готово")

            return {
                "variant": variant,
                "path": path,
                "size_bytes": os.path.getsize(path),
                "sample_rate_hz": meta["sample_rate_hz"],
                "bit_depth_bits": meta["bit_depth_bits"],
                "bitrate_bps": meta["bitrate_bps"],
                "time_sec": float(time_s),
                "lsd_db": vals.get('LSD', float("nan")),
                "snr_db": vals.get('SNR', float("nan")),
                "spec_conv": vals.get('Spec Conv', float("nan")),
                "rmse": vals.get('RMSE', float("nan")),
                "si_sdr_db": vals.get('SI-SDR', float("nan")),
                "spec_centroid_diff_hz": vals.get('Centroid Δ', float("nan")),
                "spec_cosine": vals.get('Cosine', float("nan")),
                "stoi": vals.get('STOI', float("nan")),
                "pesq": vals.get('PESQ', float("nan")),
                "mos": vals.get('MOS', float("nan")),
                "orig_sample_rate_hz": orig_meta["sample_rate_hz"],
                "orig_bit_depth_bits": orig_meta["bit_depth_bits"],
                "orig_bitrate_bps": orig_meta["bitrate_bps"],
            }

        # Запускаем расчёт для каждого варианта в отдельном потоке
        results: List[Dict] = []
        max_metric_workers = min(total, self._max_workers)

        with ThreadPoolExecutor(max_workers=max_metric_workers) as executor:
            futures = {}
            for idx, (variant, path, time_s) in enumerate(items):
                future = executor.submit(compute_one, idx, variant, path, time_s)
                futures[future] = (idx, variant)

            for future in as_completed(futures):
                if self._cancelled:
                    break
                idx, variant = futures[future]
                try:
                    result = future.result()
                    # Вычисляем дельты
                    result["delta_sr"] = result["sample_rate_hz"] - result["orig_sample_rate_hz"]
                    result["delta_bd"] = result["bit_depth_bits"] - result["orig_bit_depth_bits"]
                    result["delta_br_bps"] = result["bitrate_bps"] - result["orig_bitrate_bps"]
                    results.append(result)

                    self._log.info(
                        f"metrics_done [{idx+1}/{total}]",
                        extra={
                            "variant": variant,
                            "lsd_db": result.get("lsd_db"),
                            "snr_db": result.get("snr_db"),
                            "spec_conv": result.get("spec_conv"),
                            "rmse": result.get("rmse"),
                            "si_sdr_db": result.get("si_sdr_db"),
                            "spec_centroid_diff_hz": result.get("spec_centroid_diff_hz"),
                            "spec_cosine": result.get("spec_cosine"),
                            "stoi": result.get("stoi"),
                            "pesq": result.get("pesq"),
                            "mos": result.get("mos"),
                        }
                    )
                except Exception as e:
                    self._log.error(f"metrics_variant_error", extra={
                        "variant": variant, "error": str(e)
                    })

        if not results:
            return []

        # Нормализация min-max и расчёт score
        if progress_cb:
            progress_cb(total, total, "Нормализация и расчёт score…")

        def _minmax(vals):
            vals_f = [v for v in vals if v == v]
            if not vals_f:
                return None, None
            return min(vals_f), max(vals_f)

        eps = 1e-12
        lsd_min, lsd_max = _minmax([r["lsd_db"] for r in results])
        sc_min, sc_max = _minmax([r["spec_conv"] for r in results])
        t_min, t_max = _minmax([r["time_sec"] for r in results])
        snr_min, snr_max = _minmax([r["snr_db"] for r in results])
        rmse_min, rmse_max = _minmax([r.get("rmse") for r in results])
        sisdr_min, sisdr_max = _minmax([r.get("si_sdr_db") for r in results])
        scdiff_min, scdiff_max = _minmax([r.get("spec_centroid_diff_hz") for r in results])
        cos_min, cos_max = _minmax([r.get("spec_cosine") for r in results])
        stoi_min, stoi_max = _minmax([r.get("stoi") for r in results])
        pesq_min, pesq_max = _minmax([r.get("pesq") for r in results])
        mos_min, mos_max = _minmax([r.get("mos") for r in results])

        w = weights or {
            'lsd': 0.15, 'snr': 0.15, 'rmse': 0.10, 'si_sdr': 0.10,
            'spec_conv': 0.10, 'centroid_diff': 0.05, 'cosine': 0.05,
            'time': 0.05, 'stoi': 0.10, 'pesq': 0.10, 'mos': 0.05,
        }

        for r in results:
            # "ниже-лучше" → инвертируем
            lsd_n = 0.0 if lsd_min is None else (lsd_max - r["lsd_db"]) / ((lsd_max - lsd_min) + eps)
            sc_n = 0.0 if sc_min is None else (sc_max - r["spec_conv"]) / ((sc_max - sc_min) + eps)
            rmse_n = 0.0 if rmse_min is None else (rmse_max - r["rmse"]) / ((rmse_max - rmse_min) + eps)
            scdiff_n = 0.0 if scdiff_min is None else (scdiff_max - r["spec_centroid_diff_hz"]) / ((scdiff_max - scdiff_min) + eps)
            t_n = 0.0 if t_min is None else (t_max - r["time_sec"]) / ((t_max - t_min) + eps)
            # "выше-лучше"
            snr_n = 0.0 if snr_min is None else (r["snr_db"] - snr_min) / ((snr_max - snr_min) + eps)
            sisdr_n = 0.0 if sisdr_min is None else (r["si_sdr_db"] - sisdr_min) / ((sisdr_max - sisdr_min) + eps)
            cos_n = 0.0 if cos_min is None else (r["spec_cosine"] - cos_min) / ((cos_max - cos_min) + eps)
            stoi_n = 0.0 if stoi_min is None else (r["stoi"] - stoi_min) / ((stoi_max - stoi_min) + eps)
            pesq_n = 0.0 if pesq_min is None else (r["pesq"] - pesq_min) / ((pesq_max - pesq_min) + eps)
            mos_n = 0.0 if mos_min is None else (r["mos"] - mos_min) / ((mos_max - mos_min) + eps)

            r["score"] = float(
                w.get('lsd', 0.15) * lsd_n +
                w.get('spec_conv', 0.10) * sc_n +
                w.get('snr', 0.15) * snr_n +
                w.get('rmse', 0.10) * rmse_n +
                w.get('si_sdr', 0.10) * sisdr_n +
                w.get('centroid_diff', 0.05) * scdiff_n +
                w.get('cosine', 0.05) * cos_n +
                w.get('time', 0.05) * t_n +
                w.get('stoi', 0.10) * stoi_n +
                w.get('pesq', 0.10) * pesq_n +
                w.get('mos', 0.05) * mos_n
            )

        self._log.info("metrics_async_done", extra={"count": len(results)})
        return results

    # =========================================================================
    # ОСНОВНОЙ ЦИКЛ
    # =========================================================================

    @Slot()
    def run(self) -> None:
        """Выполнить обработку всех WAV-файлов.

        Для каждого файла:
        1. Запустить 9 методов обработки (параллельно или последовательно)
        2. Собрать метрики
        3. Отправить результат через сигнал
        """
        self._log.info("worker_start", extra={"files": len(self.wav_paths), "parallel": self._parallel})
        self._ui_log(f"▶ Запуск обработки: {len(self.wav_paths)} файлов")

        processed = 0
        total = self._total
        self._batch_t0 = time.perf_counter()

        # Гарантируем существование выходной директории
        os.makedirs(self.out_dir, exist_ok=True)

        for wav_path in self.wav_paths:
            # Проверка отмены
            if self._cancelled:
                self._log.info("worker_cancelled", extra={"processed": processed, "total": total})
                self.status.emit("Отменено пользователем")
                break

            try:
                wav_path = os.path.normpath(wav_path)
                self._log.info("file_start", extra={"path": wav_path, "idx": processed + 1, "total": total})
                self._ui_log(f"\n📄 Файл {processed + 1}/{total}: {os.path.basename(wav_path)}")

                if not os.path.exists(wav_path):
                    raise FileNotFoundError(wav_path)

                self._cur_file_t0 = time.perf_counter()
                self.status.emit(f"Обработка: {os.path.basename(wav_path)} ({processed + 1}/{total})…")
                self.progress_file.emit(1)
                self.progress_total.emit(max(1, int(100 * processed / total)))

                # Выполняем методы (параллельно или последовательно)
                if self._parallel:
                    method_results = self._process_file_parallel(wav_path, processed, total)
                else:
                    method_results = self._process_file_sequential(wav_path, processed, total)

                if self._cancelled:
                    break

                # =====================================================================
                # Вычисление метрик (асинхронно через ThreadPoolExecutor)
                # =====================================================================
                # Формируем список для метрик — все методы включая Daubechies и MDCT
                items: List[Tuple[str, str, float]] = []

                # Порядок для отображения (все 9 методов)
                order = [
                    'standard', 'fwht', 'fft', 'dct', 'dwt',
                    'huffman', 'rosenbrock', 'daubechies', 'mdct',
                ]
                display_names = {
                    'standard': 'Стандартный MP3',
                    'fwht': 'FWHT MP3',
                    'fft': 'FFT MP3',
                    'dct': 'DCT MP3',
                    'dwt': 'DWT MP3',
                    'huffman': 'Хаффман MP3',
                    'rosenbrock': 'Розенброк MP3',
                    'daubechies': 'Daubechies DWT MP3',
                    'mdct': 'MDCT MP3',
                }

                for name in order:
                    if name in method_results and method_results[name].success:
                        r = method_results[name]
                        items.append((display_names[name], r.mp3_path, r.time_sec))

                # Callback прогресса для метрик
                def metrics_progress_cb(idx: int, total: int, msg: str):
                    if not self._cancelled:
                        self._ui_log(f"  ⏳ Метрики [{idx+1}/{total}]: {msg}")

                # Веса метрик из конфига
                try:
                    from config import MetricsConfig
                    mc = MetricsConfig()
                    metrics_weights = {
                        'lsd': mc.weight_lsd,
                        'snr': mc.weight_snr,
                        'rmse': mc.weight_rmse,
                        'si_sdr': mc.weight_si_sdr,
                        'spec_conv': mc.weight_spectral_conv,
                        'centroid_diff': mc.weight_centroid_diff,
                        'cosine': mc.weight_cosine_sim,
                        'time': mc.weight_time,
                        'stoi': mc.weight_stoi,
                        'pesq': mc.weight_pesq,
                        'mos': mc.weight_mos,
                    }
                except Exception:
                    metrics_weights = None

                try:
                    self._ui_log(f"  ⏳ Вычисление метрик для {len(items)} методов...")
                    self.status.emit(f"Вычисление метрик: {os.path.basename(wav_path)}…")

                    # Асинхронный расчёт метрик через ThreadPoolExecutor
                    results = self._compute_metrics_async(
                        wav_path, items, metrics_progress_cb, metrics_weights
                    )
                    self._ui_log(f"  ✓ Метрики: {len(results)} методов рассчитаны")
                except Exception as e:
                    self._log.error("metrics_error", extra={"error": str(e)})
                    self._ui_log(f"  ⚠ Ошибка метрик: {e}")
                    results = []

                # Логирование результатов
                for r in results:
                    self._log.info(
                        "result",
                        extra={
                            "file": wav_path,
                            "variant": r.get("variant"),
                            "lsd_db": r.get("lsd_db"),
                            "time_sec": r.get("time_sec"),
                            "size_bytes": r.get("size_bytes"),
                        }
                    )

                # Проверка отмены перед отправкой результата
                if self._cancelled:
                    break
                    
                # Отправка результата (сериализуем в JSON для потокобезопасности)
                payload = {
                    "source": os.path.basename(wav_path),
                    "genre": self._genre_of(wav_path),
                    "results": results,
                }
                try:
                    # Конвертируем numpy типы в нативные Python типы и сериализуем в JSON
                    serializable_payload = self._make_json_serializable(payload)
                    json_payload = json.dumps(serializable_payload, ensure_ascii=False)
                    print(f"[WORKER] Emitting result, payload size={len(json_payload)}", flush=True)
                    self.result.emit(json_payload)
                    print(f"[WORKER] Result emitted successfully", flush=True)
                    # ВАЖНО: НЕ вызываем msleep() здесь! Поток может быть остановлен в любой момент.
                except Exception as e:
                    self._log.error("emit_result_error", extra={"error": str(e)})

                processed += 1
                self.progress_file.emit(100)
                self.progress_total.emit(int(100 * processed / total))
                self._log.info("file_done", extra={"path": wav_path})
                self._ui_log(f"✅ Завершено: {os.path.basename(wav_path)} ({processed}/{total})")

            except Exception as e:
                self._log.exception("file_error", extra={"path": wav_path})
                self.error.emit(f"{os.path.basename(wav_path)}: {e}")
                continue

        # Завершение
        try:
            self._log.info("worker_finished")
            self._ui_log(f"\n🏁 Обработка завершена: {processed}/{total} файлов")
            # ВАЖНО: emit finished() должен быть ПОСЛЕДНИМ действием в Worker!
            # После emit поток может быть немедленно остановлен через thread.quit()
            self.finished.emit()
        except Exception:
            self._log.exception("worker_emit_finished_error")


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "Worker",
    "ResultRow",
    "MethodRegistry",
    "MethodResult",
    "TransformMethod",
    "create_default_registry",
    "FWHTMethod",
    "FFTMethod",
    "DCTMethod",
    "DWTMethod",
    "HuffmanMethod",
    "RosenbrockMethod",
    "StandardMethod",
]
