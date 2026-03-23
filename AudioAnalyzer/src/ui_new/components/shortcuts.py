"""
ShortcutManager - система управления горячими клавишами.

Функционал:
- Централизованное управление горячими клавишами
- Стандартные комбинации для основных операций
- Настраиваемые пользователем сочетания
- Отображение подсказок в меню и tooltip

Архитектура:
============
ShortcutManager управляет всеми горячими клавишами приложения.
ShortcutAction представляет одно действие с его комбинацией клавиш.

Стандартные комбинации:
- Ctrl+O: Открыть файл
- Ctrl+S: Сохранить результаты
- Ctrl+P: Переключить профиль
- F5: Запустить анализ
- Ctrl+B: Пакетная обработка
- Ctrl+E: Экспорт в Excel
- Ctrl+,: Настройки
- F1: Справка
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QAction
from PySide6.QtWidgets import QWidget, QMainWindow

logger = logging.getLogger("ui_new.components.shortcuts")


# =============================================================================
# ENUMS
# =============================================================================

class ShortcutCategory(Enum):
    """Категории горячих клавиш."""
    FILE = "Файл"
    EDIT = "Редактирование"
    ANALYSIS = "Анализ"
    VIEW = "Вид"
    HELP = "Справка"


# =============================================================================
# SHORTCUT ACTION
# =============================================================================

@dataclass
class ShortcutAction:
    """Действие с горячей клавишей.

    Attributes:
    -----------
    id : str
        Уникальный идентификатор действия
    name : str
        Отображаемое название
    default_key : str
        Комбинация клавиш по умолчанию (нотация Qt)
    description : str
        Описание действия
    category : ShortcutCategory
        Категория для группировки
    callback : Optional[Callable]
        Функция обратного вызова
    """
    id: str
    name: str
    default_key: str
    description: str = ""
    category: ShortcutCategory = ShortcutCategory.FILE
    callback: Optional[Callable[[], None]] = None
    current_key: str = field(default="", init=False)

    def __post_init__(self):
        if not self.current_key:
            self.current_key = self.default_key

    @property
    def key_sequence(self) -> QKeySequence:
        """Получить QKeySequence для текущей комбинации."""
        return QKeySequence(self.current_key)

    @property
    def display_text(self) -> str:
        """Получить текст для отображения в UI."""
        return QKeySequence(self.current_key).toString(QKeySequence.PortableText)

    def reset_to_default(self) -> None:
        """Сбросить к значению по умолчанию."""
        self.current_key = self.default_key


# =============================================================================
# SHORTCUT MANAGER
# =============================================================================

class ShortcutManager(QObject):
    """Менеджер горячих клавиш.

    Управляет регистрацией, изменением и сохранением горячих клавиш.
    """

    # Сигналы
    shortcut_triggered = Signal(str)  # id действия
    shortcuts_changed = Signal()

    # Стандартные действия
    DEFAULT_ACTIONS: List[ShortcutAction] = [
        # Файл
        ShortcutAction(
            id="file.open",
            name="Открыть файл",
            default_key="Ctrl+O",
            description="Открыть WAV файл для анализа",
            category=ShortcutCategory.FILE
        ),
        ShortcutAction(
            id="file.save",
            name="Сохранить результаты",
            default_key="Ctrl+S",
            description="Сохранить результаты анализа",
            category=ShortcutCategory.FILE
        ),
        ShortcutAction(
            id="file.export_xlsx",
            name="Экспорт в Excel",
            default_key="Ctrl+E",
            description="Экспортировать результаты в XLSX",
            category=ShortcutCategory.FILE
        ),
        ShortcutAction(
            id="file.batch",
            name="Пакетная обработка",
            default_key="Ctrl+B",
            description="Запустить пакетную обработку",
            category=ShortcutCategory.FILE
        ),
        # Анализ
        ShortcutAction(
            id="analysis.run",
            name="Запустить анализ",
            default_key="F5",
            description="Запустить анализ текущего файла",
            category=ShortcutCategory.ANALYSIS
        ),
        ShortcutAction(
            id="analysis.compare",
            name="Сравнить файлы",
            default_key="Ctrl+Shift+C",
            description="Открыть диалог сравнения файлов",
            category=ShortcutCategory.ANALYSIS
        ),
        ShortcutAction(
            id="analysis.spectrum",
            name="Спектральный анализ",
            default_key="Ctrl+Shift+S",
            description="Переключиться на вкладку спектра",
            category=ShortcutCategory.ANALYSIS
        ),
        # Вид
        ShortcutAction(
            id="view.dashboard",
            name="Панель управления",
            default_key="Ctrl+D",
            description="Переключиться на Dashboard",
            category=ShortcutCategory.VIEW
        ),
        ShortcutAction(
            id="view.table",
            name="Таблица результатов",
            default_key="Ctrl+T",
            description="Переключиться на вкладку таблицы",
            category=ShortcutCategory.VIEW
        ),
        ShortcutAction(
            id="view.comparison",
            name="Графики сравнения",
            default_key="Ctrl+G",
            description="Переключиться на вкладку сравнения",
            category=ShortcutCategory.VIEW
        ),
        ShortcutAction(
            id="view.settings",
            name="Настройки",
            default_key="Ctrl+,",
            description="Открыть вкладку настроек",
            category=ShortcutCategory.VIEW
        ),
        ShortcutAction(
            id="view.logs",
            name="Показать/скрыть логи",
            default_key="Ctrl+L",
            description="Переключить видимость панели логов",
            category=ShortcutCategory.VIEW
        ),
        # Профиль
        ShortcutAction(
            id="profile.switch",
            name="Переключить профиль",
            default_key="Ctrl+P",
            description="Переключить пресет настроек",
            category=ShortcutCategory.EDIT
        ),
        ShortcutAction(
            id="profile.next",
            name="Следующий профиль",
            default_key="Ctrl+Right",
            description="Переключиться на следующий профиль",
            category=ShortcutCategory.EDIT
        ),
        ShortcutAction(
            id="profile.prev",
            name="Предыдущий профиль",
            default_key="Ctrl+Left",
            description="Переключиться на предыдущий профиль",
            category=ShortcutCategory.EDIT
        ),
        # Справка
        ShortcutAction(
            id="help.about",
            name="О программе",
            default_key="F1",
            description="Показать информацию о программе",
            category=ShortcutCategory.HELP
        ),
        ShortcutAction(
            id="help.shortcuts",
            name="Горячие клавиши",
            default_key="Ctrl+/",
            description="Показать список горячих клавиш",
            category=ShortcutCategory.HELP
        ),
    ]

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._actions: Dict[str, ShortcutAction] = {}
        self._shortcuts: Dict[str, QShortcut] = {}
        self._callbacks: Dict[str, Callable[[], None]] = {}
        self._config_path: Optional[Path] = None

        # Инициализируем стандартные действия
        for action in self.DEFAULT_ACTIONS:
            self._actions[action.id] = ShortcutAction(
                id=action.id,
                name=action.name,
                default_key=action.default_key,
                description=action.description,
                category=action.category
            )

    def set_config_path(self, path: Path) -> None:
        """Установить путь к файлу конфигурации.

        Параметры:
        ----------
        path : Path
            Путь к файлу JSON с настройками
        """
        self._config_path = path
        self._load_config()

    def _load_config(self) -> None:
        """Загрузить конфигурацию из файла."""
        if not self._config_path or not self._config_path.exists():
            return

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            shortcuts_config = config.get('shortcuts', {})
            for action_id, key_sequence in shortcuts_config.items():
                if action_id in self._actions:
                    self._actions[action_id].current_key = key_sequence

            logger.info(f"Loaded shortcuts config from {self._config_path}")

        except Exception as e:
            logger.error(f"Failed to load shortcuts config: {e}")

    def _save_config(self) -> None:
        """Сохранить конфигурацию в файл."""
        if not self._config_path:
            return

        try:
            config = {'shortcuts': {}}
            for action_id, action in self._actions.items():
                if action.current_key != action.default_key:
                    config['shortcuts'][action_id] = action.current_key

            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved shortcuts config to {self._config_path}")

        except Exception as e:
            logger.error(f"Failed to save shortcuts config: {e}")

    def register(
        self,
        parent: QWidget,
        action_id: str,
        callback: Callable[[], None]
    ) -> Optional[QShortcut]:
        """Зарегистрировать обработчик для действия.

        Параметры:
        ----------
        parent : QWidget
            Родительский виджет
        action_id : str
            Идентификатор действия
        callback : Callable
            Функция обратного вызова

        Returns:
        --------
        Optional[QShortcut]
            Созданный QShortcut или None
        """
        if action_id not in self._actions:
            logger.warning(f"Unknown action ID: {action_id}")
            return None

        action = self._actions[action_id]
        self._callbacks[action_id] = callback

        # Удаляем старый shortcut если есть
        if action_id in self._shortcuts:
            old_shortcut = self._shortcuts.pop(action_id)
            old_shortcut.setEnabled(False)
            old_shortcut.deleteLater()

        # Создаём новый
        shortcut = QShortcut(action.key_sequence, parent)
        shortcut.activated.connect(lambda: self._on_activated(action_id))
        self._shortcuts[action_id] = shortcut

        logger.debug(f"Registered shortcut: {action_id} -> {action.current_key}")
        return shortcut

    def register_all(self, parent: QWidget) -> None:
        """Зарегистрировать все действия с пустыми обработчиками.

        Параметры:
        ----------
        parent : QWidget
            Родительский виджет
        """
        for action_id in self._actions:
            if action_id not in self._shortcuts:
                self.register(parent, action_id, lambda: None)

    def _on_activated(self, action_id: str) -> None:
        """Обработать активацию shortcut."""
        logger.debug(f"Shortcut activated: {action_id}")
        self.shortcut_triggered.emit(action_id)

        if action_id in self._callbacks:
            try:
                self._callbacks[action_id]()
            except Exception as e:
                logger.error(f"Error in shortcut callback for {action_id}: {e}")

    def get_action(self, action_id: str) -> Optional[ShortcutAction]:
        """Получить действие по ID.

        Параметры:
        ----------
        action_id : str
            Идентификатор действия

        Returns:
        --------
        Optional[ShortcutAction]
            Действие или None
        """
        return self._actions.get(action_id)

    def get_all_actions(self) -> List[ShortcutAction]:
        """Получить все действия.

        Returns:
        --------
        List[ShortcutAction]
            Список всех действий
        """
        return list(self._actions.values())

    def get_actions_by_category(self, category: ShortcutCategory) -> List[ShortcutAction]:
        """Получить действия по категории.

        Параметры:
        ----------
        category : ShortcutCategory
            Категория действий

        Returns:
        --------
        List[ShortcutAction]
            Список действий в категории
        """
        return [a for a in self._actions.values() if a.category == category]

    def set_key(self, action_id: str, key_sequence: str) -> bool:
        """Установить новую комбинацию клавиш.

        Параметры:
        ----------
        action_id : str
            Идентификатор действия
        key_sequence : str
            Новая комбинация (нотация Qt)

        Returns:
        --------
        bool
            True если успешно
        """
        if action_id not in self._actions:
            return False

        # Проверяем на конфликт
        for other_id, other_action in self._actions.items():
            if other_id != action_id and other_action.current_key == key_sequence:
                logger.warning(f"Key conflict: {key_sequence} already used by {other_id}")
                return False

        action = self._actions[action_id]
        old_key = action.current_key
        action.current_key = key_sequence

        # Обновляем shortcut если зарегистрирован
        if action_id in self._shortcuts:
            self._shortcuts[action_id].setKey(action.key_sequence)

        self._save_config()
        self.shortcuts_changed.emit()

        logger.info(f"Changed shortcut: {action_id} from {old_key} to {key_sequence}")
        return True

    def reset_all(self) -> None:
        """Сбросить все горячие клавиши к значениям по умолчанию."""
        for action in self._actions.values():
            action.reset_to_default()

            # Обновляем shortcut если зарегистрирован
            if action.id in self._shortcuts:
                self._shortcuts[action.id].setKey(action.key_sequence)

        self._save_config()
        self.shortcuts_changed.emit()

        logger.info("Reset all shortcuts to defaults")

    def apply_to_menu(self, menu_bar: Any) -> None:
        """Применить горячие клавиши к пунктам меню.

        Параметры:
        ----------
        menu_bar : QMenuBar
            Панель меню для применения shortcut'ов
        """
        for action_id, action in self._actions.items():
            # Ищем QAction по objectName
            menu_action = menu_bar.findChild(QAction, action_id)
            if menu_action:
                menu_action.setShortcut(action.key_sequence)
                menu_action.setToolTip(f"{action.description} ({action.display_text})")


# =============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# =============================================================================

_instance: Optional[ShortcutManager] = None


def get_shortcut_manager() -> ShortcutManager:
    """Получить глобальный экземпляр ShortcutManager.

    Returns:
    --------
    ShortcutManager
        Глобальный менеджер горячих клавиш
    """
    global _instance
    if _instance is None:
        _instance = ShortcutManager()
    return _instance


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "ShortcutAction",
    "ShortcutManager",
    "ShortcutCategory",
    "get_shortcut_manager",
]
