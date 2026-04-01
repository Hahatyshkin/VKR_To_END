"""
Сервисы бизнес-логики для AudioAnalyzer.

Этот модуль содержит сервисы, которые выносят бизнес-логику из UI миксинов.
Сервисы следуют принципу Single Responsibility и внедряются через DI контейнер.

Архитектура:
============
- AppConfig: централизованная конфигурация приложения
- ServiceContainer: DI контейнер для управления сервисами
- AudioProcessingService: координация обработки аудио
- SpectrumService: вычисление и сравнение спектров
- FileService: работа с файловой системой

Использование:
--------------
from ui_new.services import get_container

container = get_container()
audio_service = container.audio_processing
result = audio_service.process_file("audio.wav", settings)
"""

from .container import ServiceContainer, get_container, init_container, reset_container
from .config import AppConfig, create_app_config
from .audio_service import AudioProcessingService
from .spectrum_service import SpectrumService
from .file_service import FileService

__all__ = [
    # DI Container
    "ServiceContainer",
    "get_container",
    "init_container",
    "reset_container",
    # Config
    "AppConfig",
    "create_app_config",
    # Services
    "AudioProcessingService",
    "SpectrumService",
    "FileService",
]
