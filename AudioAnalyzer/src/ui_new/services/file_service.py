"""
Сервис работы с файловой системой.

Назначение:
- Абстракция над файловой системой
- Поиск исходных и обработанных файлов
- Валидация аудиофайлов
- Управление выходной директорией

Использование:
--------------
>>> from ui_new.services import get_container
>>> container = get_container()
>>> file_service = container.file
>>> 
>>> # Найти исходные файлы
>>> sources = file_service.find_source_files()
>>> 
>>> # Найти обработанные файлы для источника
>>> processed = file_service.find_processed_files("audio.wav")
"""
from __future__ import annotations

import glob
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

from .config import AppConfig

logger = logging.getLogger("ui_new.services.file_service")


# =============================================================================
# СТРУКТУРЫ ДАННЫХ
# =============================================================================

@dataclass
class AudioFileInfo:
    """Информация об аудиофайле."""
    path: str
    name: str
    size_bytes: int
    modified_time: datetime
    is_source: bool  # True если исходный, False если обработанный
    method: Optional[str] = None  # Метод обработки (для обработанных файлов)
    source_name: Optional[str] = None  # Имя исходного файла (для обработанных)
    
    @property
    def size_mb(self) -> float:
        """Размер в мегабайтах."""
        return self.size_bytes / (1024 * 1024)


# =============================================================================
# СЕРВИС РАБОТЫ С ФАЙЛАМИ
# =============================================================================

class FileService:
    """Сервис работы с файловой системой.
    
    Предоставляет:
    - Поиск исходных и обработанных файлов
    - Валидацию аудиофайлов
    - Управление выходной директорией
    - Определение жанров из структуры папок
    
    Атрибуты:
    ----------
    config : AppConfig
        Конфигурация приложения
    """
    
    # Суффиксы обработанных файлов
    METHOD_SUFFIXES: Dict[str, str] = {
        "standard": "_standard",
        "std": "_std",
        "fwht": "_fwht",
        "fft": "_fft",
        "dct": "_dct",
        "dwt": "_dwt",
        "huffman": "_huffman",
        "rosenbrock": "_rosenbrock",
    }
    
    # Обратное отображение: суффикс -> имя метода
    SUFFIX_TO_METHOD: Dict[str, str] = {
        "_standard": "standard",
        "_std": "standard",
        "_fwht": "fwht",
        "_fft": "fft",
        "_dct": "dct",
        "_dwt": "dwt",
        "_huffman": "huffman",
        "_rosenbrock": "rosenbrock",
    }
    
    # Поддерживаемые аудио форматы
    AUDIO_EXTENSIONS: Tuple[str, ...] = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')
    
    def __init__(self, config: AppConfig):
        """Инициализация сервиса.
        
        Параметры:
        ----------
        config : AppConfig
            Конфигурация приложения
        """
        self._config = config
        logger.debug("FileService initialized")
    
    # =========================================================================
    # ПОИСК ФАЙЛОВ
    # =========================================================================
    
    def find_source_files(
        self,
        directory: Optional[str] = None,
        recursive: bool = True,
    ) -> List[AudioFileInfo]:
        """Найти исходные аудиофайлы.
        
        Параметры:
        ----------
        directory : Optional[str]
            Директория для поиска. Если None, используется test_data_dir.
        recursive : bool
            Рекурсивный поиск в подпапках
            
        Возвращает:
        -----------
        List[AudioFileInfo]
            Список информации о найденных файлах
        """
        search_dir = Path(directory) if directory else self._config.test_data_dir
        
        if not search_dir.exists():
            logger.warning(f"Source directory does not exist: {search_dir}")
            return []
        
        files = []
        pattern = "**/*.wav" if recursive else "*.wav"
        
        for path in search_dir.glob(pattern):
            if path.is_file():
                try:
                    info = self._create_file_info(str(path), is_source=True)
                    files.append(info)
                except Exception as e:
                    logger.warning(f"Error reading file {path}: {e}")
        
        logger.info(f"Found {len(files)} source files in {search_dir}")
        return files
    
    def find_processed_files(
        self,
        source_name: Optional[str] = None,
        directory: Optional[str] = None,
    ) -> List[AudioFileInfo]:
        """Найти обработанные файлы.
        
        Параметры:
        ----------
        source_name : Optional[str]
            Имя исходного файла (для фильтрации). Если None, возвращает все.
        directory : Optional[str]
            Директория для поиска. Если None, используется output_dir.
            
        Возвращает:
        -----------
        List[AudioFileInfo]
            Список информации о найденных файлах
        """
        search_dir = Path(directory) if directory else self._config.output_dir
        
        if not search_dir.exists():
            logger.warning(f"Output directory does not exist: {search_dir}")
            return []
        
        files = []
        
        for path in search_dir.glob("*.mp3"):
            if path.is_file():
                try:
                    info = self._create_file_info(str(path), is_source=False)
                    
                    # Фильтрация по имени исходного файла
                    if source_name:
                        base_source = Path(source_name).stem
                        if info.source_name != base_source:
                            continue
                    
                    files.append(info)
                except Exception as e:
                    logger.warning(f"Error reading file {path}: {e}")
        
        logger.info(f"Found {len(files)} processed files in {search_dir}")
        return files
    
    def find_available_sources(
        self,
        results: List[Any],
        current_path: Optional[str] = None,
        dataset_folder: Optional[str] = None,
    ) -> List[Tuple[str, str]]:
        """Найти доступные исходные файлы для спектрального анализа.
        
        Ищет в:
        1. Результатах обработки
        2. Текущем выбранном файле
        3. Папке с данными
        4. Выходной папке (исходные WAV)
        
        Параметры:
        ----------
        results : List[Any]
            Результаты обработки (ResultRow или словари)
        current_path : Optional[str]
            Текущий выбранный путь
        dataset_folder : Optional[str]
            Папка с набором данных
            
        Возвращает:
        -----------
        List[Tuple[str, str]]
            Список кортежей (имя_файла, путь)
        """
        sources: Dict[str, str] = {}  # name -> path
        
        # 1. Из результатов обработки
        for r in results:
            source = getattr(r, 'source', None) or r.get('source') if isinstance(r, dict) else None
            if source and source not in sources:
                path = self._locate_source_file(
                    source, 
                    getattr(r, 'path', None) or r.get('path') if isinstance(r, dict) else None,
                    dataset_folder
                )
                if path:
                    sources[source] = path
        
        # 2. Из текущего выбранного файла
        if current_path and os.path.exists(current_path):
            name = os.path.basename(current_path)
            sources[name] = current_path
        
        # 3. Из папки с данными
        if dataset_folder and os.path.isdir(dataset_folder):
            for root, _, files in os.walk(dataset_folder):
                for f in files:
                    if f.endswith('.wav') and f not in sources:
                        path = os.path.join(root, f)
                        sources[f] = path
        
        # 4. Из выходной папки - исходные WAV без суффикса метода
        output_dir = self._config.output_dir
        if output_dir.exists():
            for f in os.listdir(str(output_dir)):
                if f.endswith('.wav'):
                    base = os.path.splitext(f)[0]
                    # Проверяем что это не обработанный файл
                    is_processed = any(
                        base.endswith(suffix) 
                        for suffix in self.SUFFIX_TO_METHOD.keys()
                    )
                    if not is_processed and f not in sources:
                        path = str(output_dir / f)
                        sources[f] = path
        
        result = list(sources.items())
        logger.info(f"Found {len(result)} available sources")
        return result
    
    def _locate_source_file(
        self,
        source_name: str,
        result_path: Optional[str] = None,
        dataset_folder: Optional[str] = None,
    ) -> Optional[str]:
        """Локализовать исходный файл.
        
        Параметры:
        ----------
        source_name : str
            Имя исходного файла
        result_path : Optional[str]
            Путь к результату обработки
        dataset_folder : Optional[str]
            Папка с набором данных
            
        Возвращает:
        -----------
        Optional[str]
            Путь к исходному файлу или None
        """
        base_name = os.path.splitext(source_name)[0]
        
        possible_paths = []
        
        # В директории обработанного файла
        if result_path:
            possible_paths.append(os.path.join(os.path.dirname(result_path), source_name))
        
        # В выходной директории
        possible_paths.append(str(self._config.output_dir / source_name))
        possible_paths.append(str(self._config.output_dir / (base_name + '.wav')))
        
        # В папке с данными
        if dataset_folder and os.path.isdir(dataset_folder):
            for root, _, files in os.walk(dataset_folder):
                if source_name in files:
                    possible_paths.append(os.path.join(root, source_name))
        
        for p in possible_paths:
            if os.path.exists(p):
                return p
        
        return None
    
    # =========================================================================
    # ИНФОРМАЦИЯ О ФАЙЛАХ
    # =========================================================================
    
    def _create_file_info(self, path: str, is_source: bool) -> AudioFileInfo:
        """Создать информацию о файле.
        
        Параметры:
        ----------
        path : str
            Путь к файлу
        is_source : bool
            True если исходный файл
            
        Возвращает:
        -----------
        AudioFileInfo
            Информация о файле
        """
        stat = os.stat(path)
        name = os.path.basename(path)
        
        method = None
        source_name = None
        
        if not is_source:
            # Определяем метод и имя источника для обработанного файла
            base = os.path.splitext(name)[0]
            for suffix, method_name in self.SUFFIX_TO_METHOD.items():
                if base.endswith(suffix):
                    method = method_name
                    source_name = base[:-len(suffix)]
                    break
        
        return AudioFileInfo(
            path=path,
            name=name,
            size_bytes=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            is_source=is_source,
            method=method,
            source_name=source_name,
        )
    
    def get_file_size(self, path: str) -> int:
        """Получить размер файла в байтах.
        
        Параметры:
        ----------
        path : str
            Путь к файлу
            
        Возвращает:
        -----------
        int
            Размер в байтах, или 0 если файл не существует
        """
        try:
            return os.path.getsize(path)
        except Exception:
            return 0
    
    def get_file_size_mb(self, path: str) -> float:
        """Получить размер файла в мегабайтах.
        
        Параметры:
        ----------
        path : str
            Путь к файлу
            
        Возвращает:
        -----------
        float
            Размер в МБ
        """
        return self.get_file_size(path) / (1024 * 1024)
    
    # =========================================================================
    # ВАЛИДАЦИЯ
    # =========================================================================
    
    def validate_audio_file(self, path: str) -> Tuple[bool, str]:
        """Валидировать аудиофайл.
        
        Параметры:
        ----------
        path : str
            Путь к файлу
            
        Возвращает:
        -----------
        Tuple[bool, str]
            (is_valid, error_message)
        """
        if not os.path.exists(path):
            return False, f"Файл не существует: {path}"
        
        ext = os.path.splitext(path)[1].lower()
        if ext not in self.AUDIO_EXTENSIONS:
            return False, f"Неподдерживаемый формат: {ext}"
        
        # Проверка размера файла
        size = self.get_file_size(path)
        if size == 0:
            return False, "Файл пуст"
        
        if size > 500 * 1024 * 1024:  # 500 MB
            return False, "Файл слишком большой (максимум 500 MB)"
        
        return True, ""
    
    def is_valid_wav(self, path: str) -> bool:
        """Проверить что файл является валидным WAV.
        
        Параметры:
        ----------
        path : str
            Путь к файлу
            
        Возвращает:
        -----------
        bool
            True если файл валидный WAV
        """
        is_valid, _ = self.validate_audio_file(path)
        if not is_valid:
            return False
        
        # Проверяем RIFF заголовок
        try:
            with open(path, 'rb') as f:
                header = f.read(12)
                if len(header) < 12:
                    return False
                if header[:4] != b'RIFF':
                    return False
                if header[8:12] != b'WAVE':
                    return False
                return True
        except Exception:
            return False
    
    # =========================================================================
    # УПРАВЛЕНИЕ ДИРЕКТОРИЯМИ
    # =========================================================================
    
    def ensure_output_dir(self) -> None:
        """Создать выходную директорию если её нет."""
        self._config.output_dir.mkdir(parents=True, exist_ok=True)
    
    def clear_output_dir(self, confirm: bool = False) -> Tuple[int, List[str]]:
        """Очистить выходную директорию.
        
        Параметры:
        ----------
        confirm : bool
            Подтверждение очистки (безопасность)
            
        Возвращает:
        -----------
        Tuple[int, List[str]]
            (количество удалённых файлов, список ошибок)
        """
        if not confirm:
            return 0, ["Требуется подтверждение для очистки"]
        
        output_dir = self._config.output_dir
        if not output_dir.exists():
            return 0, []
        
        deleted_count = 0
        errors = []
        
        for item in output_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    deleted_count += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    deleted_count += 1
            except Exception as e:
                errors.append(f"Ошибка удаления {item}: {e}")
        
        logger.info(f"Cleared output directory: {deleted_count} items deleted")
        return deleted_count, errors
    
    def get_genre_from_path(
        self,
        file_path: str,
        dataset_root: Optional[str] = None,
    ) -> Optional[str]:
        """Определить жанр из пути к файлу.
        
        Жанр определяется как первая подпапка относительно dataset_root.
        
        Параметры:
        ----------
        file_path : str
            Путь к файлу
        dataset_root : Optional[str]
            Корневая папка набора данных
            
        Возвращает:
        -----------
        Optional[str]
            Жанр или None
        """
        if not dataset_root:
            return None
        
        try:
            rel = os.path.relpath(os.path.dirname(file_path), dataset_root)
            parts = rel.split(os.sep)
            return parts[0] if parts and parts[0] not in ('.', '') else None
        except Exception:
            return None


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "FileService",
    "AudioFileInfo",
]
