"""
mixins: Модуль разделения функциональности MainWindow.

Назначение:
- Разделение 2400+ строк MainWindow на логические блоки
- Упрощение тестирования и поддержки
- Консистентный интерфейс через миксины

Структура модуля:
=================
- settings_mixin.py: Панель настроек и матрица влияния (~500 строк)
- comparison_mixin.py: Графики сравнения и heatmap (~200 строк)
- player_mixin.py: Аудиоплеер (~200 строк)
- files_mixin.py: Работа с файлами (~300 строк)
- spectrum_mixin.py: Спектральный анализ (~350 строк)
- worker_mixin.py: Управление фоновой обработкой (~150 строк)

Использование:
==============
>>> from ui_new.mixins import (
...     SettingsMixin,
...     ComparisonMixin,
...     PlayerMixin,
...     FilesMixin,
...     SpectrumMixin,
...     WorkerMixin,
... )
>>>
>>> class MainWindow(
...     SettingsMixin,
...     ComparisonMixin,
...     PlayerMixin,
...     FilesMixin,
...     SpectrumMixin,
...     WorkerMixin,
...     QMainWindow
... ):
...     pass

Примечание о порядке наследования:
===================================
Миксины должны идти перед QMainWindow в порядке объявления.
Это гарантирует правильное разрешение методов (MRO).

Порядок миксинов:
1. SettingsMixin - настройки и матрица
2. ComparisonMixin - графики
3. PlayerMixin - плеер
4. FilesMixin - файлы
5. SpectrumMixin - спектр
6. WorkerMixin - обработка
7. QMainWindow - базовый класс Qt
"""
from __future__ import annotations

# =============================================================================
# ЭКСПОРТ ВСЕХ МИКСИНОВ
# =============================================================================

from .settings_mixin import SettingsMixin
from .comparison_mixin import ComparisonMixin
from .player_mixin import PlayerMixin
from .files_mixin import FilesMixin
from .spectrum_mixin import SpectrumMixin
from .worker_mixin import WorkerMixin


# =============================================================================
# ЭКСПОРТ КОНСТАНТ
# =============================================================================

from .settings_mixin import (
    METHOD_HEADERS,
    METRICS_COLS,
    PARAMS_ROWS,
)


# =============================================================================
# ПУБЛИЧНЫЙ API
# =============================================================================

__all__ = [
    # Миксины
    "SettingsMixin",
    "ComparisonMixin",
    "PlayerMixin",
    "FilesMixin",
    "SpectrumMixin",
    "WorkerMixin",
    # Константы
    "METHOD_HEADERS",
    "METRICS_COLS",
    "PARAMS_ROWS",
]
