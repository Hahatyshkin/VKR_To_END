"""
Анимации и micro-interactions для AudioAnalyzer.

Назначение:
- Анимированные карточки с hover-эффектами
- Skeleton loaders для состояний загрузки
- Плавные переходы между состояниями
- Pulse-анимации для индикаторов

Использование:
------------
from ui_new.animations import AnimatedCard, SkeletonLoader, FadeWidget

# Анимированная карточка
card = AnimatedCard(title="Анализ", parent=self)

# Skeleton loader
skeleton = SkeletonLoader(parent=self)
skeleton.start()

# Плавное появление
fade_widget = FadeWidget(widget)
fade_widget.fade_in()
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    QTimer,
    QSequentialAnimationGroup,
    QParallelAnimationGroup,
    Property,
    Signal,
    QObject,
    Qt,
    QRectF,
)
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QLinearGradient
from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QGraphicsOpacityEffect,
    QApplication,
)

from .design_system import DesignSystem, Animation

logger = logging.getLogger("ui_new.animations")


# =============================================================================
# SKELETON LOADER
# =============================================================================

class SkeletonWidget(QWidget):
    """Виджет skeleton-заглушки с shimmer эффектом.
    
    Отображает анимированную заглушку для индикации загрузки данных.
    Использует shimmer-эффект для визуальной обратной связи.
    
    Параметры:
    ----------
    width : int
        Ширина заглушки
    height : int
        Высота заглушки
    radius : int
        Радиус скругления углов
    """
    
    def __init__(
        self,
        width: int = 100,
        height: int = 20,
        radius: int = 4,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._width = width
        self._height = height
        self._radius = radius
        self._shimmer_offset = 0.0
        self._animation: Optional[QPropertyAnimation] = None
        
        self.setFixedSize(width, height)
        self._start_shimmer()
    
    def get_shimmer_offset(self) -> float:
        """Получить смещение shimmer эффекта."""
        return self._shimmer_offset
    
    def set_shimmer_offset(self, value: float) -> None:
        """Установить смещение shimmer эффекта."""
        self._shimmer_offset = value
        self.update()
    
    shimmer_offset = Property(float, get_shimmer_offset, set_shimmer_offset)
    
    def _start_shimmer(self) -> None:
        """Запустить shimmer анимацию."""
        self._animation = QPropertyAnimation(self, b"shimmer_offset")
        self._animation.setDuration(1500)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setLoopCount(-1)  # Бесконечный цикл
        self._animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._animation.start()
    
    def stop_shimmer(self) -> None:
        """Остановить shimmer анимацию."""
        if self._animation:
            self._animation.stop()
            self._animation.deleteLater()
            self._animation = None
    
    def paintEvent(self, event) -> None:
        """Отрисовка skeleton с shimmer эффектом."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Фон skeleton
        bg_color = QColor(DesignSystem.colors.surface_2)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self._width, self._height, self._radius, self._radius)
        
        # Shimmer градиент
        shimmer_width = self._width * 0.3
        x_offset = -shimmer_width + self._shimmer_offset * (self._width + shimmer_width * 2)
        
        gradient = QLinearGradient(x_offset, 0, x_offset + shimmer_width, 0)
        shimmer_color = QColor(255, 255, 255, 30)  # Полупрозрачный белый
        gradient.setColorAt(0, QColor(255, 255, 255, 0))
        gradient.setColorAt(0.5, shimmer_color)
        gradient.setColorAt(1, QColor(255, 255, 255, 0))
        
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(0, 0, self._width, self._height, self._radius, self._radius)
    
    def cleanup(self) -> None:
        """Очистка ресурсов."""
        self.stop_shimmer()


class SkeletonLoader(QFrame):
    """Композитный skeleton loader для карточек.
    
    Создаёт набор skeleton-элементов для имитации структуры
    загружаемого контента.
    
    Параметры:
    ----------
    lines : int
        Количество строк текста
    show_avatar : bool
        Показывать ли круглый аватар
    show_image : bool
        Показывать ли прямоугольное изображение
    parent : QWidget
        Родительский виджет
    
    Сигналы:
    --------
    animation_finished() - анимация завершена (для однократного режима)
    """
    
    animation_finished = Signal()
    
    def __init__(
        self,
        lines: int = 3,
        show_avatar: bool = False,
        show_image: bool = False,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._skeletons: List[SkeletonWidget] = []
        self._loop_count = -1  # Бесконечный цикл по умолчанию
        
        self._setup_ui(lines, show_avatar, show_image)
        self._apply_style()
    
    def _setup_ui(self, lines: int, show_avatar: bool, show_image: bool) -> None:
        """Настройка UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Верхняя строка (avatar + title)
        if show_avatar:
            header_layout = QHBoxLayout()
            header_layout.setSpacing(12)
            
            # Avatar skeleton (круглый)
            avatar = SkeletonWidget(40, 40, 20, self)
            self._skeletons.append(avatar)
            header_layout.addWidget(avatar)
            
            # Title skeletons
            title_v_layout = QVBoxLayout()
            title_v_layout.setSpacing(8)
            
            title1 = SkeletonWidget(150, 16, 4, self)
            title2 = SkeletonWidget(100, 12, 4, self)
            self._skeletons.extend([title1, title2])
            title_v_layout.addWidget(title1)
            title_v_layout.addWidget(title2)
            
            header_layout.addLayout(title_v_layout)
            header_layout.addStretch()
            
            layout.addLayout(header_layout)
        
        # Image skeleton
        if show_image:
            image = SkeletonWidget(280, 160, 8, self)
            self._skeletons.append(image)
            layout.addWidget(image)
        
        # Text lines
        for i in range(lines):
            width = 250 if i < lines - 1 else 150  # Последняя строка короче
            line = SkeletonWidget(width, 12, 4, self)
            self._skeletons.append(line)
            layout.addWidget(line)
        
        layout.addStretch()
    
    def _apply_style(self) -> None:
        """Применение стилей."""
        self.setStyleSheet(f"""
            SkeletonLoader {{
                background-color: {DesignSystem.colors.surface_1};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 12px;
            }}
        """)
    
    def start(self) -> None:
        """Запустить все shimmer анимации."""
        for skeleton in self._skeletons:
            skeleton._start_shimmer()
    
    def stop(self) -> None:
        """Остановить все shimmer анимации."""
        for skeleton in self._skeletons:
            skeleton.stop_shimmer()
    
    def cleanup(self) -> None:
        """Очистка ресурсов."""
        self.stop()
        for skeleton in self._skeletons:
            skeleton.cleanup()
        self._skeletons.clear()


# =============================================================================
# ANIMATED CARD
# =============================================================================

class AnimatedCard(QFrame):
    """Анимированная карточка с hover-эффектами.
    
    Поддерживает:
    - Плавное появление (fade-in)
    - Hover-эффекты (подъём, тень, граница)
    - Click-анимации
    
    Параметры:
    ----------
    title : str
        Заголовок карточки
    subtitle : str
        Подзаголовок
    elevated : bool
        Начальная тень
    animated : bool
        Анимация появления
    
    Сигналы:
    --------
    clicked() - карточка нажата
    hovered(bool) - наведение курсора (enter/leave)
    """
    
    clicked = Signal()
    hovered = Signal(bool)
    
    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        elevated: bool = True,
        animated: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._title = title
        self._subtitle = subtitle
        self._elevated = elevated
        self._hover = False
        self._opacity = 0.0 if animated else 1.0
        
        # Анимации
        self._fade_animation: Optional[QPropertyAnimation] = None
        self._hover_animation: Optional[QPropertyAnimation] = None
        self._opacity_effect: Optional[QGraphicsOpacityEffect] = None
        
        self._setup_ui()
        self._apply_style()
        
        if animated:
            self._setup_opacity_effect()
            QTimer.singleShot(50, self._animate_in)
    
    def _setup_ui(self) -> None:
        """Настройка UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        # Заголовок
        if self._title:
            title_label = QLabel(self._title)
            title_label.setObjectName("cardTitle")
            title_label.setStyleSheet(f"""
                QLabel#cardTitle {{
                    font-size: {DesignSystem.typography.h3_size}px;
                    font-weight: {DesignSystem.typography.h3_weight};
                    color: {DesignSystem.colors.text_primary};
                    background: transparent;
                }}
            """)
            layout.addWidget(title_label)
        
        # Подзаголовок
        if self._subtitle:
            subtitle_label = QLabel(self._subtitle)
            subtitle_label.setObjectName("cardSubtitle")
            subtitle_label.setStyleSheet(f"""
                QLabel#cardSubtitle {{
                    font-size: {DesignSystem.typography.body_sm_size}px;
                    color: {DesignSystem.colors.text_muted};
                    background: transparent;
                }}
            """)
            layout.addWidget(subtitle_label)
    
    def _apply_style(self) -> None:
        """Применение стилей."""
        shadow = DesignSystem.shadows.md if self._elevated else DesignSystem.shadows.none
        self.setStyleSheet(f"""
            AnimatedCard {{
                background: {DesignSystem.get_gradient_css('card')};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 12px;
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _setup_opacity_effect(self) -> None:
        """Настройка эффекта прозрачности."""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
    
    def _animate_in(self) -> None:
        """Анимация появления."""
        if not self._opacity_effect:
            return
        
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(Animation.duration_normal)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(Animation.easing_default)
        self._fade_animation.start()
    
    def fade_out(self, callback: Optional[Callable] = None) -> None:
        """Анимация исчезновения.
        
        Параметры:
        ----------
        callback : Callable, optional
            Функция для вызова после завершения анимации
        """
        if not self._opacity_effect:
            if callback:
                callback()
            return
        
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(Animation.duration_fast)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(Animation.easing_default)
        
        if callback:
            self._fade_animation.finished.connect(callback)
        
        self._fade_animation.start()
    
    def enterEvent(self, event) -> None:
        """Обработка наведения курсора."""
        self._hover = True
        self.hovered.emit(True)
        
        # Анимация границы
        self.setStyleSheet(f"""
            AnimatedCard {{
                background: {DesignSystem.get_gradient_css('card')};
                border: 2px solid {DesignSystem.colors.primary};
                border-radius: 12px;
            }}
        """)
        
        super().enterEvent(event)
    
    def leaveEvent(self, event) -> None:
        """Обработка ухода курсора."""
        self._hover = False
        self.hovered.emit(False)
        
        # Возврат к обычному стилю
        self._apply_style()
        
        super().leaveEvent(event)
    
    def mousePressEvent(self, event) -> None:
        """Обработка нажатия."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        
        super().mousePressEvent(event)


# =============================================================================
# FADE WIDGET WRAPPER
# =============================================================================

class FadeWidget(QObject):
    """Обёртка для анимации прозрачности любого виджета.
    
    Позволяет добавлять fade-in/fade-out эффекты к существующим виджетам.
    
    Параметры:
    ----------
    widget : QWidget
        Виджет для анимации
    duration : int
        Длительность анимации в мс
    
    Сигналы:
    --------
    finished() - анимация завершена
    """
    
    finished = Signal()
    
    def __init__(self, widget: QWidget, duration: int = Animation.duration_normal):
        super().__init__(widget.parent())
        
        self._widget = widget
        self._duration = duration
        self._opacity_effect = QGraphicsOpacityEffect(widget)
        self._animation: Optional[QPropertyAnimation] = None
        
        widget.setGraphicsEffect(self._opacity_effect)
    
    def fade_in(self, callback: Optional[Callable] = None) -> None:
        """Плавное появление."""
        self._animate(0.0, 1.0, callback)
    
    def fade_out(self, callback: Optional[Callable] = None) -> None:
        """Плавное исчезновение."""
        self._animate(1.0, 0.0, callback)
    
    def _animate(self, start: float, end: float, callback: Optional[Callable]) -> None:
        """Запуск анимации."""
        if self._animation:
            self._animation.stop()
            # Отключаем предыдущие соединения
            try:
                self._animation.finished.disconnect()
            except RuntimeError:
                pass  # Нет соединений
        
        self._animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._animation.setDuration(self._duration)
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.setEasingCurve(Animation.easing_default)
        
        if callback:
            self._animation.finished.connect(callback)
        
        self._animation.finished.connect(self.finished.emit)
        self._animation.start()


# =============================================================================
# PULSE ANIMATION
# =============================================================================

class PulseWidget(QWidget):
    """Виджет с пульсирующей анимацией.
    
    Используется для индикаторов состояния, прогресса,
    уведомлений о событиях.
    
    Параметры:
    ----------
    color : str
        Цвет пульсации (hex)
    size : int
        Размер виджета
    parent : QWidget
        Родительский виджет
    """
    
    def __init__(
        self,
        color: str = DesignSystem.colors.primary,
        size: int = 12,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._color = QColor(color)
        self._size = size
        self._pulse_value = 0.0
        self._animation: Optional[QPropertyAnimation] = None
        
        self.setFixedSize(size, size)
        self._start_pulse()
    
    def get_pulse_value(self) -> float:
        """Получить значение пульсации."""
        return self._pulse_value
    
    def set_pulse_value(self, value: float) -> None:
        """Установить значение пульсации."""
        self._pulse_value = value
        self.update()
    
    pulse_value = Property(float, get_pulse_value, set_pulse_value)
    
    def _start_pulse(self) -> None:
        """Запустить пульсацию."""
        self._animation = QPropertyAnimation(self, b"pulse_value")
        self._animation.setDuration(1000)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setLoopCount(-1)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._animation.start()
    
    def stop_pulse(self) -> None:
        """Остановить пульсацию."""
        if self._animation:
            self._animation.stop()
            self._animation.deleteLater()
            self._animation = None
    
    def paintEvent(self, event) -> None:
        """Отрисовка пульсации."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Вычисляем радиус на основе пульсации
        pulse_factor = 0.3 + 0.7 * (0.5 + 0.5 * (1 - self._pulse_value))
        radius = int(self._size * pulse_factor / 2)
        
        # Рисуем круг
        center = self._size // 2
        painter.setBrush(QBrush(self._color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center - radius, center - radius, radius * 2, radius * 2)
    
    def cleanup(self) -> None:
        """Очистка ресурсов."""
        self.stop_pulse()


# =============================================================================
# PROGRESS INDICATOR
# =============================================================================

class CircularProgress(QWidget):
    """Круговой индикатор прогресса с анимацией.
    
    Параметры:
    ----------
    size : int
        Размер виджета
    line_width : int
        Толщина линии
    color : str
        Цвет прогресса (hex)
    parent : QWidget
        Родительский виджет
    
    Свойства:
    ---------
    value : float
        Значение прогресса (0.0 - 1.0)
    """
    
    def __init__(
        self,
        size: int = 40,
        line_width: int = 3,
        color: str = DesignSystem.colors.primary,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._size = size
        self._line_width = line_width
        self._color = QColor(color)
        self._value = 0.0
        self._animation: Optional[QPropertyAnimation] = None
        
        self.setFixedSize(size, size)
    
    def get_value(self) -> float:
        """Получить значение прогресса."""
        return self._value
    
    def set_value(self, value: float) -> None:
        """Установить значение прогресса."""
        self._value = max(0.0, min(1.0, value))
        self.update()
    
    value = Property(float, get_value, set_value)
    
    def animate_to(self, target: float, duration: int = Animation.duration_normal) -> None:
        """Анимация до целевого значения.
        
        Параметры:
        ----------
        target : float
            Целевое значение (0.0 - 1.0)
        duration : int
            Длительность анимации в мс
        """
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(duration)
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(max(0.0, min(1.0, target)))
        self._animation.setEasingCurve(Animation.easing_default)
        self._animation.start()
    
    def paintEvent(self, event) -> None:
        """Отрисовка индикатора."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Фоновый круг
        bg_color = QColor(DesignSystem.colors.surface_2)
        painter.setPen(QPen(QBrush(bg_color), self._line_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        center = self._size // 2
        radius = center - self._line_width
        
        painter.drawEllipse(center, center, radius * 2, radius * 2)
        
        # Прогресс
        if self._value > 0:
            painter.setPen(QPen(QBrush(self._color), self._line_width))
            
            # Дуга прогресса
            from PySide6.QtCore import QRectF
            rect = QRectF(
                self._line_width,
                self._line_width,
                self._size - self._line_width * 2,
                self._size - self._line_width * 2
            )
            
            # Начинаем сверху, идём по часовой
            start_angle = 90 * 16  # Qt uses 1/16 degree
            span_angle = int(-self._value * 360 * 16)
            
            painter.drawArc(rect, start_angle, span_angle)


# =============================================================================
# ANIMATION UTILITIES
# =============================================================================

def create_fade_in_animation(
    widget: QWidget,
    duration: int = Animation.duration_normal
) -> QPropertyAnimation:
    """Создать анимацию появления виджета.
    
    Параметры:
    ----------
    widget : QWidget
        Виджет для анимации
    duration : int
        Длительность в мс
    
    Возвращает:
    -----------
    QPropertyAnimation
        Настроенная анимация (не запущена)
    """
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    
    animation = QPropertyAnimation(effect, b"opacity")
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(Animation.easing_default)
    
    return animation


def create_slide_animation(
    widget: QWidget,
    start_pos: Tuple[int, int],
    end_pos: Tuple[int, int],
    duration: int = Animation.duration_normal
) -> QPropertyAnimation:
    """Создать анимацию перемещения виджета.
    
    Параметры:
    ----------
    widget : QWidget
        Виджет для анимации
    start_pos : Tuple[int, int]
        Начальная позиция (x, y)
    end_pos : Tuple[int, int]
        Конечная позиция (x, y)
    duration : int
        Длительность в мс
    
    Возвращает:
    -----------
    QPropertyAnimation
        Настроенная анимация (не запущена)
    """
    animation = QPropertyAnimation(widget, b"pos")
    animation.setDuration(duration)
    animation.setStartValue(start_pos)
    animation.setEndValue(end_pos)
    animation.setEasingCurve(Animation.easing_default)
    
    return animation


def run_sequential_animations(animations: List[QPropertyAnimation]) -> QSequentialAnimationGroup:
    """Запустить анимации последовательно.
    
    Параметры:
    ----------
    animations : List[QPropertyAnimation]
        Список анимаций для последовательного выполнения
    
    Возвращает:
    -----------
    QSequentialAnimationGroup
        Группа анимаций (уже запущена)
    """
    group = QSequentialAnimationGroup()
    for anim in animations:
        group.addAnimation(anim)
    group.start()
    return group


def run_parallel_animations(animations: List[QPropertyAnimation]) -> QParallelAnimationGroup:
    """Запустить анимации параллельно.
    
    Параметры:
    ----------
    animations : List[QPropertyAnimation]
        Список анимаций для параллельного выполнения
    
    Возвращает:
    -----------
    QParallelAnimationGroup
        Группа анимаций (уже запущена)
    """
    group = QParallelAnimationGroup()
    for anim in animations:
        group.addAnimation(anim)
    group.start()
    return group


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    # Skeleton loaders
    "SkeletonWidget",
    "SkeletonLoader",
    # Animated widgets
    "AnimatedCard",
    "FadeWidget",
    "PulseWidget",
    "CircularProgress",
    # Utilities
    "create_fade_in_animation",
    "create_slide_animation",
    "run_sequential_animations",
    "run_parallel_animations",
]
