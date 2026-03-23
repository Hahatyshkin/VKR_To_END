"""
Темы оформления для AudioAnalyzer.

Назначение:
- Светлая и тёмная темы
- Применение темы к виджетам
- Консистентные цвета для UI элементов

Использование:
--------------
>>> from ui_new.themes import ThemeManager, apply_theme
>>> 
>>> # Применить тёмную тему
>>> theme_manager = ThemeManager()
>>> theme_manager.apply_dark_theme(main_window)
>>> 
>>> # Переключить тему
>>> theme_manager.toggle_theme(main_window)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt

logger = logging.getLogger("ui_new.themes")


# =============================================================================
# ОПРЕДЕЛЕНИЯ ТЕМ
# =============================================================================

@dataclass(frozen=True)
class ThemeColors:
    """Цвета темы."""
    
    # Фоновые цвета
    background: str
    background_alt: str
    surface: str
    
    # Текст
    text: str
    text_secondary: str
    text_disabled: str
    
    # Акцентные цвета
    accent: str
    accent_hover: str
    accent_pressed: str
    
    # Статусные цвета
    success: str
    warning: str
    error: str
    info: str
    
    # Границы и разделители
    border: str
    divider: str
    
    # Графики
    chart_background: str
    chart_grid: str
    chart_text: str
    
    # Цвета для методов (графики)
    method_colors: Tuple[Tuple[int, int, int], ...] = field(default_factory=lambda: (
        (0, 0, 0),        # Исходный - черный
        (255, 0, 0),      # Красный
        (0, 128, 0),      # Зелёный
        (0, 0, 255),      # Синий
        (255, 165, 0),    # Оранжевый
        (128, 0, 128),    # Фиолетовый
        (0, 128, 128),    # Бирюзовый
        (255, 192, 203),  # Розовый
    ))


# Светлая тема
LIGHT_THEME = ThemeColors(
    background="#ffffff",
    background_alt="#f5f5f5",
    surface="#ffffff",
    text="#212121",
    text_secondary="#757575",
    text_disabled="#9e9e9e",
    accent="#0078d4",
    accent_hover="#106ebe",
    accent_pressed="#005a9e",
    success="#107c10",
    warning="#ff8c00",
    error="#d32f2f",
    info="#0078d4",
    border="#e0e0e0",
    divider="#bdbdbd",
    chart_background="#ffffff",
    chart_grid="#e0e0e0",
    chart_text="#212121",
)

# Тёмная тема
DARK_THEME = ThemeColors(
    background="#1e1e1e",
    background_alt="#2d2d2d",
    surface="#252526",
    text="#e0e0e0",
    text_secondary="#9e9e9e",
    text_disabled="#616161",
    accent="#60a5fa",
    accent_hover="#93c5fd",
    accent_pressed="#3b82f6",
    success="#4ade80",
    warning="#fbbf24",
    error="#f87171",
    info="#60a5fa",
    border="#404040",
    divider="#333333",
    chart_background="#1e1e1e",
    chart_grid="#333333",
    chart_text="#e0e0e0",
    method_colors=(
        (200, 200, 200),  # Исходный - светло-серый
        (239, 68, 68),    # Красный
        (34, 197, 94),    # Зелёный
        (59, 130, 246),   # Синий
        (249, 115, 22),   # Оранжевый
        (168, 85, 247),   # Фиолетовый
        (20, 184, 166),   # Бирюзовый
        (244, 114, 182),  # Розовый
    ),
)


# =============================================================================
# МЕНЕДЖЕР ТЕМ
# =============================================================================

class ThemeManager:
    """Менеджер тем оформления.
    
    Предоставляет:
    - Применение светлой/тёмной темы
    - Переключение между темами
    - Получение текущих цветов
    
    Атрибуты:
    ----------
    current_theme : str
        Текущая тема ('light' или 'dark')
    colors : ThemeColors
        Цвета текущей темы
    """
    
    THEMES = {
        'light': LIGHT_THEME,
        'dark': DARK_THEME,
    }
    
    def __init__(self, initial_theme: str = 'light'):
        """Инициализация менеджера тем.
        
        Параметры:
        ----------
        initial_theme : str
            Начальная тема ('light' или 'dark')
        """
        self._current_theme = initial_theme
        self._colors = self.THEMES.get(initial_theme, LIGHT_THEME)
        logger.debug(f"ThemeManager initialized with theme: {initial_theme}")
    
    @property
    def current_theme(self) -> str:
        """Текущая тема."""
        return self._current_theme
    
    @property
    def colors(self) -> ThemeColors:
        """Цвета текущей темы."""
        return self._colors
    
    def get_method_color(self, index: int) -> Tuple[int, int, int]:
        """Получить цвет для метода по индексу.
        
        Параметры:
        ----------
        index : int
            Индекс метода
            
        Возвращает:
        -----------
        Tuple[int, int, int]
            RGB цвет
        """
        colors = self._colors.method_colors
        return colors[index % len(colors)]
    
    def apply_light_theme(self, widget: QWidget) -> None:
        """Применить светлую тему к виджету.
        
        Параметры:
        ----------
        widget : QWidget
            Виджет для применения темы
        """
        self._apply_theme(widget, 'light')
    
    def apply_dark_theme(self, widget: QWidget) -> None:
        """Применить тёмную тему к виджету.
        
        Параметры:
        ----------
        widget : QWidget
            Виджет для применения темы
        """
        self._apply_theme(widget, 'dark')
    
    def toggle_theme(self, widget: QWidget) -> str:
        """Переключить тему.
        
        Параметры:
        ----------
        widget : QWidget
            Виджет для применения темы
            
        Возвращает:
        -----------
        str
            Новая тема
        """
        new_theme = 'dark' if self._current_theme == 'light' else 'light'
        self._apply_theme(widget, new_theme)
        return new_theme
    
    def _apply_theme(self, widget: QWidget, theme: str) -> None:
        """Применить тему к виджету.
        
        Параметры:
        ----------
        widget : QWidget
            Виджет для применения темы
        theme : str
            Имя темы ('light' или 'dark')
        """
        colors = self.THEMES.get(theme, LIGHT_THEME)
        self._current_theme = theme
        self._colors = colors
        
        # Генерируем stylesheet
        stylesheet = self._generate_stylesheet(colors)
        
        try:
            widget.setStyleSheet(stylesheet)
            logger.info(f"Applied {theme} theme")
        except Exception as e:
            logger.error(f"Error applying theme: {e}")
    
    def _generate_stylesheet(self, colors: ThemeColors) -> str:
        """Сгенерировать stylesheet из цветов темы.
        
        Параметры:
        ----------
        colors : ThemeColors
            Цвета темы
            
        Возвращает:
        -----------
        str
            Stylesheet строка
        """
        return f"""
            /* Основные виджеты */
            QWidget {{
                background-color: {colors.background};
                color: {colors.text};
            }}
            
            /* QMainWindow */
            QMainWindow {{
                background-color: {colors.background};
            }}
            
            /* QLabel */
            QLabel {{
                color: {colors.text};
                background: transparent;
            }}
            
            /* QLineEdit */
            QLineEdit {{
                background-color: {colors.surface};
                color: {colors.text};
                border: 1px solid {colors.border};
                padding: 4px 8px;
                border-radius: 4px;
            }}
            
            QLineEdit:focus {{
                border-color: {colors.accent};
            }}
            
            QLineEdit:read-only {{
                background-color: {colors.background_alt};
            }}
            
            /* QPushButton */
            QPushButton {{
                background-color: {colors.surface};
                color: {colors.text};
                border: 1px solid {colors.border};
                padding: 6px 16px;
                border-radius: 4px;
            }}
            
            QPushButton:hover {{
                background-color: {colors.background_alt};
                border-color: {colors.accent};
            }}
            
            QPushButton:pressed {{
                background-color: {colors.accent};
                color: white;
            }}
            
            QPushButton:disabled {{
                background-color: {colors.background_alt};
                color: {colors.text_disabled};
            }}
            
            /* Primary button */
            QPushButton[primary="true"] {{
                background-color: {colors.accent};
                color: white;
                border: none;
            }}
            
            QPushButton[primary="true"]:hover {{
                background-color: {colors.accent_hover};
            }}
            
            /* QComboBox */
            QComboBox {{
                background-color: {colors.surface};
                color: {colors.text};
                border: 1px solid {colors.border};
                padding: 4px 24px 4px 8px;
                border-radius: 4px;
            }}
            
            QComboBox:hover {{
                border-color: {colors.accent};
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
                background-color: transparent;
            }}
            
            QComboBox::down-arrow {{
                width: 0px;
                height: 0px;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {colors.text};
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {colors.surface};
                color: {colors.text};
                selection-background-color: {colors.accent};
                selection-color: white;
                border: 1px solid {colors.border};
                border-radius: 4px;
                outline: none;
            }}
            
            /* QCheckBox */
            QCheckBox {{
                color: {colors.text};
                spacing: 8px;
            }}
            
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {colors.border};
                border-radius: 3px;
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {colors.accent};
                border-color: {colors.accent};
            }}
            
            /* QTableWidget */
            QTableWidget {{
                background-color: {colors.surface};
                color: {colors.text};
                gridline-color: {colors.divider};
                border: 1px solid {colors.border};
            }}
            
            QTableWidget::item {{
                padding: 4px;
            }}
            
            QTableWidget::item:selected {{
                background-color: {colors.accent};
                color: white;
            }}
            
            QHeaderView::section {{
                background-color: {colors.background_alt};
                color: {colors.text};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {colors.border};
            }}
            
            /* QTabWidget */
            QTabWidget::pane {{
                border: 1px solid {colors.border};
                background-color: {colors.surface};
            }}
            
            QTabBar::tab {{
                background-color: {colors.background_alt};
                color: {colors.text};
                padding: 8px 16px;
                border: 1px solid {colors.border};
            }}
            
            QTabBar::tab:selected {{
                background-color: {colors.surface};
                border-bottom: 2px solid {colors.accent};
            }}
            
            QTabBar::tab:hover {{
                background-color: {colors.surface};
            }}
            
            /* QProgressBar */
            QProgressBar {{
                background-color: {colors.background_alt};
                color: {colors.text};
                border: 1px solid {colors.border};
                border-radius: 4px;
                text-align: center;
            }}
            
            QProgressBar::chunk {{
                background-color: {colors.accent};
                border-radius: 3px;
            }}
            
            /* QPlainTextEdit */
            QPlainTextEdit {{
                background-color: {colors.surface};
                color: {colors.text};
                border: 1px solid {colors.border};
            }}
            
            /* QScrollBar */
            QScrollBar:vertical {{
                background-color: {colors.background_alt};
                width: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {colors.text_secondary};
                border-radius: 6px;
                min-height: 30px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {colors.text};
            }}
            
            /* QSplitter */
            QSplitter::handle {{
                background-color: {colors.divider};
            }}
            
            /* QMessageBox */
            QMessageBox {{
                background-color: {colors.surface};
            }}
            
            /* QMenu */
            QMenu {{
                background-color: {colors.surface};
                color: {colors.text};
                border: 1px solid {colors.border};
            }}
            
            QMenu::item:selected {{
                background-color: {colors.accent};
                color: white;
            }}
        """


# =============================================================================
# ФУНКЦИИ ПРИМЕНЕНИЯ ТЕМЫ
# =============================================================================

def apply_theme(widget: QWidget, theme: str = 'light') -> ThemeManager:
    """Применить тему к виджету.
    
    Параметры:
    ----------
    widget : QWidget
        Виджет для применения темы
    theme : str
        Имя темы ('light' или 'dark')
        
    Возвращает:
    -----------
    ThemeManager
        Менеджер тем
    """
    manager = ThemeManager(theme)
    manager._apply_theme(widget, theme)
    return manager


def get_theme_colors(theme: str = 'light') -> ThemeColors:
    """Получить цвета темы.
    
    Параметры:
    ----------
    theme : str
        Имя темы ('light' или 'dark')
        
    Возвращает:
    -----------
    ThemeColors
        Цвета темы
    """
    return ThemeManager.THEMES.get(theme, LIGHT_THEME)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "ThemeManager",
    "ThemeColors",
    "LIGHT_THEME",
    "DARK_THEME",
    "apply_theme",
    "get_theme_colors",
]
