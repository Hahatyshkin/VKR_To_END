"""
Design System - централизованная система стилей для AudioAnalyzer.

Назначение:
- Единая цветовая палитра (Material Design 3)
- Градиенты и тени
- Типографика
- Анимации и transitions
- Компонентные стили

Использование:
------------
from ui_new.design_system import DesignSystem, apply_modern_style

# Применить к главному окну
apply_modern_style(main_window)

# Использовать цвета
color = DesignSystem.get_color('primary')
gradient = DesignSystem.get_gradient('primary')
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from enum import Enum

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QByteArray
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QWidget, QApplication, QMainWindow, QPushButton, QLabel,
    QFrame, QComboBox, QLineEdit, QTableWidget, QTabWidget,
    QProgressBar, QCheckBox, QGroupBox, QScrollArea,
)

logger = logging.getLogger("ui_new.design_system")


# =============================================================================
# ЦВЕТОВАЯ ПАЛИТРА (Material Design 3 + Tailwind-inspired)
# =============================================================================

@dataclass(frozen=True)
class ColorPalette:
    """Цветовая палитра темы."""
    
    # Primary Colors (Indigo)
    primary: str = "#6366F1"
    primary_hover: str = "#818CF8"
    primary_pressed: str = "#4F46E5"
    primary_container: str = "#312E81"
    primary_light: str = "#A5B4FC"
    
    # Secondary Colors (Purple)
    secondary: str = "#A855F7"
    secondary_hover: str = "#C084FC"
    secondary_pressed: str = "#9333EA"
    
    # Surface Colors (elevation-based)
    surface_0: str = "#0F0F0F"      # Lowest elevation
    surface_1: str = "#18181B"      # Base
    surface_2: str = "#27272A"      # Raised
    surface_3: str = "#3F3F46"      # Overlay
    
    # Text Colors (improved contrast for accessibility)
    text_primary: str = "#F9FAFB"
    text_secondary: str = "#D1D5DB"
    text_muted: str = "#A8ADB5"      # Improved from #9CA3AF for better contrast (5.5:1 min)
    text_disabled: str = "#6B7280"
    
    # Accent Colors
    accent_blue: str = "#3B82F6"
    accent_green: str = "#22C55E"
    accent_orange: str = "#F97316"
    accent_pink: str = "#EC4899"
    accent_teal: str = "#14B8A6"
    accent_yellow: str = "#EAB308"
    
    # Status Colors
    success: str = "#22C55E"
    success_bg: str = "#166534"
    warning: str = "#F97316"
    warning_bg: str = "#854D0E"
    error: str = "#EF4444"
    error_bg: str = "#991B1B"
    info: str = "#3B82F6"
    info_bg: str = "#1E40AF"
    
    # Border & Divider
    border: str = "#374151"
    border_light: str = "#4B5563"
    divider: str = "#27272A"


# =============================================================================
# ГРАДИЕНТЫ
# =============================================================================

@dataclass(frozen=True)
class GradientPalette:
    """Градиенты для элементов UI."""
    
    primary: Tuple[str, str] = ("#6366F1", "#8B5CF6")
    secondary: Tuple[str, str] = ("#A855F7", "#EC4899")
    success: Tuple[str, str] = ("#22C55E", "#16A34A")
    warning: Tuple[str, str] = ("#F97316", "#EA580C")
    error: Tuple[str, str] = ("#EF4444", "#DC2626")
    surface: Tuple[str, str] = ("#18181B", "#0F0F0F")
    card: Tuple[str, str] = ("#27272A", "#18181B")
    header: Tuple[str, str] = ("#1F2937", "#111827")


# =============================================================================
# ТЕНИ
# =============================================================================

@dataclass(frozen=True)
class ShadowPalette:
    """Тени для элементов UI (CSS-like)."""
    
    none: str = "none"
    sm: str = "0 1px 2px rgba(0, 0, 0, 0.3)"
    md: str = "0 4px 6px rgba(0, 0, 0, 0.4)"
    lg: str = "0 10px 15px rgba(0, 0, 0, 0.5)"
    xl: str = "0 20px 25px rgba(0, 0, 0, 0.6)"
    inner: str = "inset 0 2px 4px rgba(0, 0, 0, 0.3)"
    
    # Colored shadows for accent elements
    primary: str = "0 4px 14px rgba(99, 102, 241, 0.4)"
    success: str = "0 4px 14px rgba(34, 197, 94, 0.4)"
    error: str = "0 4px 14px rgba(239, 68, 68, 0.4)"


# =============================================================================
# ТИПОГРАФИКА
# =============================================================================

@dataclass(frozen=True)
class Typography:
    """Типографика приложения."""
    
    # Font families
    font_primary: str = "Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    font_mono: str = "JetBrains Mono, Consolas, monospace"
    
    # Heading sizes
    h1_size: int = 28
    h1_weight: int = 700
    
    h2_size: int = 22
    h2_weight: int = 600
    
    h3_size: int = 18
    h3_weight: int = 600
    
    h4_size: int = 16
    h4_weight: int = 600
    
    # Body sizes
    body_size: int = 14
    body_weight: int = 400
    
    body_sm_size: int = 12
    body_sm_weight: int = 400
    
    # Code
    code_size: int = 13
    code_weight: int = 400
    
    # Line heights
    line_height_tight: float = 1.25
    line_height_normal: float = 1.5
    line_height_relaxed: float = 1.75


# =============================================================================
# АНИМАЦИИ
# =============================================================================

@dataclass(frozen=True)
class Animation:
    """Параметры анимаций."""
    
    # Durations (ms)
    duration_fast: int = 150
    duration_normal: int = 250
    duration_slow: int = 400
    
    # Easing curves
    easing_default: QEasingCurve.Type = QEasingCurve.Type.OutCubic
    easing_bounce: QEasingCurve.Type = QEasingCurve.Type.OutBack
    easing_smooth: QEasingCurve.Type = QEasingCurve.Type.InOutCubic
    
    # Hover effects
    hover_scale: float = 1.02
    hover_translate_y: int = -2


# =============================================================================
# DESIGN SYSTEM CLASS
# =============================================================================

class DesignSystem:
    """Централизованная система дизайна.
    
    Предоставляет:
    - Цвета и градиенты
    - Типографику
    - Стили компонентов
    - Анимации
    
    Использование:
    ------------
    >>> color = DesignSystem.colors.primary
    >>> gradient = DesignSystem.gradients.primary
    >>> style = DesignSystem.get_button_style()
    """
    
    colors = ColorPalette()
    gradients = GradientPalette()
    shadows = ShadowPalette()
    typography = Typography()
    animation = Animation()
    
    @classmethod
    def get_color(cls, name: str) -> str:
        """Получить цвет по имени.
        
        Параметры:
        ----------
        name : str
            Имя цвета (primary, secondary, success, etc.)
            
        Возвращает:
        -----------
        str
            HEX цвет
        """
        return getattr(cls.colors, name, cls.colors.primary)
    
    @classmethod
    def get_gradient_qt(cls, name: str) -> QLinearGradient:
        """Получить Qt градиент по имени.
        
        Параметры:
        ----------
        name : str
            Имя градиента
            
        Возвращает:
        -----------
        QLinearGradient
            Qt градиент для рисования
        """
        colors = getattr(cls.gradients, name, cls.gradients.primary)
        gradient = QLinearGradient(0, 0, 1, 1)
        gradient.setCoordinateMode(QLinearGradient.ObjectBoundingMode)
        gradient.setColorAt(0, QColor(colors[0]))
        gradient.setColorAt(1, QColor(colors[1]))
        return gradient
    
    @classmethod
    def get_gradient_css(cls, name: str, direction: str = "135deg") -> str:
        """Получить CSS градиент по имени.
        
        Параметры:
        ----------
        name : str
            Имя градиента
        direction : str
            Направление градиента
            
        Возвращает:
        -----------
        str
            CSS строка градиента
        """
        colors = getattr(cls.gradients, name, cls.gradients.primary)
        return f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {colors[0]}, stop:1 {colors[1]})"
    
    # =========================================================================
    # СТИЛИ КОМПОНЕНТОВ
    # =========================================================================
    
    @classmethod
    def get_button_style(
        cls,
        variant: str = "primary",
        size: str = "medium"
    ) -> str:
        """Получить стиль кнопки.
        
        Параметры:
        ----------
        variant : str
            Вариант: primary, secondary, success, danger, ghost
        size : str
            Размер: small, medium, large
            
        Возвращает:
        -----------
        str
            CSS stylesheet
        """
        # Размеры
        sizes = {
            "small": ("padding: 6px 12px;", "font-size: 12px;", "border-radius: 6px;"),
            "medium": ("padding: 10px 20px;", "font-size: 14px;", "border-radius: 8px;"),
            "large": ("padding: 14px 28px;", "font-size: 16px;", "border-radius: 10px;"),
        }
        pad, font, radius = sizes.get(size, sizes["medium"])
        
        # Варианты
        variants = {
            "primary": f"""
                QPushButton {{
                    {pad}
                    {font}
                    {radius}
                    background: {cls.get_gradient_css('primary')};
                    color: white;
                    border: none;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {cls.get_gradient_css('secondary')};
                }}
                QPushButton:pressed {{
                    background: {cls.colors.primary_pressed};
                }}
                QPushButton:disabled {{
                    background: {cls.colors.surface_3};
                    color: {cls.colors.text_disabled};
                }}
            """,
            "secondary": f"""
                QPushButton {{
                    {pad}
                    {font}
                    {radius}
                    background-color: {cls.colors.surface_2};
                    color: {cls.colors.text_primary};
                    border: 1px solid {cls.colors.border};
                }}
                QPushButton:hover {{
                    background-color: {cls.colors.surface_3};
                    border-color: {cls.colors.primary};
                }}
                QPushButton:pressed {{
                    background-color: {cls.colors.primary_container};
                }}
                QPushButton:disabled {{
                    background-color: {cls.colors.surface_1};
                    color: {cls.colors.text_disabled};
                }}
            """,
            "success": f"""
                QPushButton {{
                    {pad}
                    {font}
                    {radius}
                    background: {cls.get_gradient_css('success')};
                    color: white;
                    border: none;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #16A34A;
                }}
            """,
            "danger": f"""
                QPushButton {{
                    {pad}
                    {font}
                    {radius}
                    background: {cls.get_gradient_css('error')};
                    color: white;
                    border: none;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #DC2626;
                }}
            """,
            "ghost": f"""
                QPushButton {{
                    {pad}
                    {font}
                    {radius}
                    background: transparent;
                    color: {cls.colors.text_primary};
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                }}
                QPushButton:pressed {{
                    background-color: rgba(255, 255, 255, 0.05);
                }}
            """,
        }
        
        return variants.get(variant, variants["primary"])
    
    @classmethod
    def get_card_style(cls, elevated: bool = True) -> str:
        """Получить стиль карточки.
        
        Параметры:
        ----------
        elevated : bool
            Добавить тень возвышения
            
        Возвращает:
        -----------
        str
            CSS stylesheet
        """
        shadow = cls.shadows.md if elevated else cls.shadows.none
        return f"""
            QFrame {{
                background: {cls.get_gradient_css('card')};
                border: 1px solid {cls.colors.border};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {cls.colors.primary};
            }}
        """
    
    @classmethod
    def get_input_style(cls) -> str:
        """Получить стиль поля ввода.
        
        Возвращает:
        -----------
        str
            CSS stylesheet
        """
        return f"""
            QLineEdit {{
                background-color: {cls.colors.surface_1};
                color: {cls.colors.text_primary};
                border: 1px solid {cls.colors.border};
                border-radius: 10px;
                padding: 12px 16px;
                font-size: 15px;
                min-height: 24px;
                selection-background-color: {cls.colors.primary};
            }}
            QLineEdit:focus {{
                border: 2px solid {cls.colors.primary};
                background-color: {cls.colors.surface_2};
            }}
            QLineEdit:read-only {{
                background-color: {cls.colors.surface_2};
                color: {cls.colors.text_primary};
                border: 1px solid {cls.colors.border_light};
            }}
            QLineEdit:disabled {{
                background-color: {cls.colors.surface_0};
                color: {cls.colors.text_disabled};
            }}
        """
    
    @classmethod
    def get_combobox_style(cls) -> str:
        """Получить стиль выпадающего списка.
        
        Возвращает:
        -----------
        str
            CSS stylesheet
        """
        return f"""
            QComboBox {{
                background-color: {cls.colors.surface_1};
                color: {cls.colors.text_primary};
                border: 1px solid {cls.colors.border};
                border-radius: 8px;
                padding: 8px 30px 8px 12px;
                font-size: 14px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {cls.colors.primary};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 24px;
                border: none;
                border-left: 1px solid {cls.colors.border};
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background-color: transparent;
            }}
            QComboBox::down-arrow {{
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {cls.colors.text_secondary};
            }}
            QComboBox QAbstractItemView {{
                background-color: {cls.colors.surface_2};
                color: {cls.colors.text_primary};
                selection-background-color: {cls.colors.primary};
                selection-color: white;
                border: 1px solid {cls.colors.border};
                border-radius: 8px;
                outline: none;
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {cls.colors.surface_3};
            }}
        """
    
    @classmethod
    def get_progress_bar_style(cls, variant: str = "primary") -> str:
        """Получить стиль прогресс-бара.
        
        Параметры:
        ----------
        variant : str
            Вариант: primary, success, warning, error
            
        Возвращает:
        -----------
        str
            CSS stylesheet
        """
        gradient_map = {
            "primary": cls.get_gradient_css("primary"),
            "success": cls.get_gradient_css("success"),
            "warning": cls.get_gradient_css("warning"),
            "error": cls.get_gradient_css("error"),
        }
        
        return f"""
            QProgressBar {{
                background-color: {cls.colors.surface_1};
                border: none;
                border-radius: 4px;
                text-align: center;
                color: {cls.colors.text_secondary};
                font-size: 12px;
                min-height: 8px;
                max-height: 16px;
            }}
            QProgressBar::chunk {{
                background: {gradient_map.get(variant, gradient_map["primary"])};
                border-radius: 4px;
            }}
        """
    
    @classmethod
    def get_tab_widget_style(cls) -> str:
        """Получить стиль таб-виджета.
        
        Возвращает:
        -----------
        str
            CSS stylesheet
        """
        return f"""
            QTabWidget::pane {{
                background-color: {cls.colors.surface_1};
                border: 1px solid {cls.colors.border};
                border-radius: 12px;
                border-top-left-radius: 0px;
            }}
            
            QTabBar::tab {{
                background-color: {cls.colors.surface_2};
                color: {cls.colors.text_secondary};
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {cls.colors.surface_1};
                color: {cls.colors.text_primary};
                border-bottom: 2px solid {cls.colors.primary};
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {cls.colors.surface_3};
                color: {cls.colors.text_primary};
            }}
        """
    
    @classmethod
    def get_table_style(cls) -> str:
        """Получить стиль таблицы.
        
        Возвращает:
        -----------
        str
            CSS stylesheet
        """
        return f"""
            QTableWidget {{
                background-color: {cls.colors.surface_1};
                color: {cls.colors.text_primary};
                gridline-color: {cls.colors.border};
                border: 1px solid {cls.colors.border};
                border-radius: 8px;
            }}
            
            QTableWidget::item {{
                padding: 8px;
            }}
            
            QTableWidget::item:selected {{
                background-color: {cls.colors.primary};
                color: white;
            }}
            
            QTableWidget::item:hover {{
                background-color: {cls.colors.surface_3};
            }}
            
            QHeaderView::section {{
                background-color: {cls.colors.surface_2};
                color: {cls.colors.text_primary};
                padding: 10px;
                border: none;
                border-bottom: 1px solid {cls.colors.border};
                font-weight: 600;
            }}
        """
    
    @classmethod
    def get_scroll_area_style(cls) -> str:
        """Получить стиль scroll area.
        
        Возвращает:
        -----------
        str
            CSS stylesheet
        """
        return f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            
            QScrollBar:vertical {{
                background-color: {cls.colors.surface_1};
                width: 10px;
                border-radius: 5px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {cls.colors.surface_3};
                border-radius: 5px;
                min-height: 30px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {cls.colors.border_light};
            }}
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """
    
    @classmethod
    def get_group_box_style(cls) -> str:
        """Получить стиль group box.
        
        Возвращает:
        -----------
        str
            CSS stylesheet
        """
        return f"""
            QGroupBox {{
                color: {cls.colors.text_primary};
                font-weight: 600;
                border: 1px solid {cls.colors.border};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: {cls.colors.surface_1};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: {cls.colors.text_primary};
            }}
        """
    
    @classmethod
    def get_checkbox_style(cls) -> str:
        """Получить стиль чекбокса.
        
        Возвращает:
        -----------
        str
            CSS stylesheet
        """
        return f"""
            QCheckBox {{
                color: {cls.colors.text_primary};
                spacing: 8px;
                font-size: 14px;
            }}
            
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {cls.colors.border};
                border-radius: 4px;
                background-color: {cls.colors.surface_1};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {cls.colors.primary};
                border-color: {cls.colors.primary};
            }}
            
            QCheckBox::indicator:hover {{
                border-color: {cls.colors.primary};
            }}
        """


# =============================================================================
# ФУНКЦИЯ ПРИМЕНЕНИЯ СТИЛЕЙ
# =============================================================================

def apply_modern_style(widget: QWidget) -> None:
    """Применить современный стиль к виджету и всем дочерним элементам.
    
    Параметры:
    ----------
    widget : QWidget
        Виджет для стилизации
    """
    # Базовый stylesheet для всего приложения
    base_style = f"""
        /* Глобальные стили */
        QWidget {{
            background-color: {DesignSystem.colors.surface_1};
            color: {DesignSystem.colors.text_primary};
            font-family: {DesignSystem.typography.font_primary};
            font-size: {DesignSystem.typography.body_size}px;
        }}
        
        QMainWindow {{
            background-color: {DesignSystem.colors.surface_0};
        }}
        
        QLabel {{
            color: {DesignSystem.colors.text_primary};
            background: transparent;
        }}
        
        QToolTip {{
            background-color: {DesignSystem.colors.surface_2};
            color: {DesignSystem.colors.text_primary};
            border: 1px solid {DesignSystem.colors.border};
            border-radius: 6px;
            padding: 6px 10px;
        }}
        
        QMenu {{
            background-color: {DesignSystem.colors.surface_2};
            color: {DesignSystem.colors.text_primary};
            border: 1px solid {DesignSystem.colors.border};
            border-radius: 8px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 8px 24px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: {DesignSystem.colors.primary};
        }}
        
        QMessageBox {{
            background-color: {DesignSystem.colors.surface_1};
        }}
        
        QDialog {{
            background-color: {DesignSystem.colors.surface_1};
        }}
    """
    
    # Применяем базовый стиль
    current_style = widget.styleSheet()
    widget.setStyleSheet(base_style + "\n" + current_style)
    
    logger.info("Modern design system applied")


def get_global_stylesheet() -> str:
    """Получить глобальный stylesheet для приложения.
    
    Возвращает:
    -----------
    str
        CSS stylesheet для всего приложения
    """
    return f"""
        /* ===== ГЛОБАЛЬНЫЕ СТИЛИ ===== */
        
        QWidget {{
            background-color: {DesignSystem.colors.surface_1};
            color: {DesignSystem.colors.text_primary};
            font-family: {DesignSystem.typography.font_primary};
            font-size: {DesignSystem.typography.body_size}px;
        }}
        
        QMainWindow {{
            background-color: {DesignSystem.colors.surface_0};
        }}
        
        /* ===== ТЕКСТ ===== */
        
        QLabel {{
            color: {DesignSystem.colors.text_primary};
            background: transparent;
        }}
        
        QLabel[heading="true"] {{
            font-size: {DesignSystem.typography.h2_size}px;
            font-weight: {DesignSystem.typography.h2_weight};
            color: {DesignSystem.colors.text_primary};
        }}
        
        QLabel[muted="true"] {{
            color: {DesignSystem.colors.text_muted};
        }}
        
        /* ===== КНОПКИ ===== */
        
        {DesignSystem.get_button_style('primary').replace('QPushButton', 'QPushButton[variant="primary"]')}
        {DesignSystem.get_button_style('secondary').replace('QPushButton', 'QPushButton[variant="secondary"]')}
        {DesignSystem.get_button_style('ghost').replace('QPushButton', 'QPushButton[variant="ghost"]')}
        
        /* ===== ВВОД ===== */
        
        {DesignSystem.get_input_style()}
        {DesignSystem.get_combobox_style()}
        {DesignSystem.get_checkbox_style()}
        
        /* ===== ТАБЛИЦЫ ===== */
        
        {DesignSystem.get_table_style()}
        {DesignSystem.get_tab_widget_style()}
        
        /* ===== ПРОГРЕСС ===== */
        
        {DesignSystem.get_progress_bar_style()}
        
        /* ===== ГРУППЫ ===== */
        
        {DesignSystem.get_group_box_style()}
        
        /* ===== SCROLL ===== */
        
        {DesignSystem.get_scroll_area_style()}
        
        /* ===== ТУЛТИПЫ ===== */
        
        QToolTip {{
            background-color: {DesignSystem.colors.surface_2};
            color: {DesignSystem.colors.text_primary};
            border: 1px solid {DesignSystem.colors.border};
            border-radius: 6px;
            padding: 6px 10px;
        }}
        
        /* ===== FOCUS INDICATORS (Accessibility) ===== */
        
        QPushButton:focus,
        QLineEdit:focus,
        QComboBox:focus,
        QCheckBox:focus,
        QTableWidget:focus,
        QTabBar::tab:focus {{
            outline: 2px solid {DesignSystem.colors.primary};
            outline-offset: 2px;
        }}
        
        QPushButton:focus {{
            border: 2px solid {DesignSystem.colors.primary};
        }}
        
        QLineEdit:focus {{
            border: 2px solid {DesignSystem.colors.primary};
            background-color: {DesignSystem.colors.surface_1};
        }}
        
        QCheckBox::indicator:focus {{
            border: 2px solid {DesignSystem.colors.primary};
        }}
        
        /* ===== МЕНЮ ===== */
        
        QMenu {{
            background-color: {DesignSystem.colors.surface_2};
            color: {DesignSystem.colors.text_primary};
            border: 1px solid {DesignSystem.colors.border};
            border-radius: 8px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 8px 24px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: {DesignSystem.colors.primary};
        }}
        
        /* ===== ДИАЛОГИ ===== */
        
        QMessageBox {{
            background-color: {DesignSystem.colors.surface_1};
        }}
        
        QDialog {{
            background-color: {DesignSystem.colors.surface_1};
        }}
    """


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "DesignSystem",
    "ColorPalette",
    "GradientPalette",
    "ShadowPalette",
    "Typography",
    "Animation",
    "apply_modern_style",
    "get_global_stylesheet",
]
