"""
Toast-уведомления для AudioAnalyzer.

Функционал:
- Анимированные всплывающие уведомления
- Категории: info, success, warning, error
- Настраиваемое время отображения
- Очередь уведомлений

Архитектура:
============
ToastManager управляет отображением toast-уведомлений.
ToastWidget представляет одно уведомление.

Использование:
--------------
toast_manager = ToastManager(main_window)
toast_manager.show_info("Файл загружен успешно")
toast_manager.show_success("Анализ завершён")
toast_manager.show_error("Ошибка: файл не найден")
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import List, Optional, Tuple
from weakref import WeakSet

from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    QTimer,
    QPoint,
    QSize,
    Property,
    Signal,
    QObject,
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger("ui_new.components.toast")


# =============================================================================
# ENUMS
# =============================================================================

class ToastType(Enum):
    """Типы toast-уведомлений."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class ToastPosition(Enum):
    """Позиция отображения toast."""
    TOP_RIGHT = "top_right"
    TOP_LEFT = "top_left"
    BOTTOM_RIGHT = "bottom_right"
    BOTTOM_LEFT = "bottom_left"
    TOP_CENTER = "top_center"
    BOTTOM_CENTER = "bottom_center"


# =============================================================================
# STYLE CONFIG
# =============================================================================

TOAST_STYLES = {
    ToastType.INFO: {
        "bg_color": "#1E40AF",
        "border_color": "#3B82F6",
        "icon": "ℹ️",
        "text_color": "#FFFFFF"
    },
    ToastType.SUCCESS: {
        "bg_color": "#166534",
        "border_color": "#22C55E",
        "icon": "✅",
        "text_color": "#FFFFFF"
    },
    ToastType.WARNING: {
        "bg_color": "#854D0E",
        "border_color": "#EAB308",
        "icon": "⚠️",
        "text_color": "#FFFFFF"
    },
    ToastType.ERROR: {
        "bg_color": "#991B1B",
        "border_color": "#EF4444",
        "icon": "❌",
        "text_color": "#FFFFFF"
    },
}


# =============================================================================
# TOAST WIDGET
# =============================================================================

class ToastWidget(QFrame):
    """Виджет одного toast-уведомления.

    Features:
    - Анимация появления/исчезновения
    - Автоматическое скрытие по таймеру
    - Кнопка закрытия
    - Прогресс-бар оставшегося времени
    """

    closed = Signal()

    def __init__(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration: int = 4000,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._message = message
        self._toast_type = toast_type
        self._duration = duration
        self._opacity = 0.0

        self._setup_ui()
        self._setup_animations()
        self._start_timer()

        # Фиксированный размер
        self.setFixedWidth(320)
        self.setMinimumHeight(60)

    def _setup_ui(self) -> None:
        """Построить UI."""
        style = TOAST_STYLES[self._toast_type]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 12, 12)
        layout.setSpacing(12)

        # Иконка
        icon_label = QLabel(style["icon"])
        icon_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(icon_label)

        # Текст
        self.message_label = QLabel(self._message)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(f"""
            QLabel {{
                color: {style['text_color']};
                font-size: 13px;
                background: transparent;
            }}
        """)
        layout.addWidget(self.message_label, 1)

        # Кнопка закрытия
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {style['text_color']};
                border: none;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.2);
                border-radius: 12px;
            }}
        """)
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn)

        # Стили виджета
        self.setStyleSheet(f"""
            ToastWidget {{
                background-color: {style['bg_color']};
                border: 2px solid {style['border_color']};
                border-radius: 8px;
            }}
        """)

        # Эффект прозрачности
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)

    def _setup_animations(self) -> None:
        """Настроить анимации."""
        # Анимация появления
        self._show_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._show_anim.setDuration(200)
        self._show_anim.setStartValue(0.0)
        self._show_anim.setEndValue(1.0)
        self._show_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Анимация исчезновения
        self._hide_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._hide_anim.setDuration(200)
        self._hide_anim.setStartValue(1.0)
        self._hide_anim.setEndValue(0.0)
        self._hide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._hide_anim.finished.connect(self._on_hide_finished)

    def _start_timer(self) -> None:
        """Запустить таймер автоскрытия."""
        if self._duration > 0:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self._on_auto_hide)
            self._timer.start(self._duration)

    def show_toast(self) -> None:
        """Показать уведомление."""
        self.show()
        self._show_anim.start()

    def hide_toast(self) -> None:
        """Скрыть уведомление с анимацией."""
        self._hide_anim.start()

    def _on_auto_hide(self) -> None:
        """Автоматическое скрытие."""
        self.hide_toast()

    def _on_close(self) -> None:
        """Закрыть по кнопке."""
        if hasattr(self, '_timer'):
            self._timer.stop()
        self.hide_toast()

    def _on_hide_finished(self) -> None:
        """Завершение анимации скрытия."""
        self.hide()
        self.closed.emit()

    def enterEvent(self, event) -> None:
        """При наведении мыши - остановить таймер."""
        if hasattr(self, '_timer'):
            self._timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """При уходе мыши - перезапустить таймер."""
        if hasattr(self, '_timer') and self._duration > 0:
            self._timer.start(2000)  # Осталось 2 секунды
        super().leaveEvent(event)


# =============================================================================
# TOAST MANAGER
# =============================================================================

class ToastManager(QObject):
    """Менеджер toast-уведомлений.

    Управляет очередью и позиционированием уведомлений.
    """

    def __init__(
        self,
        parent: QWidget,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        max_visible: int = 5,
        spacing: int = 8
    ):
        super().__init__(parent)

        self._parent = parent
        self._position = position
        self._max_visible = max_visible
        self._spacing = spacing

        self._active_toasts: List[ToastWidget] = []
        self._queue: List[Tuple[str, ToastType, int]] = []

    def _calculate_position(self, index: int) -> QPoint:
        """Рассчитать позицию для toast по индексу.

        Параметры:
        ----------
        index : int
            Индекс toast в списке активных

        Returns:
        --------
        QPoint
            Координаты позиции
        """
        parent_rect = self._parent.rect()
        margin = 16

        # Суммарная высота предыдущих toast'ов
        y_offset = margin
        for i in range(index):
            if i < len(self._active_toasts):
                y_offset += self._active_toasts[i].height() + self._spacing

        if self._position == ToastPosition.TOP_RIGHT:
            x = parent_rect.width() - 320 - margin
            y = y_offset
        elif self._position == ToastPosition.TOP_LEFT:
            x = margin
            y = y_offset
        elif self._position == ToastPosition.BOTTOM_RIGHT:
            x = parent_rect.width() - 320 - margin
            y = parent_rect.height() - y_offset - 60
        elif self._position == ToastPosition.BOTTOM_LEFT:
            x = margin
            y = parent_rect.height() - y_offset - 60
        elif self._position == ToastPosition.TOP_CENTER:
            x = (parent_rect.width() - 320) // 2
            y = y_offset
        else:  # BOTTOM_CENTER
            x = (parent_rect.width() - 320) // 2
            y = parent_rect.height() - y_offset - 60

        return QPoint(x, y)

    def _reposition_toasts(self) -> None:
        """Пересчитать позиции всех активных toast'ов."""
        for i, toast in enumerate(self._active_toasts):
            pos = self._calculate_position(i)
            # Анимация перемещения
            toast.move(pos)

    def _show_next(self) -> None:
        """Показать следующее уведомление из очереди."""
        if not self._queue:
            return

        if len(self._active_toasts) >= self._max_visible:
            return

        message, toast_type, duration = self._queue.pop(0)
        self._show_toast(message, toast_type, duration)

    def _show_toast(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration: int = 4000
    ) -> None:
        """Показать toast-уведомление.

        Параметры:
        ----------
        message : str
            Текст уведомления
        toast_type : ToastType
            Тип уведомления
        duration : int
            Время отображения в мс
        """
        toast = ToastWidget(message, toast_type, duration, self._parent)
        toast.closed.connect(lambda: self._on_toast_closed(toast))

        self._active_toasts.append(toast)
        self._reposition_toasts()
        toast.show_toast()

    def _on_toast_closed(self, toast: ToastWidget) -> None:
        """Обработать закрытие toast."""
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)
            toast.deleteLater()

        self._reposition_toasts()
        self._show_next()

    # =========================================================================
    # ПУБЛИЧНЫЕ МЕТОДЫ
    # =========================================================================

    def show(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration: int = 4000
    ) -> None:
        """Показать уведомление.

        Параметры:
        ----------
        message : str
            Текст уведомления
        toast_type : ToastType
            Тип уведомления (info, success, warning, error)
        duration : int
            Время отображения в миллисекундах (0 = не скрывать автоматически)
        """
        if len(self._active_toasts) >= self._max_visible:
            self._queue.append((message, toast_type, duration))
        else:
            self._show_toast(message, toast_type, duration)

    def show_info(self, message: str, duration: int = 4000) -> None:
        """Показать информационное уведомление."""
        self.show(message, ToastType.INFO, duration)

    def show_success(self, message: str, duration: int = 4000) -> None:
        """Показать уведомление об успехе."""
        self.show(message, ToastType.SUCCESS, duration)

    def show_warning(self, message: str, duration: int = 5000) -> None:
        """Показать предупреждение."""
        self.show(message, ToastType.WARNING, duration)

    def show_error(self, message: str, duration: int = 6000) -> None:
        """Показать уведомление об ошибке."""
        self.show(message, ToastType.ERROR, duration)

    def clear_all(self) -> None:
        """Скрыть все уведомления."""
        for toast in self._active_toasts[:]:
            toast.hide_toast()
        self._queue.clear()


# =============================================================================
# УДОБНЫЕ ФУНКЦИИ
# =============================================================================

def show_toast(
    parent: QWidget,
    message: str,
    toast_type: ToastType = ToastType.INFO,
    duration: int = 4000
) -> ToastWidget:
    """Быстро показать toast без создания менеджера.

    Параметры:
    ----------
    parent : QWidget
        Родительский виджет
    message : str
        Текст уведомления
    toast_type : ToastType
        Тип уведомления
    duration : int
        Время отображения

    Returns:
    --------
    ToastWidget
        Созданный виджет уведомления
    """
    toast = ToastWidget(message, toast_type, duration, parent)
    # Позиционируем в правом верхнем углу
    parent_rect = parent.rect()
    toast.move(parent_rect.width() - 320 - 16, 16)
    toast.show_toast()
    return toast


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "ToastType",
    "ToastPosition",
    "ToastWidget",
    "ToastManager",
    "show_toast",
]
