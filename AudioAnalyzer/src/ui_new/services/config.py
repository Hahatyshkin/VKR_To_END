"""
Централизованная конфигурация приложения.

Назначение:
- Единая точка для всех настраиваемых параметров
- Иммутабельная конфигурация (frozen dataclass)
- Валидация параметров при создании
- Поддержка загрузки из файла/переменных окружения

Использование:
--------------
>>> from ui_new.services.config import create_app_config
>>> config = create_app_config()
>>> print(config.output_dir)
"""
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("ui_new.services.config")


# =============================================================================
# КОНСТАНТЫ ПРОГРЕССА
# =============================================================================

# Прогресс файла - диапазоны для каждого метода (start, end)
PROGRESS_RANGES: Dict[str, Tuple[int, int]] = {
    "fwht": (5, 18),
    "fft": (18, 30),
    "dct": (30, 42),
    "dwt": (42, 54),
    "huffman": (54, 66),
    "rosenbrock": (66, 78),
    "standard": (78, 88),
    "daubechies": (88, 94),
    "mdct": (94, 100),
}

# Базовый прогресс (до начала обработки)
PROGRESS_BASE: int = 5

# Диапазон прогресса для обработки
PROGRESS_RANGE: int = 50

# Максимальное количество точек на графике спектра
SPECTRUM_MAX_POINTS: int = 2000

# Частота дискретизации для спектрального анализа
SPECTRUM_SAMPLE_RATE: int = 44100


# =============================================================================
# КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ
# =============================================================================

@dataclass(frozen=True)
class AppConfig:
    """Иммутабельная конфигурация приложения.
    
    Все параметры доступны только для чтения.
    Для изменения конфигурации создаётся новый экземпляр.
    
    Атрибуты:
    ----------
    project_root : Path
        Корневая директория проекта
    output_dir : Path
        Директория для выходных файлов
    test_data_dir : Path
        Директория с тестовыми данными
    logs_dir : Path
        Директория для логов
    window_width : int
        Ширина окна по умолчанию
    window_height : int
        Высота окна по умолчанию
    max_spectrum_points : int
        Максимальное количество точек на графике спектра
    progress_ranges : Dict[str, Tuple[int, int]]
        Диапазоны прогресса для каждого метода
    theme : str
        Текущая тема ('light' или 'dark')
    """
    
    # Пути
    project_root: Path
    output_dir: Path
    test_data_dir: Path
    logs_dir: Path
    
    # Размеры окна
    window_width: int = 1100
    window_height: int = 650
    
    # Параметры спектра
    max_spectrum_points: int = SPECTRUM_MAX_POINTS
    spectrum_sample_rate: int = SPECTRUM_SAMPLE_RATE
    
    # Прогресс
    progress_ranges: Dict[str, Tuple[int, int]] = field(
        default_factory=lambda: dict(PROGRESS_RANGES)
    )
    
    # Тема
    theme: str = "light"
    
    # Максимальное количество файлов в истории
    max_history_items: int = 100
    
    def __post_init__(self) -> None:
        """Валидация после инициализации."""
        # Используем object.__setattr__ для frozen dataclass
        if self.window_width < 800:
            object.__setattr__(self, 'window_width', 800)
        if self.window_height < 600:
            object.__setattr__(self, 'window_height', 600)
        if self.max_spectrum_points < 100:
            object.__setattr__(self, 'max_spectrum_points', 100)
    
    @property
    def output_dir_str(self) -> str:
        """Путь к выходной директории как строка."""
        return str(self.output_dir)
    
    @property
    def project_root_str(self) -> str:
        """Путь к корневой директории как строка."""
        return str(self.project_root)
    
    def get_progress_range(self, method: str) -> Tuple[int, int]:
        """Получить диапазон прогресса для метода.
        
        Параметры:
        ----------
        method : str
            Имя метода (fwht, fft, dct, dwt, huffman, rosenbrock, standard)
            
        Возвращает:
        -----------
        Tuple[int, int]
            Кортеж (start, end) диапазона прогресса
        """
        return self.progress_ranges.get(method, (0, 100))
    
    def ensure_directories(self) -> None:
        """Создать необходимые директории если их нет."""
        for directory in [self.output_dir, self.logs_dir]:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Директория готова: {directory}")
            except Exception as e:
                logger.warning(f"Не удалось создать директорию {directory}: {e}")
    
    def with_theme(self, theme: str) -> 'AppConfig':
        """Создать новую конфигурацию с другой темой.
        
        Параметры:
        ----------
        theme : str
            Новая тема ('light' или 'dark')
            
        Возвращает:
        -----------
        AppConfig
            Новая конфигурация с изменённой темой
        """
        return AppConfig(
            project_root=self.project_root,
            output_dir=self.output_dir,
            test_data_dir=self.test_data_dir,
            logs_dir=self.logs_dir,
            window_width=self.window_width,
            window_height=self.window_height,
            max_spectrum_points=self.max_spectrum_points,
            spectrum_sample_rate=self.spectrum_sample_rate,
            progress_ranges=self.progress_ranges,
            theme=theme,
            max_history_items=self.max_history_items,
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """Создать конфигурацию из словаря.
        
        Параметры:
        ----------
        data : Dict[str, Any]
            Словарь с параметрами
            
        Возвращает:
        -----------
        AppConfig
            Новая конфигурация
        """
        return cls(
            project_root=Path(data.get('project_root', '.')),
            output_dir=Path(data.get('output_dir', './output')),
            test_data_dir=Path(data.get('test_data_dir', './test_data')),
            logs_dir=Path(data.get('logs_dir', './logs')),
            window_width=data.get('window_width', 1100),
            window_height=data.get('window_height', 650),
            max_spectrum_points=data.get('max_spectrum_points', SPECTRUM_MAX_POINTS),
            spectrum_sample_rate=data.get('spectrum_sample_rate', SPECTRUM_SAMPLE_RATE),
            theme=data.get('theme', 'light'),
            max_history_items=data.get('max_history_items', 100),
        )


def create_app_config(
    project_root: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    test_data_dir: Optional[Path] = None,
    logs_dir: Optional[Path] = None,
    theme: str = "light",
) -> AppConfig:
    """Создать конфигурацию приложения с автоматическим определением путей.
    
    Параметры:
    ----------
    project_root : Optional[Path]
        Корневая директория проекта (автоопределение если None)
    output_dir : Optional[Path]
        Директория для выходных файлов
    test_data_dir : Optional[Path]
        Директория с тестовыми данными
    logs_dir : Optional[Path]
        Директория для логов
    theme : str
        Тема интерфейса ('light' или 'dark')
        
    Возвращает:
    -----------
    AppConfig
        Конфигурация приложения
    """
    # Автоопределение корневой директории
    if project_root is None:
        # Определяем по расположению этого файла
        current_file = Path(__file__).resolve()
        # src/ui_new/services/config.py -> project root
        project_root = current_file.parent.parent.parent.parent
    
    # Определяем выходную директорию
    if output_dir is None:
        if getattr(sys, 'frozen', False):
            # Запущен как .exe
            output_dir = Path(sys.executable).parent / "output"
        else:
            output_dir = project_root / "output"
    
    # Определяем директорию тестовых данных
    if test_data_dir is None:
        test_data_dir = project_root / "default_test_data"
    
    # Определяем директорию логов
    if logs_dir is None:
        logs_dir = project_root / "logs"
    
    config = AppConfig(
        project_root=project_root,
        output_dir=output_dir,
        test_data_dir=test_data_dir,
        logs_dir=logs_dir,
        theme=theme,
    )
    
    # Создаём директории
    config.ensure_directories()
    
    logger.info(
        f"Конфигурация создана: project_root={project_root}, "
        f"output_dir={output_dir}, theme={theme}"
    )
    
    return config


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "AppConfig",
    "create_app_config",
    "PROGRESS_RANGES",
    "PROGRESS_BASE",
    "PROGRESS_RANGE",
    "SPECTRUM_MAX_POINTS",
    "SPECTRUM_SAMPLE_RATE",
]
