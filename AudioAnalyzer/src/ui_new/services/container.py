"""
DI контейнер для управления сервисами.

Назначение:
- Централизованное создание и управление сервисами
- Внедрение зависимостей через конструктор
- Singleton паттерн для сервисов
- Ленивая инициализация сервисов

Использование:
--------------
>>> from ui_new.services.container import init_container, get_container
>>> 
>>> # Инициализация при старте приложения
>>> init_container()
>>> 
>>> # Получение сервиса
>>> container = get_container()
>>> audio_service = container.audio_processing
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, Type, TypeVar, Callable
from pathlib import Path

from .config import AppConfig, create_app_config

logger = logging.getLogger("ui_new.services.container")

# Тип для сервисов
T = TypeVar('T')


class ServiceContainer:
    """DI контейнер для управления сервисами.
    
    Предоставляет:
    - Ленивую инициализацию сервисов
    - Singleton паттерн для каждого сервиса
    - Централизованный доступ к конфигурации
    - Возможность подмены сервисов для тестирования
    
    Атрибуты:
    ----------
    config : AppConfig
        Конфигурация приложения
    
    Пример:
    -------
    >>> container = ServiceContainer()
    >>> audio_service = container.audio_processing
    >>> spectrum_service = container.spectrum
    """
    
    def __init__(self, config: Optional[AppConfig] = None):
        """Инициализация контейнера.
        
        Параметры:
        ----------
        config : Optional[AppConfig]
            Конфигурация приложения. Если None, создаётся автоматически.
        """
        self._config = config or create_app_config()
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        
        logger.debug("ServiceContainer initialized")
    
    @property
    def config(self) -> AppConfig:
        """Получить конфигурацию."""
        return self._config
    
    @property
    def audio_processing(self) -> 'AudioProcessingService':
        """Получить сервис обработки аудио."""
        return self._get_service(
            'audio_processing',
            lambda: self._create_audio_processing_service()
        )
    
    @property
    def spectrum(self) -> 'SpectrumService':
        """Получить сервис спектрального анализа."""
        return self._get_service(
            'spectrum',
            lambda: self._create_spectrum_service()
        )
    
    @property
    def file(self) -> 'FileService':
        """Получить сервис работы с файлами."""
        return self._get_service(
            'file',
            lambda: self._create_file_service()
        )
    
    def _get_service(self, name: str, factory: Callable[[], T]) -> T:
        """Получить сервис с ленивой инициализацией.
        
        Параметры:
        ----------
        name : str
            Имя сервиса
        factory : Callable[[], T]
            Фабрика для создания сервиса
            
        Возвращает:
        -----------
        T
            Экземпляр сервиса
        """
        if name not in self._services:
            self._services[name] = factory()
            logger.debug(f"Service created: {name}")
        return self._services[name]
    
    def _create_audio_processing_service(self) -> 'AudioProcessingService':
        """Создать сервис обработки аудио."""
        from .audio_service import AudioProcessingService
        return AudioProcessingService(config=self._config)
    
    def _create_spectrum_service(self) -> 'SpectrumService':
        """Создать сервис спектрального анализа."""
        from .spectrum_service import SpectrumService
        return SpectrumService(config=self._config)
    
    def _create_file_service(self) -> 'FileService':
        """Создать сервис работы с файлами."""
        from .file_service import FileService
        return FileService(config=self._config)
    
    def register_service(self, name: str, service: Any) -> None:
        """Зарегистрировать сервис вручную.
        
        Полезно для тестирования или подмены реализаций.
        
        Параметры:
        ----------
        name : str
            Имя сервиса
        service : Any
            Экземпляр сервиса
        """
        self._services[name] = service
        logger.debug(f"Service registered: {name}")
    
    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """Зарегистрировать фабрику для сервиса.
        
        Параметры:
        ----------
        name : str
            Имя сервиса
        factory : Callable[[], Any]
            Фабрика для создания сервиса
        """
        self._factories[name] = factory
        logger.debug(f"Factory registered: {name}")
    
    def clear(self) -> None:
        """Очистить все сервисы.
        
        Полезно для тестирования.
        """
        self._services.clear()
        self._factories.clear()
        logger.debug("ServiceContainer cleared")
    
    def reconfigure(self, config: AppConfig) -> None:
        """Переконфигурировать контейнер.
        
        Внимание: это очистит все существующие сервисы!
        
        Параметры:
        ----------
        config : AppConfig
            Новая конфигурация
        """
        self.clear()
        self._config = config
        logger.info("ServiceContainer reconfigured")


# =============================================================================
# Глобальный экземпляр контейнера
# =============================================================================

_container: Optional[ServiceContainer] = None


def init_container(config: Optional[AppConfig] = None) -> ServiceContainer:
    """Инициализировать глобальный контейнер.
    
    Должна вызываться один раз при старте приложения.
    
    Параметры:
    ----------
    config : Optional[AppConfig]
        Конфигурация приложения. Если None, создаётся автоматически.
        
    Возвращает:
    -----------
    ServiceContainer
        Инициализированный контейнер
    """
    global _container
    
    if _container is not None:
        logger.warning("Container already initialized, reinitializing...")
    
    _container = ServiceContainer(config=config)
    logger.info("Global container initialized")
    return _container


def get_container() -> ServiceContainer:
    """Получить глобальный контейнер.
    
    Если контейнер не инициализирован, создаётся автоматически.
    
    Возвращает:
    -----------
    ServiceContainer
        Глобальный контейнер
    """
    global _container
    
    if _container is None:
        logger.info("Container not initialized, auto-initializing...")
        _container = ServiceContainer()
    
    return _container


def reset_container() -> None:
    """Сбросить глобальный контейнер.
    
    Полезно для тестирования.
    """
    global _container
    
    if _container is not None:
        _container.clear()
    _container = None
    logger.debug("Global container reset")


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "ServiceContainer",
    "init_container",
    "get_container",
    "reset_container",
]
