"""
Профили методов для AudioAnalyzer.

Назначение:
- Сохранение и загрузка профилей настроек
- Предустановленные профили для разных сценариев
- Экспорт/импорт профилей

Использование:
--------------
>>> from ui_new.profiles import ProfileManager, get_profile
>>> 
>>> # Получить профиль
>>> profile = get_profile('speech_fast')
>>> settings = profile.settings
>>> 
>>> # Сохранить профиль
>>> manager = ProfileManager()
>>> manager.save_profile('my_profile', settings)
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ui_new.profiles")


# =============================================================================
# СТРУКТУРА ПРОФИЛЯ
# =============================================================================

@dataclass
class MethodProfile:
    """Профиль настроек метода.
    
    Атрибуты:
    ----------
    name : str
        Имя профиля
    description : str
        Описание профиля
    settings : Dict[str, Any]
        Настройки обработки
    created_at : Optional[str]
        Дата создания (ISO формат)
    tags : List[str]
        Теги для категоризации
    """
    name: str
    description: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MethodProfile':
        """Создать из словаря."""
        return cls(
            name=data.get('name', 'Unknown'),
            description=data.get('description', ''),
            settings=data.get('settings', {}),
            created_at=data.get('created_at'),
            tags=data.get('tags', []),
        )


# =============================================================================
# ПРЕДУСТАНОВЛЕННЫЕ ПРОФИЛИ
# =============================================================================

BUILTIN_PROFILES: Dict[str, MethodProfile] = {
    # Стандартный профиль
    'standard': MethodProfile(
        name='Стандартный',
        description='Базовые настройки для общего использования',
        settings={
            'block_size': 2048,
            'bitrate': '192k',
            'select_mode': 'none',
            'keep_energy_ratio': 1.0,
            'sequency_keep_ratio': 1.0,
            'levels': 4,
            'mu': 255.0,
            'bits': 8,
            'rosen_alpha': 0.2,
            'rosen_beta': 1.0,
        },
        tags=['default', 'general'],
    ),
    
    # Быстрая обработка
    'fast': MethodProfile(
        name='Быстрый',
        description='Оптимизация скорости обработки. Меньший размер блока и битрейт.',
        settings={
            'block_size': 1024,
            'bitrate': '128k',
            'select_mode': 'none',
            'keep_energy_ratio': 1.0,
            'sequency_keep_ratio': 1.0,
            'levels': 3,
            'mu': 255.0,
            'bits': 8,
            'rosen_alpha': 0.2,
            'rosen_beta': 1.0,
        },
        tags=['speed', 'preview'],
    ),
    
    # Высокое качество
    'quality': MethodProfile(
        name='Качество',
        description='Максимальное качество. Больший размер блока и высокий битрейт.',
        settings={
            'block_size': 4096,
            'bitrate': '320k',
            'select_mode': 'energy',
            'keep_energy_ratio': 0.98,
            'sequency_keep_ratio': 0.95,
            'levels': 5,
            'mu': 255.0,
            'bits': 12,
            'rosen_alpha': 0.1,
            'rosen_beta': 1.0,
        },
        tags=['quality', 'archive'],
    ),
    
    # Речь
    'speech': MethodProfile(
        name='Речь',
        description='Оптимизация для речевых файлов. Энергетический отбор.',
        settings={
            'block_size': 2048,
            'bitrate': '128k',
            'select_mode': 'energy',
            'keep_energy_ratio': 0.90,
            'sequency_keep_ratio': 0.85,
            'levels': 4,
            'mu': 255.0,
            'bits': 8,
            'rosen_alpha': 0.3,
            'rosen_beta': 1.0,
        },
        tags=['speech', 'podcast', 'voice'],
    ),
    
    # Музыка
    'music': MethodProfile(
        name='Музыка',
        description='Оптимизация для музыкальных файлов.',
        settings={
            'block_size': 4096,
            'bitrate': '256k',
            'select_mode': 'energy',
            'keep_energy_ratio': 0.95,
            'sequency_keep_ratio': 0.90,
            'levels': 5,
            'mu': 255.0,
            'bits': 10,
            'rosen_alpha': 0.15,
            'rosen_beta': 1.0,
        },
        tags=['music', 'audio'],
    ),
    
    # Подкаст
    'podcast': MethodProfile(
        name='Подкаст',
        description='Баланс качества и размера для подкастов.',
        settings={
            'block_size': 2048,
            'bitrate': '192k',
            'select_mode': 'energy',
            'keep_energy_ratio': 0.92,
            'sequency_keep_ratio': 0.88,
            'levels': 4,
            'mu': 255.0,
            'bits': 9,
            'rosen_alpha': 0.25,
            'rosen_beta': 1.0,
        },
        tags=['podcast', 'speech', 'voice'],
    ),
    
    # Сжатие
    'compression': MethodProfile(
        name='Сжатие',
        description='Максимальное сжатие. Агрессивный отбор коэффициентов.',
        settings={
            'block_size': 2048,
            'bitrate': '128k',
            'select_mode': 'energy',
            'keep_energy_ratio': 0.80,
            'sequency_keep_ratio': 0.75,
            'levels': 4,
            'mu': 127.0,
            'bits': 6,
            'rosen_alpha': 0.4,
            'rosen_beta': 1.0,
        },
        tags=['compression', 'small'],
    ),
}


# =============================================================================
# МЕНЕДЖЕР ПРОФИЛЕЙ
# =============================================================================

class ProfileManager:
    """Менеджер профилей настроек.
    
    Предоставляет:
    - Загрузку и сохранение профилей
    - Список доступных профилей
    - Импорт/экспорт профилей
    
    Атрибуты:
    ----------
    profiles_dir : Path
        Директория для хранения пользовательских профилей
    """
    
    def __init__(self, profiles_dir: Optional[Path] = None):
        """Инициализация менеджера.
        
        Параметры:
        ----------
        profiles_dir : Optional[Path]
            Директория для хранения профилей
        """
        if profiles_dir is None:
            # По умолчанию в папке конфигурации пользователя
            config_dir = Path.home() / ".audioanalyzer"
            profiles_dir = config_dir / "profiles"
        
        self._profiles_dir = profiles_dir
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Загружаем пользовательские профили
        self._custom_profiles: Dict[str, MethodProfile] = {}
        self._load_custom_profiles()
        
        logger.debug(f"ProfileManager initialized with dir: {profiles_dir}")
    
    def get_profile(self, name: str) -> Optional[MethodProfile]:
        """Получить профиль по имени.
        
        Параметры:
        ----------
        name : str
            Имя профиля
            
        Возвращает:
        -----------
        Optional[MethodProfile]
            Профиль или None если не найден
        """
        # Сначала ищем в пользовательских
        if name in self._custom_profiles:
            return self._custom_profiles[name]
        
        # Затем в встроенных
        if name in BUILTIN_PROFILES:
            return BUILTIN_PROFILES[name]
        
        return None
    
    def get_all_profiles(self) -> Dict[str, MethodProfile]:
        """Получить все профили.
        
        Возвращает:
        -----------
        Dict[str, MethodProfile]
            Словарь всех профилей
        """
        profiles = dict(BUILTIN_PROFILES)
        profiles.update(self._custom_profiles)
        return profiles
    
    def get_profile_names(self) -> List[str]:
        """Получить имена всех профилей.
        
        Возвращает:
        -----------
        List[str]
            Список имён профилей
        """
        names = list(BUILTIN_PROFILES.keys())
        names.extend(self._custom_profiles.keys())
        return names
    
    def save_profile(
        self,
        name: str,
        settings: Dict[str, Any],
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Сохранить профиль.
        
        Параметры:
        ----------
        name : str
            Имя профиля
        settings : Dict[str, Any]
            Настройки
        description : str
            Описание
        tags : Optional[List[str]]
            Теги
            
        Возвращает:
        -----------
        bool
            True если сохранение успешно
        """
        from datetime import datetime
        
        profile = MethodProfile(
            name=name,
            description=description,
            settings=settings,
            created_at=datetime.now().isoformat(),
            tags=tags or [],
        )
        
        # Сохраняем в память
        self._custom_profiles[name] = profile
        
        # Сохраняем в файл
        try:
            profile_path = self._profiles_dir / f"{name}.json"
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Profile saved: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving profile {name}: {e}")
            return False
    
    def delete_profile(self, name: str) -> bool:
        """Удалить профиль.
        
        Параметры:
        ----------
        name : str
            Имя профиля
            
        Возвращает:
        -----------
        bool
            True если удаление успешно
        """
        # Нельзя удалить встроенный профиль
        if name in BUILTIN_PROFILES:
            logger.warning(f"Cannot delete built-in profile: {name}")
            return False
        
        # Удаляем из памяти
        if name in self._custom_profiles:
            del self._custom_profiles[name]
        
        # Удаляем файл
        try:
            profile_path = self._profiles_dir / f"{name}.json"
            if profile_path.exists():
                profile_path.unlink()
            
            logger.info(f"Profile deleted: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting profile {name}: {e}")
            return False
    
    def export_profile(self, name: str, export_path: str) -> bool:
        """Экспортировать профиль в файл.
        
        Параметры:
        ----------
        name : str
            Имя профиля
        export_path : str
            Путь для экспорта
            
        Возвращает:
        -----------
        bool
            True если экспорт успешен
        """
        profile = self.get_profile(name)
        if not profile:
            logger.warning(f"Profile not found: {name}")
            return False
        
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Profile exported: {name} -> {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting profile: {e}")
            return False
    
    def import_profile(self, import_path: str) -> Optional[str]:
        """Импортировать профиль из файла.
        
        Параметры:
        ----------
        import_path : str
            Путь к файлу профиля
            
        Возвращает:
        -----------
        Optional[str]
            Имя импортированного профиля или None
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            profile = MethodProfile.from_dict(data)
            
            # Сохраняем
            self._custom_profiles[profile.name] = profile
            
            # Сохраняем в файл
            profile_path = self._profiles_dir / f"{profile.name}.json"
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Profile imported: {profile.name}")
            return profile.name
            
        except Exception as e:
            logger.error(f"Error importing profile: {e}")
            return None
    
    def _load_custom_profiles(self) -> None:
        """Загрузить пользовательские профили."""
        if not self._profiles_dir.exists():
            return
        
        for profile_file in self._profiles_dir.glob("*.json"):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                profile = MethodProfile.from_dict(data)
                self._custom_profiles[profile.name] = profile
                
            except Exception as e:
                logger.warning(f"Error loading profile {profile_file}: {e}")


# =============================================================================
# ФУНКЦИИ УДОБСТВА
# =============================================================================

def get_profile(name: str) -> Optional[MethodProfile]:
    """Получить профиль по имени.
    
    Параметры:
    ----------
    name : str
        Имя профиля
        
    Возвращает:
    -----------
    Optional[MethodProfile]
        Профиль или None
    """
    manager = ProfileManager()
    return manager.get_profile(name)


def get_all_profiles() -> Dict[str, MethodProfile]:
    """Получить все профили.
    
    Возвращает:
    -----------
    Dict[str, MethodProfile]
        Словарь профилей
    """
    manager = ProfileManager()
    return manager.get_all_profiles()


def apply_profile_to_settings(
    profile_name: str,
    current_settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Применить профиль к настройкам.
    
    Параметры:
    ----------
    profile_name : str
        Имя профиля
    current_settings : Dict[str, Any]
        Текущие настройки
        
    Возвращает:
    -----------
    Dict[str, Any]
        Обновлённые настройки
    """
    profile = get_profile(profile_name)
    if not profile:
        return current_settings
    
    # Копируем текущие настройки и обновляем из профиля
    new_settings = dict(current_settings)
    new_settings.update(profile.settings)
    
    return new_settings


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "MethodProfile",
    "ProfileManager",
    "BUILTIN_PROFILES",
    "get_profile",
    "get_all_profiles",
    "apply_profile_to_settings",
]
