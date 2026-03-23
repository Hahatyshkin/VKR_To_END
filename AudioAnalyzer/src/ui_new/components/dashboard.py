"""
Dashboard - современная панель мониторинга с ключевыми метриками.

Функционал:
- Отображение ключевых метрик (количество файлов, средние показатели качества)
- Миниатюры последних спектрограмм
- Быстрый доступ к часто используемым функциям
- История последних операций
- Современный дизайн с градиентами и анимациями

Архитектура:
============
DashboardWidget состоит из нескольких секций:
1. Header с приветствием и текущей датой
2. KPI карточки (анализированные файлы, средний SNR, методы)
3. Quick Actions - кнопки быстрого доступа
4. Recent Activity - последние операции
5. Method Selector - выбор методов обработки (NEW)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, QTimer, QSize, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QIcon, QColor, QPainter, QPen, QBrush, QLinearGradient
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QCheckBox,
    QGroupBox,
)

from ..design_system import DesignSystem, apply_modern_style
from ..icons import Icons

if TYPE_CHECKING:
    from ..worker import ResultRow

logger = logging.getLogger("ui_new.components.dashboard")


# =============================================================================
# ANIMATED FRAME - базовый класс для анимированных элементов
# =============================================================================

class AnimatedFrame(QFrame):
    """Базовый класс для фреймов с hover анимацией."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._hover = False
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def enterEvent(self, event) -> None:
        """При наведении мыши."""
        self._hover = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event) -> None:
        """При уходе мыши."""
        self._hover = False
        self.update()
        super().leaveEvent(event)


# =============================================================================
# KPI КАРТОЧКА (MODERN)
# =============================================================================

class KPICard(QFrame):
    """Современная карточка с ключевым показателем.

    Содержит:
    - Иконку (SVG-based)
    - Название метрики
    - Значение с анимацией
    - Тренд (опционально)
    - Градиентный акцент
    """
    
    clicked = Signal()
    
    def __init__(
        self,
        title: str,
        value: str = "0",
        subtitle: str = "",
        icon_name: str = "analytics",  # SVG icon name
        color: str = "primary",
        trend: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._title = title
        self._value = value
        self._subtitle = subtitle
        self._icon_name = icon_name
        self._color = color
        self._trend = trend
        self._hover = False

        self._setup_ui()
        self._apply_styles()
        
        # Accessibility
        self.setAccessibleName(f"KPI Card: {self._title}")
        self.setAccessibleDescription(f"Метрика: {self._title}. Значение: {self._value}")

    def _setup_ui(self) -> None:
        """Построить UI карточки."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Верхняя строка: иконка + название
        header_layout = QHBoxLayout()

        # Иконка в styled QLabel (без QFrame контейнера)
        self.icon_label = QLabel()
        icon_pixmap = Icons.get_pixmap(self._icon_name, "#FFFFFF", 20)
        self.icon_label.setPixmap(icon_pixmap)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(36, 36)
        self.icon_label.setStyleSheet(f"""
            background: {DesignSystem.get_gradient_css('primary')};
            border-radius: 8px;
        """)
        header_layout.addWidget(self.icon_label)

        self.title_label = QLabel(self._title)
        self.title_label.setStyleSheet(f"""
            font-size: 11px;
            color: {DesignSystem.colors.text_muted};
            font-weight: 500;
        """)
        header_layout.addWidget(self.title_label, 1)
        
        # Trend indicator
        if self._trend:
            trend_label = QLabel(self._trend)
            trend_color = DesignSystem.colors.success if self._trend.startswith("+") else DesignSystem.colors.error
            trend_label.setStyleSheet(f"""
                font-size: 12px;
                color: {trend_color};
                font-weight: 600;
                padding: 2px 6px;
                background-color: rgba(34, 197, 94, 0.1);
                border-radius: 4px;
            """)
            header_layout.addWidget(trend_label)

        layout.addLayout(header_layout)

        # Значение
        self.value_label = QLabel(self._value)
        self.value_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: 700;
            color: {DesignSystem.colors.text_primary};
        """)
        layout.addWidget(self.value_label)

        # Подзаголовок
        if self._subtitle:
            self.subtitle_label = QLabel(self._subtitle)
            self.subtitle_label.setStyleSheet(f"""
                font-size: 12px;
                color: {DesignSystem.colors.text_muted};
            """)
            layout.addWidget(self.subtitle_label)

        self.setCursor(Qt.PointingHandCursor)

    def _apply_styles(self) -> None:
        """Применить стили."""
        color = DesignSystem.get_color(self._color)
        self.setStyleSheet(f"""
            KPICard {{
                background: {DesignSystem.get_gradient_css('card')};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 16px;
                border-left: 4px solid {color};
            }}
            KPICard:hover {{
                border-color: {color};
                background-color: #2a2d32;
            }}
        """)

    def set_value(self, value: str, subtitle: str = "") -> None:
        """Установить новое значение."""
        self._value = value
        self.value_label.setText(value)
        if subtitle and hasattr(self, 'subtitle_label'):
            self.subtitle_label.setText(subtitle)

    def enterEvent(self, event) -> None:
        self._hover = True
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        """Обработать клик."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# =============================================================================
# QUICK ACTION BUTTON (MODERN)
# =============================================================================

class QuickActionButton(QFrame):
    """Современная кнопка быстрого действия с hover эффектом."""

    clicked = Signal()

    def __init__(
        self,
        text: str,
        icon_name: str = "play",  # SVG icon name
        description: str = "",
        variant: str = "primary",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._text = text
        self._icon_name = icon_name
        self._description = description
        self._variant = variant
        self._hover = False

        self._setup_ui()
        
        # Accessibility
        self.setAccessibleName(f"Quick Action: {self._text}")
        self.setAccessibleDescription(self._description or f"Выполнить: {self._text}")

    def _setup_ui(self) -> None:
        """Настроить UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # SVG Иконка в styled QLabel (без QFrame контейнера)
        self.icon_label = QLabel()
        icon_pixmap = Icons.get_pixmap(self._icon_name, "#FFFFFF", 28)
        self.icon_label.setPixmap(icon_pixmap)
        self.icon_label.setFixedSize(52, 52)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet(f"""
            background: {DesignSystem.get_gradient_css('primary')};
            border-radius: 12px;
        """)
        layout.addWidget(self.icon_label)

        # Текст и описание
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        text_label = QLabel(self._text)
        text_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {DesignSystem.colors.text_primary};
        """)
        text_layout.addWidget(text_label)

        if self._description:
            desc_label = QLabel(self._description)
            desc_label.setStyleSheet(f"""
                font-size: 13px;
                color: {DesignSystem.colors.text_muted};
            """)
            text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

        # Стрелка в styled QLabel
        arrow_label = QLabel()
        arrow_pixmap = Icons.get_pixmap("arrow_forward", DesignSystem.colors.text_secondary, 24)
        arrow_label.setPixmap(arrow_pixmap)
        arrow_label.setFixedSize(40, 40)
        arrow_label.setAlignment(Qt.AlignCenter)
        arrow_label.setStyleSheet(f"""
            background-color: {DesignSystem.colors.surface_3};
            border-radius: 10px;
        """)
        layout.addWidget(arrow_label)

        # Стили
        self._apply_styles()
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(80)

    def _apply_styles(self) -> None:
        """Применить стили."""
        self.setStyleSheet(f"""
            QuickActionButton {{
                background-color: {DesignSystem.colors.surface_2};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 16px;
            }}
            QuickActionButton:hover {{
                background-color: {DesignSystem.colors.surface_3};
                border: 2px solid {DesignSystem.colors.primary};
            }}
        """)

    def enterEvent(self, event) -> None:
        self._hover = True
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# =============================================================================
# METHOD SELECTOR WIDGET (NEW)
# =============================================================================

class MethodSelectorWidget(QFrame):
    """Виджет выбора методов обработки с современным дизайном.

    Features:
    - Чекбоксы для каждого метода
    - Визуальные карточки с иконками
    - Быстрый выбор группы (все/ни одного/рекомендуемые)
    """
    
    methods_changed = Signal(list)  # Список выбранных методов
    
    # Методы с SVG иконками (method_id, name, description, icon_name)
    METHODS = [
        ("standard", "Стандартный", "Прямое MP3 кодирование", "file_audio"),
        ("fwht", "FWHT", "Быстрое преобразование Уолша-Адамара", "speed"),
        ("fft", "FFT", "Быстрое преобразование Фурье", "analytics"),
        ("dct", "DCT", "Дискретное косинусное преобразование", "graphic_eq"),
        ("dwt", "DWT", "Дискретное вейвлет-преобразование (Хаар)", "waveform"),
        ("huffman", "Huffman", "Huffman-подобное сжатие", "folder_open"),
        ("rosenbrock", "Rosenbrock", "Нелинейное сглаживание", "tune"),
        ("daubechies", "Daubechies", "Вейвлеты Добечи (db4)", "waveform"),
        ("mdct", "MDCT", "Modified DCT (MP3/AAC)", "graphic_eq"),
    ]
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._checkboxes: Dict[str, QCheckBox] = {}
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Построить UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        
        # Заголовок
        header = QHBoxLayout()
        title = QLabel("Методы обработки")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {DesignSystem.colors.text_primary};
        """)
        header.addWidget(title)
        header.addStretch()
        
        # Быстрые кнопки выбора
        btn_all = QPushButton("Все")
        btn_all.setFixedHeight(36)
        btn_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.colors.surface_2};
                color: {DesignSystem.colors.text_secondary};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.colors.primary};
                color: white;
                border-color: {DesignSystem.colors.primary};
            }}
        """)
        btn_all.clicked.connect(self._select_all)
        header.addWidget(btn_all)
        
        btn_none = QPushButton("Сброс")
        btn_none.setFixedHeight(36)
        btn_none.setStyleSheet(btn_all.styleSheet())
        btn_none.clicked.connect(self._select_none)
        header.addWidget(btn_none)
        
        layout.addLayout(header)
        
        # ScrollArea для методов (адаптивность)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(300)
        scroll.setMaximumHeight(500)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {DesignSystem.colors.surface_3};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {DesignSystem.colors.border_light};
            }}
        """)
        
        # Контейнер для методов
        methods_container = QWidget()
        methods_layout = QVBoxLayout(methods_container)
        methods_layout.setContentsMargins(0, 0, 0, 0)
        methods_layout.setSpacing(10)
        
        for method_id, name, desc, icon in self.METHODS:
            card = self._create_method_card(method_id, name, desc, icon)
            methods_layout.addWidget(card)
        
        scroll.setWidget(methods_container)
        layout.addWidget(scroll, 1)
        
        self._apply_styles()
    
    def _create_method_card(self, method_id: str, name: str, desc: str, icon_name: str) -> QFrame:
        """Создать карточку метода с SVG иконкой."""
        card = QFrame()
        card.setObjectName("methodCard")
        card.setMinimumHeight(60)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(14)
        
        # Чекбокс с галочкой - контейнер для центрирования
        cb_container = QWidget()
        cb_container.setFixedSize(28, 28)
        cb_layout = QVBoxLayout(cb_container)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        cb_layout.setSpacing(0)
        
        cb = QCheckBox()
        cb.setChecked(True)
        cb.setStyleSheet(f"""
            QCheckBox {{
                spacing: 0px;
                margin: 0px;
                padding: 0px;
            }}
            QCheckBox::indicator {{
                width: 22px;
                height: 22px;
                border: 2px solid {DesignSystem.colors.border_light};
                border-radius: 6px;
                background-color: {DesignSystem.colors.surface_1};
            }}
            QCheckBox::indicator:checked {{
                background-color: {DesignSystem.colors.primary};
                border-color: {DesignSystem.colors.primary};
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iI0ZGRkZGRiI+PHBhdGggZD0iTTkgMTYuMTdMNC44MyAxMmwtMS40MiAxLjQxTDkgMTkgMjEgN2wtMS40MS0xLjQxeiIvPjwvc3ZnPg==);
            }}
            QCheckBox::indicator:hover {{
                border-color: {DesignSystem.colors.primary};
            }}
        """)
        cb.stateChanged.connect(self._on_method_changed)
        self._checkboxes[method_id] = cb
        cb_layout.addWidget(cb, 0, Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(cb_container)
        
        # SVG Иконка в styled QLabel
        icon_label = QLabel()
        icon_pixmap = Icons.get_pixmap(icon_name, DesignSystem.colors.primary, 24)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"""
            background-color: {DesignSystem.colors.surface_1};
            border-radius: 10px;
        """)
        card_layout.addWidget(icon_label)
        
        # Текст
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 600;
            color: {DesignSystem.colors.text_primary};
        """)
        text_layout.addWidget(name_label)
        
        desc_label = QLabel(desc)
        desc_label.setStyleSheet(f"""
            font-size: 12px;
            color: {DesignSystem.colors.text_muted};
        """)
        text_layout.addWidget(desc_label)
        
        card_layout.addLayout(text_layout, 1)
        
        # Применяем стиль к карте через objectName
        card.setStyleSheet(f"""
            QFrame#methodCard {{
                background-color: {DesignSystem.colors.surface_2};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 12px;
            }}
            QFrame#methodCard:hover {{
                border-color: {DesignSystem.colors.primary};
            }}
        """)
        
        return card
    
    def _apply_styles(self) -> None:
        """Применить стили."""
        self.setStyleSheet(f"""
            MethodSelectorWidget {{
                background: transparent;
            }}
        """)
    
    def _select_all(self) -> None:
        """Выбрать все методы."""
        for cb in self._checkboxes.values():
            cb.setChecked(True)
    
    def _select_none(self) -> None:
        """Снять выбор со всех методов."""
        for cb in self._checkboxes.values():
            cb.setChecked(False)
    
    def _on_method_changed(self) -> None:
        """Обработать изменение выбора метода."""
        selected = self.get_selected_methods()
        self.methods_changed.emit(selected)
    
    def get_selected_methods(self) -> List[str]:
        """Получить список выбранных методов."""
        return [mid for mid, cb in self._checkboxes.items() if cb.isChecked()]
    
    def set_selected_methods(self, methods: List[str]) -> None:
        """Установить выбранные методы."""
        for mid, cb in self._checkboxes.items():
            cb.setChecked(mid in methods)


# =============================================================================
# RECENT ACTIVITY ITEM (MODERN)
# =============================================================================

class RecentActivityItem(QFrame):
    """Современный элемент истории последних операций."""

    clicked = Signal(str)

    def __init__(
        self,
        filename: str,
        method: str,
        timestamp: datetime,
        metrics: Dict[str, float],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._filename = filename
        self._method = method
        self._timestamp = timestamp
        self._metrics = metrics

        self._setup_ui()
        
        # Accessibility
        self.setAccessibleName(f"Recent file: {self._filename}")
        self.setAccessibleDescription(f"Файл {self._filename} обработан методом {self._method}")

    def _setup_ui(self) -> None:
        """Построить UI элемента."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(14)

        # Иконка в styled QLabel
        icon_label = QLabel()
        icon_pixmap = Icons.get_pixmap("music_note", DesignSystem.colors.primary, 24)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"""
            background-color: {DesignSystem.colors.surface_2};
            border-radius: 10px;
        """)
        layout.addWidget(icon_label)

        # Информация
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)

        # Имя файла (обрезанное)
        display_name = self._filename if len(self._filename) <= 30 else self._filename[:27] + "..."
        filename_label = QLabel(display_name)
        filename_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 500;
            color: {DesignSystem.colors.text_primary};
        """)
        filename_label.setToolTip(self._filename)
        info_layout.addWidget(filename_label)

        method_label = QLabel(f"Метод: {self._method}")
        method_label.setStyleSheet(f"""
            font-size: 12px;
            color: {DesignSystem.colors.text_muted};
        """)
        info_layout.addWidget(method_label)

        layout.addLayout(info_layout, 1)

        # Метрики
        if self._metrics:
            snr = self._metrics.get('snr', 0)
            snr_label = QLabel(f"SNR: {snr:.1f} dB")
            snr_label.setStyleSheet(f"""
                font-size: 12px;
                font-weight: 600;
                color: {DesignSystem.colors.success};
                padding: 4px 8px;
                background-color: rgba(34, 197, 94, 0.1);
                border-radius: 6px;
            """)
            layout.addWidget(snr_label)

        # Время
        time_str = self._timestamp.strftime("%H:%M")
        time_label = QLabel(time_str)
        time_label.setStyleSheet(f"""
            font-size: 11px;
            color: {DesignSystem.colors.text_muted};
        """)
        layout.addWidget(time_label)

        self.setStyleSheet(f"""
            RecentActivityItem {{
                background-color: transparent;
                border-radius: 8px;
            }}
            RecentActivityItem:hover {{
                background-color: {DesignSystem.colors.surface_2};
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        """Обработать клик."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._filename)
        super().mousePressEvent(event)


# =============================================================================
# MINI SPECTROGRAM WIDGET (MODERN)
# =============================================================================

class MiniSpectrogram(QFrame):
    """Миниатюра спектрограммы с современным дизайном."""

    clicked = Signal(str)

    def __init__(
        self,
        filename: str,
        spectrum_data: Optional[Any] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._filename = filename
        self._spectrum_data = spectrum_data

        self._setup_ui()
        self._apply_styles()
        
        # Accessibility
        self.setAccessibleName(f"Spectrogram preview: {self._filename}")
        self.setAccessibleDescription(f"Миниатюра спектрограммы файла {self._filename}")

    def _setup_ui(self) -> None:
        """Построить UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Placeholder для спектрограммы с градиентом и SVG иконкой
        self.preview_label = QLabel()
        preview_pixmap = Icons.get_pixmap("waveform", "#FFFFFF", 36)
        self.preview_label.setPixmap(preview_pixmap)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(f"""
            QLabel {{
                background: {DesignSystem.get_gradient_css('primary')};
                border-radius: 10px;
            }}
        """)
        self.preview_label.setFixedSize(120, 80)
        layout.addWidget(self.preview_label, 0, Qt.AlignCenter)

        # Имя файла
        filename_short = self._filename[:14] + "..." if len(self._filename) > 14 else self._filename
        name_label = QLabel(filename_short)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(f"""
            font-size: 11px;
            color: {DesignSystem.colors.text_muted};
            background: transparent;
        """)
        name_label.setToolTip(self._filename)
        layout.addWidget(name_label, 0, Qt.AlignCenter)

    def _apply_styles(self) -> None:
        """Применить стили."""
        self.setStyleSheet(f"""
            MiniSpectrogram {{
                background-color: {DesignSystem.colors.surface_2};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 14px;
            }}
            MiniSpectrogram:hover {{
                border-color: {DesignSystem.colors.primary};
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(150, 130)

    def paintEvent(self, event) -> None:
        """Отрисовать мини-спектрограмму."""
        super().paintEvent(event)

        if self._spectrum_data is not None:
            # TODO: Отрисовка реальной спектрограммы
            pass

    def mousePressEvent(self, event) -> None:
        """Обработать клик."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._filename)
        super().mousePressEvent(event)


# =============================================================================
# DASHBOARD WIDGET (MODERN)
# =============================================================================

class DashboardWidget(QWidget):
    """Главная панель мониторинга с современным дизайном.

    Содержит:
    - KPI карточки с ключевыми метриками
    - Quick Actions для быстрого доступа к функциям
    - Method Selector для выбора методов обработки
    - Recent Activity - последние операции
    - Миниатюры последних спектрограмм
    """

    # Сигналы
    open_file_requested = Signal()
    batch_process_requested = Signal()
    compare_requested = Signal()
    file_selected = Signal(str)
    methods_changed = Signal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Состояние
        self._results: List[ResultRow] = []
        self._recent_files: List[Dict[str, Any]] = []

        self._setup_ui()
        self._connect_signals()

        # Обновление времени
        self._time_timer = QTimer(self)
        self._time_timer.timeout.connect(self._update_datetime)
        self._time_timer.start(60000)  # каждую минуту

    def _setup_ui(self) -> None:
        """Построить UI Dashboard."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Header
        self._build_header(main_layout)

        # KPI карточки (компактные)
        self._build_kpi_cards(main_layout)

        # Быстрые действия (в строку)
        self._build_quick_actions_row(main_layout)

        # Основной контент в два столбца: Методы + Последние операции
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Левый столбец: Методы обработки (компактнее)
        left_column = QVBoxLayout()
        left_column.setSpacing(8)
        self._build_method_selector(left_column)
        content_layout.addLayout(left_column, 1)

        # Правый столбец: Последние операции + Спектрограммы
        right_column = QVBoxLayout()
        right_column.setSpacing(8)
        self._build_recent_activity(right_column)
        self._build_spectrogram_previews(right_column)
        content_layout.addLayout(right_column, 1)

        main_layout.addLayout(content_layout, 1)

    def _build_header(self, layout: QVBoxLayout) -> None:
        """Построить заголовок Dashboard."""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {DesignSystem.get_gradient_css('header')};
                border-radius: 16px;
                padding: 20px;
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)

        # Приветствие
        welcome_layout = QVBoxLayout()
        welcome_layout.setSpacing(6)

        greeting = self._get_greeting()
        self.greeting_label = QLabel(f"{greeting}!")
        self.greeting_label.setStyleSheet(f"""
            font-size: 26px;
            font-weight: 700;
            color: {DesignSystem.colors.text_primary};
        """)
        welcome_layout.addWidget(self.greeting_label)

        self.date_label = QLabel(datetime.now().strftime("%A, %d %B %Y"))
        self.date_label.setStyleSheet(f"""
            font-size: 14px;
            color: {DesignSystem.colors.text_muted};
        """)
        welcome_layout.addWidget(self.date_label)

        header_layout.addLayout(welcome_layout, 1)

        # Логотип/название приложения
        app_label = QLabel("AudioAnalyzer")
        app_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: white;
            padding: 12px 24px;
            background: {DesignSystem.get_gradient_css('primary')};
            border-radius: 12px;
        """)
        header_layout.addWidget(app_label)

        layout.addWidget(header)

    def _build_kpi_cards(self, layout: QVBoxLayout) -> None:
        """Построить KPI карточки."""
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        # Карточка: Анализированные файлы
        self.files_card = KPICard(
            title="Файлы",
            value="0",
            subtitle="В сессии",
            icon_name="folder_open",
            color="accent_blue"
        )
        self.files_card.setMaximumWidth(200)
        self.files_card.clicked.connect(self.open_file_requested)
        cards_layout.addWidget(self.files_card)

        # Карточка: Средний SNR
        self.snr_card = KPICard(
            title="SNR",
            value="-- dB",
            subtitle="Качество",
            icon_name="analytics",
            color="success"
        )
        self.snr_card.setMaximumWidth(200)
        cards_layout.addWidget(self.snr_card)

        # Карточка: Методы
        self.methods_card = KPICard(
            title="Методов",
            value="0",
            subtitle="Использовано",
            icon_name="method",
            color="secondary"
        )
        self.methods_card.setMaximumWidth(200)
        cards_layout.addWidget(self.methods_card)

        # Карточка: Время обработки
        self.time_card = KPICard(
            title="Время",
            value="0.0s",
            subtitle="Обработка",
            icon_name="clock",
            color="accent_orange"
        )
        self.time_card.setMaximumWidth(200)
        cards_layout.addWidget(self.time_card)
        
        cards_layout.addStretch(1)

        layout.addLayout(cards_layout)

    def _build_quick_actions(self, layout: QVBoxLayout) -> None:
        """Построить панель быстрых действий."""
        section_label = QLabel("Быстрые действия")
        section_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {DesignSystem.colors.text_primary};
            margin-bottom: 12px;
        """)
        layout.addWidget(section_label)

        actions_frame = QFrame()
        actions_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.colors.surface_1};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 16px;
                padding: 8px;
            }}
        """)
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(12, 12, 12, 12)

        # Открыть файл
        self.btn_open = QuickActionButton(
            "Открыть WAV файл",
            icon_name="folder_open",
            description="Выбрать аудиофайл для анализа",
            variant="primary"
        )
        self.btn_open.clicked.connect(self.open_file_requested)
        actions_layout.addWidget(self.btn_open)

        # Пакетная обработка
        self.btn_batch = QuickActionButton(
            "Пакетная обработка",
            icon_name="batch_process",
            description="Обработать папку с WAV-файлами"
        )
        self.btn_batch.clicked.connect(self.batch_process_requested)
        actions_layout.addWidget(self.btn_batch)

        # Сравнение
        self.btn_compare = QuickActionButton(
            "Сравнить файлы",
            icon_name="compare",
            description="Сравнительный анализ аудиофайлов"
        )
        self.btn_compare.clicked.connect(self.compare_requested)
        actions_layout.addWidget(self.btn_compare)

        layout.addWidget(actions_frame)

    def _build_quick_actions_row(self, layout: QVBoxLayout) -> None:
        """Построить панель быстрых действий в виде горизонтальной строки."""
        section_label = QLabel("Быстрые действия")
        section_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 600;
            color: {DesignSystem.colors.text_primary};
            margin-bottom: 8px;
        """)
        layout.addWidget(section_label)

        # Горизонтальный контейнер для кнопок
        actions_frame = QFrame()
        actions_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.colors.surface_1};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 12px;
            }}
        """)
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setSpacing(8)
        actions_layout.setContentsMargins(12, 10, 12, 10)

        # Кнопка: Открыть файл (компактная)
        self.btn_open = QPushButton("📁 Открыть файл")
        self.btn_open.setStyleSheet(f"""
            QPushButton {{
                background: {DesignSystem.get_gradient_css('primary')};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {DesignSystem.colors.primary_pressed};
            }}
        """)
        self.btn_open.clicked.connect(self.open_file_requested)
        actions_layout.addWidget(self.btn_open)

        # Кнопка: Пакетная обработка
        self.btn_batch = QPushButton("📦 Пакетная обработка")
        self.btn_batch.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.colors.surface_2};
                color: {DesignSystem.colors.text_primary};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.colors.surface_3};
                border-color: {DesignSystem.colors.primary};
            }}
        """)
        self.btn_batch.clicked.connect(self.batch_process_requested)
        actions_layout.addWidget(self.btn_batch)

        # Кнопка: Сравнить
        self.btn_compare = QPushButton("📊 Сравнить")
        self.btn_compare.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.colors.surface_2};
                color: {DesignSystem.colors.text_primary};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.colors.surface_3};
                border-color: {DesignSystem.colors.primary};
            }}
        """)
        self.btn_compare.clicked.connect(self.compare_requested)
        actions_layout.addWidget(self.btn_compare)

        actions_layout.addStretch(1)
        layout.addWidget(actions_frame)

    def _build_method_selector(self, layout: QVBoxLayout) -> None:
        """Построить панель выбора методов."""
        self.method_selector = MethodSelectorWidget()
        self.method_selector.methods_changed.connect(self.methods_changed.emit)
        layout.addWidget(self.method_selector)

    def _build_recent_activity(self, layout: QVBoxLayout) -> None:
        """Построить панель последних операций."""
        section_label = QLabel("Последние операции")
        section_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 600;
            color: {DesignSystem.colors.text_primary};
            margin-bottom: 8px;
        """)
        layout.addWidget(section_label)

        # Scrollable область для списка
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {DesignSystem.colors.surface_1};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 14px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {DesignSystem.colors.surface_3};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {DesignSystem.colors.border_light};
            }}
        """)
        scroll.setMinimumHeight(180)
        scroll.setMaximumHeight(280)

        self.activity_container = QWidget()
        self.activity_layout = QVBoxLayout(self.activity_container)
        self.activity_layout.setContentsMargins(10, 10, 10, 10)
        self.activity_layout.setSpacing(4)
        
        # Placeholder когда нет записей
        self._activity_placeholder = QLabel("Нет недавних операций\nОбработайте файлы для появления записей")
        self._activity_placeholder.setAlignment(Qt.AlignCenter)
        self._activity_placeholder.setStyleSheet(f"""
            color: {DesignSystem.colors.text_muted};
            font-size: 13px;
            padding: 30px;
        """)
        self.activity_layout.addWidget(self._activity_placeholder)
        self.activity_layout.addStretch(1)

        scroll.setWidget(self.activity_container)
        layout.addWidget(scroll, 1)

    def _build_spectrogram_previews(self, layout: QVBoxLayout) -> None:
        """Построить миниатюры спектрограмм."""
        section_label = QLabel("Последние спектрограммы")
        section_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 600;
            color: {DesignSystem.colors.text_primary};
            margin-bottom: 8px;
        """)
        layout.addWidget(section_label)

        previews_frame = QFrame()
        previews_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.colors.surface_1};
                border: 1px solid {DesignSystem.colors.border};
                border-radius: 14px;
                padding: 16px;
            }}
        """)
        previews_layout = QGridLayout(previews_frame)
        previews_layout.setSpacing(12)

        # Placeholder миниатюры
        for i in range(4):
            row, col = i // 2, i % 2
            preview = MiniSpectrogram(f"empty_{i}")
            preview.clicked.connect(self._on_preview_clicked)
            previews_layout.addWidget(preview, row, col)

        layout.addWidget(previews_frame)
        layout.addStretch(1)

    def _connect_signals(self) -> None:
        """Подключить внутренние сигналы."""
        pass

    def _get_greeting(self) -> str:
        """Получить приветствие по времени суток."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "Доброе утро"
        elif 12 <= hour < 18:
            return "Добрый день"
        elif 18 <= hour < 23:
            return "Добрый вечер"
        else:
            return "Доброй ночи"

    def _update_datetime(self) -> None:
        """Обновить дату и приветствие."""
        self.date_label.setText(datetime.now().strftime("%A, %d %B %Y"))
        self.greeting_label.setText(f"{self._get_greeting()}!")

    def _on_preview_clicked(self, filename: str) -> None:
        """Обработать клик на миниатюру."""
        if not filename.startswith("empty_"):
            self.file_selected.emit(filename)

    # =========================================================================
    # ПУБЛИЧНЫЕ МЕТОДЫ
    # =========================================================================

    def update_results(self, results: List[ResultRow]) -> None:
        """Обновить результаты анализа.

        Параметры:
        ----------
        results : List[ResultRow]
            Список результатов анализа
        """
        self._results = results

        # Обновляем KPI карточки
        self.files_card.set_value(str(len(results)))

        if results:
            # Средний SNR (используем snr_db из ResultRow)
            import math
            snr_values = []
            for r in results:
                if hasattr(r, 'snr_db') and r.snr_db is not None:
                    try:
                        val = float(r.snr_db)
                        if not math.isnan(val) and not math.isinf(val):
                            snr_values.append(val)
                    except (ValueError, TypeError):
                        pass
            if snr_values:
                avg_snr = sum(snr_values) / len(snr_values)
                self.snr_card.set_value(f"{avg_snr:.1f} dB")
            else:
                self.snr_card.set_value("-- dB")

            # Количество уникальных методов
            methods = set(r.variant for r in results if r.variant)
            self.methods_card.set_value(str(len(methods)))

            # Обновляем последние операции
            self._update_recent_activity(results[-10:])

    def update_processing_time(self, time_seconds: float) -> None:
        """Обновить время обработки.

        Параметры:
        ----------
        time_seconds : float
            Время обработки в секундах
        """
        if time_seconds < 60:
            self.time_card.set_value(f"{time_seconds:.1f}s")
        else:
            minutes = int(time_seconds // 60)
            seconds = time_seconds % 60
            self.time_card.set_value(f"{minutes}m {seconds:.0f}s")

    def _update_recent_activity(self, results: List[ResultRow]) -> None:
        """Обновить список последних операций."""
        # Очищаем старые элементы
        while self.activity_layout.count() > 1:
            item = self.activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Добавляем новые элементы
        for result in reversed(results[-10:]):
            # Используем правильные поля ResultRow: snr_db и source
            snr_val = 0.0
            if hasattr(result, 'snr_db') and result.snr_db is not None:
                try:
                    # Проверяем на NaN
                    import math
                    if not math.isnan(float(result.snr_db)):
                        snr_val = float(result.snr_db)
                except (ValueError, TypeError):
                    pass
            metrics = {'snr': snr_val}
            item = RecentActivityItem(
                filename=result.source if hasattr(result, 'source') else "Unknown",
                method=result.variant if hasattr(result, 'variant') else "Unknown",
                timestamp=datetime.now(),
                metrics=metrics
            )
            item.clicked.connect(self.file_selected)
            self.activity_layout.insertWidget(0, item)

    def add_recent_file(self, filename: str, spectrum_data: Any = None) -> None:
        """Добавить недавний файл с данными спектрограммы.

        Параметры:
        ----------
        filename : str
            Имя файла
        spectrum_data : Any
            Данные спектрограммы для миниатюры
        """
        self._recent_files.insert(0, {
            'filename': filename,
            'spectrum_data': spectrum_data,
            'timestamp': datetime.now()
        })

        # Ограничиваем список
        self._recent_files = self._recent_files[:20]

    def get_selected_methods(self) -> List[str]:
        """Получить выбранные методы обработки."""
        return self.method_selector.get_selected_methods()

    def set_selected_methods(self, methods: List[str]) -> None:
        """Установить выбранные методы."""
        self.method_selector.set_selected_methods(methods)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "DashboardWidget",
    "KPICard",
    "QuickActionButton",
    "RecentActivityItem",
    "MiniSpectrogram",
    "MethodSelectorWidget",
]
