"""
Сервис координации обработки аудио.

Назначение:
- Координация Worker и методов обработки
- Управление прогрессом
- Агрегация результатов
- Рекомендации по выбору метода

Использование:
--------------
>>> from ui_new.services import get_container
>>> container = get_container()
>>> audio_service = container.audio_processing
>>> 
>>> # Получить настройки по умолчанию
>>> settings = audio_service.get_default_settings()
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .config import AppConfig, PROGRESS_RANGES

logger = logging.getLogger("ui_new.services.audio_service")


# =============================================================================
# СТРУКТУРЫ ДАННЫХ
# =============================================================================

@dataclass
class ProgressInfo:
    """Информация о прогрессе."""
    current_method: str
    current_stage: int
    total_stages: int
    file_progress: float  # 0.0 - 1.0
    total_progress: float  # 0.0 - 1.0
    elapsed_time: float
    estimated_remaining: Optional[float]
    message: str


@dataclass
class ProcessingResult:
    """Результат обработки файла."""
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
        """Размер в МБ."""
        return self.size_bytes / (1024 * 1024)


# =============================================================================
# СЕРВИС ОБРАБОТКИ АУДИО
# =============================================================================

class AudioProcessingService:
    """Сервис координации обработки аудио.
    
    Предоставляет:
    - Настройки по умолчанию
    - Фабрику callback-ов прогресса
    - Расчёт ETA
    - Рекомендации методов
    
    Атрибуты:
    ----------
    config : AppConfig
        Конфигурация приложения
    """
    
    # Число методов обработки
    TOTAL_METHODS: int = 7
    
    # Имена методов в порядке выполнения
    METHOD_ORDER: List[str] = [
        "fwht", "fft", "dct", "dwt", "huffman", "rosenbrock", "standard"
    ]
    
    # Отображаемые имена методов
    METHOD_DISPLAY_NAMES: Dict[str, str] = {
        "fwht": "FWHT",
        "fft": "FFT",
        "dct": "DCT",
        "dwt": "DWT",
        "huffman": "Хаффман",
        "rosenbrock": "Розенброк",
        "standard": "Стандартный",
    }
    
    def __init__(self, config: AppConfig):
        """Инициализация сервиса.
        
        Параметры:
        ----------
        config : AppConfig
            Конфигурация приложения
        """
        self._config = config
        logger.debug("AudioProcessingService initialized")
    
    # =========================================================================
    # НАСТРОЙКИ
    # =========================================================================
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Получить настройки по умолчанию.
        
        Возвращает:
        -----------
        Dict[str, Any]
            Словарь с настройками
        """
        return {
            "block_size": 2048,
            "bitrate": "192k",
            "select_mode": "none",
            "keep_energy_ratio": 1.0,
            "sequency_keep_ratio": 1.0,
            "levels": 4,
            "mu": 255.0,
            "bits": 8,
            "rosen_alpha": 0.2,
            "rosen_beta": 1.0,
        }
    
    def validate_settings(self, settings: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Валидировать настройки.
        
        Параметры:
        ----------
        settings : Dict[str, Any]
            Словарь с настройками
            
        Возвращает:
        -----------
        Tuple[bool, List[str]]
            (is_valid, list_of_errors)
        """
        errors = []
        
        # block_size - должен быть степенью двойки
        block_size = settings.get("block_size", 2048)
        if block_size < 64 or block_size > 16384:
            errors.append("block_size должен быть от 64 до 16384")
        elif block_size & (block_size - 1) != 0:
            errors.append("block_size должен быть степенью двойки")
        
        # bitrate
        bitrate = settings.get("bitrate", "192k")
        valid_bitrates = ["64k", "96k", "128k", "160k", "192k", "224k", "256k", "320k"]
        if bitrate not in valid_bitrates:
            errors.append(f"bitrate должен быть одним из: {', '.join(valid_bitrates)}")
        
        # select_mode
        select_mode = settings.get("select_mode", "none")
        if select_mode not in ("none", "energy", "lowpass"):
            errors.append("select_mode должен быть 'none', 'energy' или 'lowpass'")
        
        # keep_energy_ratio
        keep_energy = settings.get("keep_energy_ratio", 1.0)
        if not 0.0 <= keep_energy <= 1.0:
            errors.append("keep_energy_ratio должен быть от 0.0 до 1.0")
        
        # sequency_keep_ratio
        seq_keep = settings.get("sequency_keep_ratio", 1.0)
        if not 0.0 <= seq_keep <= 1.0:
            errors.append("sequency_keep_ratio должен быть от 0.0 до 1.0")
        
        # levels
        levels = settings.get("levels", 4)
        if levels < 1 or levels > 10:
            errors.append("levels должен быть от 1 до 10")
        
        # mu
        mu = settings.get("mu", 255.0)
        if mu <= 0:
            errors.append("mu должен быть больше 0")
        
        # bits
        bits = settings.get("bits", 8)
        if bits < 2 or bits > 16:
            errors.append("bits должен быть от 2 до 16")
        
        # rosen_alpha, rosen_beta
        rosen_alpha = settings.get("rosen_alpha", 0.2)
        rosen_beta = settings.get("rosen_beta", 1.0)
        if rosen_alpha <= 0:
            errors.append("rosen_alpha должен быть больше 0")
        if rosen_beta <= 0:
            errors.append("rosen_beta должен быть больше 0")
        
        return len(errors) == 0, errors
    
    # =========================================================================
    # ПРОГРЕСС
    # =========================================================================
    
    def get_progress_range(self, method: str) -> Tuple[int, int]:
        """Получить диапазон прогресса для метода.
        
        Параметры:
        ----------
        method : str
            Имя метода
            
        Возвращает:
        -----------
        Tuple[int, int]
            (start, end) диапазон в процентах
        """
        return self._config.get_progress_range(method)
    
    def calculate_progress(
        self,
        method: str,
        method_progress: float,
    ) -> int:
        """Рассчитать общий прогресс файла.
        
        Параметры:
        ----------
        method : str
            Имя текущего метода
        method_progress : float
            Прогресс внутри метода (0.0 - 1.0)
            
        Возвращает:
        -----------
        int
            Общий прогресс в процентах (0-100)
        """
        start, end = self.get_progress_range(method)
        return start + int(method_progress * (end - start))
    
    def create_progress_callback(
        self,
        method: str,
        emit_progress: Callable[[int], None],
        emit_status: Callable[[str], None],
        is_cancelled: Callable[[], bool],
        format_eta: Optional[Callable[[float], str]] = None,
    ) -> Callable[[float, str], None]:
        """Создать callback для отслеживания прогресса.
        
        Параметры:
        ----------
        method : str
            Имя метода
        emit_progress : Callable[[int], None]
            Функция для отправки прогресса
        emit_status : Callable[[str], None]
            Функция для отправки статуса
        is_cancelled : Callable[[], bool]
            Функция проверки отмены
        format_eta : Optional[Callable[[float], str]]
            Функция форматирования ETA
            
        Возвращает:
        -----------
        Callable[[float, str], None]
            Callback функция
        """
        def callback(frac: float, msg: str) -> None:
            if is_cancelled():
                return
            
            progress = self.calculate_progress(method, frac)
            emit_progress(progress)
            
            if format_eta:
                status = f"{msg} | ETA: {format_eta(0)}"
            else:
                status = msg
            emit_status(status)
        
        return callback
    
    # =========================================================================
    # ETA
    # =========================================================================
    
    def format_eta(self, seconds: float) -> str:
        """Форматировать секунды в строку ETA.
        
        Параметры:
        ----------
        seconds : float
            Количество секунд
            
        Возвращает:
        -----------
        str
            Строка в формате H:MM:SS или MM:SS
        """
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
    
    def estimate_remaining_time(
        self,
        elapsed: float,
        completed_stages: int,
        total_stages: int,
        stage_times: Dict[int, float],
    ) -> float:
        """Оценить оставшееся время.
        
        Параметры:
        ----------
        elapsed : float
            Прошедшее время в секундах
        completed_stages : int
            Количество завершённых стадий
        total_stages : int
            Общее количество стадий
        stage_times : Dict[int, float]
            Время выполнения каждой стадии
            
        Возвращает:
        -----------
        float
            Оценка оставшегося времени в секундах
        """
        if completed_stages >= total_stages:
            return 0.0
        
        # Среднее время на стадию
        if stage_times:
            avg_time = sum(stage_times.values()) / len(stage_times)
        else:
            # Если нет данных, используем прошедшее время
            avg_time = elapsed / max(1, completed_stages)
        
        remaining_stages = total_stages - completed_stages
        return remaining_stages * avg_time
    
    # =========================================================================
    # РЕКОМЕНДАЦИИ
    # =========================================================================
    
    def get_method_recommendations(
        self,
        audio_characteristics: Dict[str, Any],
    ) -> List[Tuple[str, float, str]]:
        """Получить рекомендации по выбору метода.
        
        Параметры:
        ----------
        audio_characteristics : Dict[str, Any]
            Характеристики аудио:
            - duration_sec: длительность
            - sample_rate: частота дискретизации
            - dynamic_range_db: динамический диапазон
            - spectral_centroid_hz: спектральный центроид
            - is_speech: является ли речью
            
        Возвращает:
        -----------
        List[Tuple[str, float, str]]
            Список (метод, оценка, описание) отсортированный по оценке
        """
        recommendations = []
        
        duration = audio_characteristics.get("duration_sec", 0)
        dynamic_range = audio_characteristics.get("dynamic_range_db", 0)
        spectral_centroid = audio_characteristics.get("spectral_centroid_hz", 0)
        is_speech = audio_characteristics.get("is_speech", False)
        
        # FWHT - быстрый для коротких файлов
        if duration < 10:
            recommendations.append((
                "fwht", 0.9,
                "Рекомендуется для коротких файлов (быстрая обработка)"
            ))
        else:
            recommendations.append((
                "fwht", 0.6,
                "Базовый метод, быстрая обработка"
            ))
        
        # FFT - универсальный
        recommendations.append((
            "fft", 0.8,
            "Универсальный метод с хорошим частотным разрешением"
        ))
        
        # DCT - хорошее сжатие
        if dynamic_range > 40:
            recommendations.append((
                "dct", 0.85,
                "Хорошее энергетическое сжатие для файлов с широким динамическим диапазоном"
            ))
        else:
            recommendations.append((
                "dct", 0.7,
                "Стандартный метод с хорошим сжатием"
            ))
        
        # DWT - хорош для низкочастотного контента
        if spectral_centroid < 2000:
            recommendations.append((
                "dwt", 0.85,
                "Рекомендуется для низкочастотного контента"
            ))
        else:
            recommendations.append((
                "dwt", 0.65,
                "Вейвлет-преобразование для частотно-временного анализа"
            ))
        
        # Huffman - хорош для речи
        if is_speech or dynamic_range > 50:
            recommendations.append((
                "huffman", 0.85,
                "Оптимизирован для речевых сигналов"
            ))
        else:
            recommendations.append((
                "huffman", 0.6,
                "μ-law компандирование"
            ))
        
        # Rosenbrock - экспериментальный
        recommendations.append((
            "rosenbrock", 0.5,
            "Экспериментальный метод нелинейного сглаживания"
        ))
        
        # Standard - базовый
        recommendations.append((
            "standard", 0.75,
            "Стандартное MP3 кодирование (базовый метод)"
        ))
        
        # Сортируем по оценке
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "AudioProcessingService",
    "ProgressInfo",
    "ProcessingResult",
]
