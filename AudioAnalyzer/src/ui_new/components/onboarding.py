"""
OnboardingManager - система онбординга для новых пользователей.

Функционал:
- Интерактивные подсказки при первом запуске
- Туториал по основным функциям
- Подсветка элементов интерфейса
- Прогресс ознакомления

Архитектура:
============
OnboardingManager управляет процессом знакомства пользователя с приложением.
OnboardingStep представляет один шаг обучения.
OnboardingOverlay - оверлей с подсказками.

Использование:
--------------
onboarding = OnboardingManager(main_window)
onboarding.start()  # Начать онбординг
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    QTimer,
    QPoint,
    QRect,
    Signal,
    QObject,
)
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QRegion
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

logger = logging.getLogger("ui_new.components.onboarding")


# =============================================================================
# ENUMS
# =============================================================================

class OnboardingStepType(Enum):
    """Типы шагов онбординга."""
    HIGHLIGHT = "highlight"  # Подсветка элемента
    TOOLTIP = "tooltip"  # Подсказка
    DIALOG = "dialog"  # Диалоговое окно
    TOUR = "tour"  # Тур по элементам


# =============================================================================
# ONBOARDING STEP
# =============================================================================

@dataclass
class OnboardingStep:
    """Шаг онбординга.

    Attributes:
    -----------
    id : str
        Уникальный идентификатор
    title : str
        Заголовок шага
    description : str
        Описание шага
    target_selector : Optional[str]
        CSS-подобный селектор для целевого виджета
    step_type : OnboardingStepType
        Тип шага
    position : str
        Позиция подсказки относительно цели (top, bottom, left, right)
    """
    id: str
    title: str
    description: str = ""
    target_selector: Optional[str] = None
    step_type: OnboardingStepType = OnboardingStepType.HIGHLIGHT
    position: str = "bottom"
    is_completed: bool = field(default=False, init=False)


# =============================================================================
# DEFAULT ONBOARDING STEPS
# =============================================================================

DEFAULT_ONBOARDING_STEPS: List[OnboardingStep] = [
    OnboardingStep(
        id="welcome",
        title="Добро пожаловать в AudioAnalyzer!",
        description=(
            "AudioAnalyzer - это приложение для анализа и сравнения "
            "качества аудиофайлов. Давайте познакомимся с основными функциями."
        ),
        step_type=OnboardingStepType.DIALOG
    ),
    OnboardingStep(
        id="open_file",
        title="Открытие файла",
        description=(
            "Нажмите кнопку 'Выбрать .wav…' для выбора аудиофайла "
            "для анализа. Поддерживаются файлы формата WAV."
        ),
        target_selector="btn_browse",
        position="bottom"
    ),
    OnboardingStep(
        id="batch_process",
        title="Пакетная обработка",
        description=(
            "Используйте 'Выбрать папку…' для выбора папки с WAV-файлами "
            "и 'Запустить набор' для пакетной обработки всех файлов."
        ),
        target_selector="btn_batch",
        position="bottom"
    ),
    OnboardingStep(
        id="settings",
        title="Настройки методов",
        description=(
            "Во вкладке 'Настройки' вы можете настроить параметры "
            "различных методов анализа: FWHT, FFT, DCT, DWT и других."
        ),
        target_selector="tabs:settings",
        position="left"
    ),
    OnboardingStep(
        id="comparison",
        title="Сравнение результатов",
        description=(
            "Вкладка 'Сравнение' позволяет визуализировать "
            "результаты анализа с помощью графиков и тепловых карт."
        ),
        target_selector="tabs:comparison",
        position="left"
    ),
    OnboardingStep(
        id="player",
        title="Аудиоплеер",
        description=(
            "Вкладка 'Плеер' позволяет воспроизводить исходные "
            "и обработанные аудиофайлы."
        ),
        target_selector="tabs:player",
        position="left"
    ),
    OnboardingStep(
        id="spectrum",
        title="Спектральный анализ",
        description=(
            "Вкладка 'Спектр' предназначена для детального "
            "спектрального анализа аудиофайлов."
        ),
        target_selector="tabs:spectrum",
        position="left"
    ),
    OnboardingStep(
        id="export",
        title="Экспорт результатов",
        description=(
            "Используйте кнопку 'Экспорт в Excel' для сохранения "
            "результатов анализа в формате XLSX."
        ),
        target_selector="btn_export_xlsx",
        position="top"
    ),
    OnboardingStep(
        id="complete",
        title="Готово!",
        description=(
            "Теперь вы знакомы с основными функциями AudioAnalyzer. "
            "Нажмите F1 для справки в любой момент."
        ),
        step_type=OnboardingStepType.DIALOG
    ),
]


# =============================================================================
# ONBOARDING OVERLAY
# =============================================================================

class OnboardingOverlay(QWidget):
    """Оверлей для подсветки элементов и отображения подсказок.

    Особенности:
    - Полупрозрачный фон (дочерний виджет, не отдельное окно)
    - Вырезанная область для подсветки элемента
    - Подсказка с описанием

    Архитектура:
    Оверлей создаётся как дочерний виджет centralWidget главного окна.
    Это гарантирует корректное отображение на всех платформах (Linux, Windows, macOS),
    избегая проблем с WA_TranslucentBackground и отдельными окнами на X11.
    """

    next_requested = Signal()
    prev_requested = Signal()
    skip_requested = Signal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self._highlight_rect: Optional[QRect] = None
        self._current_step: Optional[OnboardingStep] = None
        self._current_index: int = 0
        self._total_steps: int = 0

        # НЕ используем FramelessWindowHint / WA_TranslucentBackground —
        # на Linux/X11 это создаёт сплошной чёрный прямоугольник.
        # Вместо этого оверлей — дочерний виджет, закрывающий parent.
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Настроить UI."""
        # Контейнер для подсказки
        self.tooltip_widget = QFrame(self)
        self.tooltip_widget.setStyleSheet("""
            QFrame {
                background-color: #1E40AF;
                border: 2px solid #3B82F6;
                border-radius: 8px;
            }
        """)

        tooltip_layout = QVBoxLayout(self.tooltip_widget)
        tooltip_layout.setContentsMargins(16, 12, 16, 12)
        tooltip_layout.setSpacing(8)

        # Заголовок
        self.title_label = QLabel()
        self.title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        tooltip_layout.addWidget(self.title_label)

        # Описание
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("""
            QLabel {
                color: #E5E7EB;
                font-size: 12px;
            }
        """)
        tooltip_layout.addWidget(self.desc_label)

        # Прогресс
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        tooltip_layout.addWidget(self.progress_label)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        self.btn_skip = QPushButton("Пропустить")
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #9CA3AF;
                border: none;
                padding: 8px;
            }
            QPushButton:hover {
                color: #E5E7EB;
            }
        """)
        self.btn_skip.clicked.connect(self.skip_requested)
        buttons_layout.addWidget(self.btn_skip)

        buttons_layout.addStretch(1)

        self.btn_prev = QPushButton("← Назад")
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #E5E7EB;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        self.btn_prev.clicked.connect(self.prev_requested)
        buttons_layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Далее →")
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        self.btn_next.clicked.connect(self.next_requested)
        buttons_layout.addWidget(self.btn_next)

        tooltip_layout.addLayout(buttons_layout)

        self.tooltip_widget.hide()

    def set_step(
        self,
        step: OnboardingStep,
        index: int,
        total: int,
        target_rect: Optional[QRect] = None
    ) -> None:
        """Установить текущий шаг.

        Параметры:
        ----------
        step : OnboardingStep
            Шаг онбординга
        index : int
            Индекс текущего шага
        total : int
            Общее количество шагов
        target_rect : Optional[QRect]
            Прямоугольник целевого элемента
        """
        self._current_step = step
        self._current_index = index
        self._total_steps = total
        self._highlight_rect = target_rect

        # Обновляем контент
        self.title_label.setText(step.title)
        self.desc_label.setText(step.description)
        self.progress_label.setText(f"Шаг {index + 1} из {total}")

        # Позиционируем подсказку
        if step.step_type == OnboardingStepType.DIALOG:
            # Центрируем диалог в пределах оверлея
            overlay_rect = self.rect()
            tooltip_width = 350
            tooltip_height = 180
            x = (overlay_rect.width() - tooltip_width) // 2
            y = (overlay_rect.height() - tooltip_height) // 2
            self.tooltip_widget.setGeometry(x, y, tooltip_width, tooltip_height)
        else:
            # Позиционируем относительно цели
            self._position_tooltip(target_rect)

        # Обновляем кнопки
        self.btn_prev.setEnabled(index > 0)
        self.btn_next.setText("Далее →" if index < total - 1 else "Завершить")

        self.tooltip_widget.show()
        self.update()

    def _position_tooltip(self, target_rect: Optional[QRect]) -> None:
        """Позиционировать подсказку относительно цели.

        Координаты target_rect уже в локальной системе координат
        центрального виджета (тот же что и оверлей).
        """
        if not target_rect or not self._current_step:
            return

        margin = 12
        tooltip_width = 300
        tooltip_height = 150

        position = self._current_step.position

        if position == "bottom":
            x = target_rect.left() + (target_rect.width() - tooltip_width) // 2
            y = target_rect.bottom() + margin
        elif position == "top":
            x = target_rect.left() + (target_rect.width() - tooltip_width) // 2
            y = target_rect.top() - tooltip_height - margin
        elif position == "left":
            x = target_rect.left() - tooltip_width - margin
            y = target_rect.top()
        elif position == "right":
            x = target_rect.right() + margin
            y = target_rect.top()
        else:
            x = target_rect.left()
            y = target_rect.bottom() + margin

        # Убеждаемся что подсказка в пределах оверлея
        overlay_rect = self.rect()
        x = max(10, min(x, overlay_rect.width() - tooltip_width - 10))
        y = max(10, min(y, overlay_rect.height() - tooltip_height - 10))

        self.tooltip_widget.setGeometry(x, y, tooltip_width, tooltip_height)

    def paintEvent(self, event) -> None:
        """Отрисовать оверлей."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Заполняем полупрозрачным фоном
        parent_rect = self.rect()
        painter.fillRect(parent_rect, QColor(0, 0, 0, 180))

        # Если есть область для подсветки - вырезаем её
        if self._highlight_rect:
            # Создаём регион с вырезом
            full_region = QRegion(parent_rect)
            highlight_region = QRegion(
                self._highlight_rect.adjusted(-8, -8, 8, 8)
            )
            final_region = full_region - highlight_region

            painter.setClipRegion(final_region)
            painter.fillRect(parent_rect, QColor(0, 0, 0, 180))

            # Рисуем рамку вокруг подсвеченной области
            painter.setClipRect(parent_rect)
            painter.setPen(QPen(QColor("#3B82F6"), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(
                self._highlight_rect.adjusted(-8, -8, 8, 8),
                8, 8
            )

    def showEvent(self, event) -> None:
        """Обработать показ.

        Оверлей — дочерний виджет, поэтому просто занимаем всю площадь parent
        и поднимаемся наверх. Не нужно mapToGlobal — координаты локальные.
        """
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
            self.raise_()
        super().showEvent(event)

    def resizeEvent(self, event) -> None:
        """Подстраиваться под размер parent при ресайзе."""
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        super().resizeEvent(event)


# =============================================================================
# ONBOARDING MANAGER
# =============================================================================

class OnboardingManager(QObject):
    """Менеджер онбординга.

    Управляет процессом знакомства пользователя с приложением.
    """

    # Сигналы
    started = Signal()
    completed = Signal()
    step_changed = Signal(int)

    # Ключ для хранения состояния
    SETTINGS_KEY = "onboarding_completed"

    def __init__(
        self,
        main_window: QMainWindow,
        config_path: Optional[Path] = None
    ):
        super().__init__(main_window)

        self._main_window = main_window
        self._config_path = config_path

        self._steps: List[OnboardingStep] = DEFAULT_ONBOARDING_STEPS.copy()
        self._current_index: int = 0

        # Оверлей создаётся на centralWidget, а не на QMainWindow.
        # Это исключает проблемы с меню-баром, статус-баром и отдельными окнами.
        central = main_window.centralWidget()
        self._overlay = OnboardingOverlay(central)
        self._overlay.next_requested.connect(self._on_next)
        self._overlay.prev_requested.connect(self._on_prev)
        self._overlay.skip_requested.connect(self._on_skip)

    def _load_state(self) -> Dict[str, Any]:
        """Загрузить состояние из файла."""
        if not self._config_path or not self._config_path.exists():
            return {}

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load onboarding state: {e}")
            return {}

    def _save_state(self, state: Dict[str, Any]) -> None:
        """Сохранить состояние в файл."""
        if not self._config_path:
            return

        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save onboarding state: {e}")

    def is_completed(self) -> bool:
        """Проверить, завершён ли онбординг.

        Returns:
        --------
        bool
            True если онбординг был завершён
        """
        state = self._load_state()
        return state.get(self.SETTINGS_KEY, False)

    def start(self, force: bool = False) -> None:
        """Начать онбординг.

        Параметры:
        ----------
        force : bool
            Запустить даже если уже был завершён
        """
        if not force and self.is_completed():
            logger.info("Onboarding already completed")
            return

        self._current_index = 0
        self._show_current_step()
        self.started.emit()

        logger.info("Onboarding started")

    def _show_current_step(self) -> None:
        """Показать текущий шаг."""
        if self._current_index >= len(self._steps):
            self._complete()
            return

        step = self._steps[self._current_index]

        # Находим целевой элемент
        target_rect = None
        if step.target_selector:
            target_rect = self._find_target_rect(step.target_selector)

        self._overlay.set_step(
            step,
            self._current_index,
            len(self._steps),
            target_rect
        )
        self._overlay.show()
        self._overlay.raise_()

        self.step_changed.emit(self._current_index)

    def _find_target_rect(self, selector: str) -> Optional[QRect]:
        """Найти прямоугольник целевого виджета по селектору.

        Параметры:
        ----------
        selector : str
            Селектор (objectName или специальный формат)

        Returns:
        --------
        Optional[QRect]
            Прямоугольник виджета в координатах centralWidget
            (совпадают с координатами оверлея)
        """
        # Специальные селекторы
        if selector.startswith("tabs:"):
            tab_name = selector.split(":")[1]
            return self._find_tab_rect(tab_name)

        # Поиск по objectName
        widget = self._main_window.findChild(QWidget, selector)
        if widget:
            # Преобразуем координаты в систему centralWidget (parent оверлея)
            central = self._main_window.centralWidget()
            if central:
                global_pos = widget.mapTo(central, QPoint(0, 0))
            else:
                global_pos = widget.mapTo(self._main_window, QPoint(0, 0))
            return QRect(global_pos, widget.size())

        return None

    def _find_tab_rect(self, tab_name: str) -> Optional[QRect]:
        """Найти прямоугольник вкладки по имени.

        Параметры:
        ----------
        tab_name : str
            Название вкладки

        Returns:
        --------
        Optional[QRect]
            Прямоугольник вкладки в координатах centralWidget
        """
        # Ищем QTabWidget
        tabs = self._main_window.findChild(QWidget, "tabs")
        if not tabs:
            return None

        # Находим tabBar
        tab_bar = None
        for child in tabs.children():
            if child.__class__.__name__ == "QTabBar":
                tab_bar = child
                break

        if not tab_bar:
            return None

        # Ищем вкладку по имени
        central = self._main_window.centralWidget()
        for i in range(tab_bar.count()):
            if tab_name.lower() in tab_bar.tabText(i).lower():
                rect = tab_bar.tabRect(i)
                if central:
                    global_pos = tab_bar.mapTo(central, rect.topLeft())
                else:
                    global_pos = tab_bar.mapTo(self._main_window, rect.topLeft())
                return QRect(global_pos, rect.size())

        return None

    def _on_next(self) -> None:
        """Перейти к следующему шагу."""
        if self._current_index < len(self._steps) - 1:
            self._current_index += 1
            self._show_current_step()
        else:
            self._complete()

    def _on_prev(self) -> None:
        """Вернуться к предыдущему шагу."""
        if self._current_index > 0:
            self._current_index -= 1
            self._show_current_step()

    def _on_skip(self) -> None:
        """Пропустить онбординг."""
        self._overlay.hide()
        self._complete()

    def _complete(self) -> None:
        """Завершить онбординг."""
        self._overlay.hide()

        # Сохраняем состояние
        state = self._load_state()
        state[self.SETTINGS_KEY] = True
        self._save_state(state)

        self.completed.emit()
        logger.info("Onboarding completed")

    def reset(self) -> None:
        """Сбросить состояние онбординга."""
        state = self._load_state()
        state[self.SETTINGS_KEY] = False
        self._save_state(state)
        logger.info("Onboarding reset")


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "OnboardingStep",
    "OnboardingStepType",
    "OnboardingOverlay",
    "OnboardingManager",
    "DEFAULT_ONBOARDING_STEPS",
]
