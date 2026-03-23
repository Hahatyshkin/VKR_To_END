"""
ui_new — единый модуль пользовательского интерфейса AudioAnalyzer.

Содержимое:
- main_window.py: Главное окно приложения
- worker.py: Фоновая обработка аудио
- constants.py: Константы UI (VARIANTS, METRIC_KEYS, ...)
- presets.py: Пресеты настроек
- log_handler.py: Логирование в UI
- services/: DI контейнер и сервисы бизнес-логики
- themes.py: Темы оформления
- profiles_new.py: Профили методов
- cli.py: CLI интерфейс

Использование:
    # Импорт GUI-компонентов (требует PySide6):
    from ui_new.main_window import MainWindow
    
    # Импорт backend-модулей (без PySide6):
    from ui_new.worker import Worker, create_default_registry
    from ui_new.constants import VARIANTS, METRIC_KEYS
"""

# Backend модули - можно импортировать без PySide6
from .constants import VARIANTS, METRIC_KEYS, TABLE_HEADERS

# Ленивый импорт для GUI-зависимых модулей
def __getattr__(name: str):
    """Ленивый импорт GUI-компонентов."""
    
    # GUI-компоненты
    if name == "MainWindow":
        from .main_window import MainWindow
        return MainWindow
    
    # Worker и ResultRow
    if name == "Worker":
        from .worker import Worker
        return Worker
    if name == "ResultRow":
        from .worker import ResultRow
        return ResultRow
    if name == "create_default_registry":
        from .worker import create_default_registry
        return create_default_registry
    
    # Presets (требует PySide6)
    if name == "PRESET_NAMES":
        from .presets import PRESET_NAMES
        return PRESET_NAMES
    if name == "apply_preset":
        from .presets import apply_preset
        return apply_preset
    
    # Log handlers
    if name == "QtLogHandler":
        from .log_handler import QtLogHandler
        return QtLogHandler
    if name == "UiLogEmitter":
        from .log_handler import UiLogEmitter
        return UiLogEmitter
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MainWindow",
    "Worker",
    "ResultRow",
    "create_default_registry",
    "VARIANTS",
    "METRIC_KEYS",
    "TABLE_HEADERS",
    "PRESET_NAMES",
    "apply_preset",
    "QtLogHandler",
    "UiLogEmitter",
]
