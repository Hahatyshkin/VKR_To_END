# План доработки AudioAnalyzer — Детальные планы реализации

**Версия:** 1.0  
**Дата:** Март 2025  
**Статус:** На согласовании

---

## Содержание

1. [План архитектурных улучшений](#1-план-архитектурных-улучшений)
2. [План UI/UX улучшений](#2-план-uiux-улучшений)
3. [План нового функционала](#3-план-нового-функционала)
4. [План тестирования и качества](#4-план-тестирования-и-качества)
5. [План производительности](#5-план-производительности)
6. [Сводный план и оценки](#6-сводный-план-и-оценки)

---

## 1. План архитектурных улучшений

### 1.1 Рефакторинг миксинов (разделение UI и логики)

**Проблема:** Миксины содержат смешанный код UI и бизнес-логики

**Решение:** Вынести бизнес-логику в отдельные сервисы

#### Этапы реализации:

```
Этап 1: Создание слоя сервисов (2 дня)
├── Создать src/services/__init__.py
├── Создать src/services/spectrum_service.py
├── Создать src/services/player_service.py
├── Создать src/services/processing_service.py
└── Создать src/services/file_service.py

Этап 2: Рефакторинг SpectrumMixin (1 день)
├── Перенести _build_interactive_spectrum() → SpectrumService
├── Перенести вычисление спектров → SpectrumService
├── Оставить в миксине только UI код
└── Добавить делегирование вызовов сервису

Этап 3: Рефакторинг остальных миксинов (2 дня)
├── PlayerMixin → PlayerService
├── WorkerMixin → ProcessingService
└── FilesMixin → FileService

Этап 4: Тестирование (1 день)
└── Проверить работоспособность всех функций
```

#### Структура нового кода:

```python
# src/services/spectrum_service.py
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np

@dataclass
class SpectrumResult:
    """Результат вычисления спектра."""
    name: str
    frequencies: np.ndarray
    amplitudes_db: np.ndarray

class SpectrumService:
    """Сервис для спектрального анализа."""
    
    def __init__(self, log_callback=None):
        self._log = log_callback
    
    def compute_spectrum(
        self, 
        audio_path: str, 
        max_points: int = 2000
    ) -> SpectrumResult:
        """Вычислить спектр аудиофайла."""
        ...
    
    def compare_spectra(
        self,
        source_path: str,
        target_paths: List[Tuple[str, str]]
    ) -> List[SpectrumResult]:
        """Сравнить спектры нескольких файлов."""
        ...

# src/ui_new/mixins/spectrum_mixin.py (после рефакторинга)
class SpectrumMixin:
    """Только UI код для спектра."""
    
    def _build_spectrum_tab(self) -> Tuple[QWidget, Dict]:
        """Построить UI вкладки спектра."""
        ...  # Только создание виджетов
    
    def on_compare_spectrum(self) -> None:
        """Обработчик кнопки сравнения."""
        # Делегирование сервису
        self._spectrum_service.compare_spectra(
            source=self.spectrum_source_edit.text(),
            targets=self._get_selected_files()
        )
```

**Оценка времени:** 6 дней  
**Риск:** Средний (требует тщательного тестирования)  
**Приоритет:** 🔴 Высокий

---

### 1.2 Внедрение Dependency Injection

**Проблема:** Жёсткие зависимости затрудняют тестирование

**Решение:** Создать простой DI контейнер

#### Этапы реализации:

```
Этап 1: Создание DI контейнера (1 день)
├── Создать src/core/container.py
├── Создать src/core/interfaces.py (Protocol классы)
└── Создать src/core/providers.py

Этап 2: Определение интерфейсов (1 день)
├── IAudioLoader - загрузка аудио
├── IAudioEncoder - кодирование в MP3
├── IMetricsCalculator - расчёт метрик
├── IFileRepository - работа с файлами
└── IConfiguration - конфигурация

Этап 3: Регистрация сервисов (0.5 дня)
└── Настроить контейнер в app.py

Этап 4: Рефакторинг для использования DI (1.5 дня)
└── Заменить прямые импорты на инъекцию
```

#### Пример реализации:

```python
# src/core/interfaces.py
from typing import Protocol, Tuple
import numpy as np

class IAudioLoader(Protocol):
    """Интерфейс загрузки аудио."""
    
    def load_wav(self, path: str) -> Tuple[np.ndarray, int]:
        """Загрузить WAV файл."""
        ...

class IMetricsCalculator(Protocol):
    """Интерфейс калькулятора метрик."""
    
    def compute_all(
        self, 
        reference: np.ndarray, 
        test: np.ndarray,
        sr_ref: int,
        sr_test: int
    ) -> dict:
        """Вычислить все метрики."""
        ...

# src/core/container.py
from typing import Dict, Type, Any, Callable

class DIContainer:
    """Простой DI контейнер."""
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
    
    def register_instance(self, interface: Type, instance: Any) -> None:
        """Зарегистрировать экземпляр."""
        self._services[interface] = instance
    
    def register_factory(
        self, 
        interface: Type, 
        factory: Callable[['DIContainer'], Any]
    ) -> None:
        """Зарегистрировать фабрику."""
        self._factories[interface] = factory
    
    def resolve(self, interface: Type) -> Any:
        """Получить экземпляр сервиса."""
        if interface in self._services:
            return self._services[interface]
        if interface in self._factories:
            instance = self._factories[interface](self)
            self._services[interface] = instance
            return instance
        raise ValueError(f"Service {interface} not registered")

# Инициализация в app.py
def create_container() -> DIContainer:
    container = DIContainer()
    
    # Регистрация сервисов
    container.register_factory(IAudioLoader, 
        lambda c: AudioLoader())
    container.register_factory(IMetricsCalculator,
        lambda c: MetricsCalculator())
    
    return container
```

**Оценка времени:** 4 дня  
**Риск:** Низкий  
**Приоритет:** 🟡 Средний

---

### 1.3 Централизация конфигурации

**Проблема:** Пути и настройки разбросаны по коду

**Решение:** Единый конфигурационный модуль

#### Этапы реализации:

```
Этап 1: Создание конфигурации (0.5 дня)
├── Создать src/core/config.py
└── Перенести все константы

Этап 2: Поддержка профилей (0.5 дня)
├── Добавить загрузку из JSON/YAML
└── Добавить валидацию

Этап 3: Интеграция (0.5 дня)
└── Заменить все обращения к константам
```

#### Пример реализации:

```python
# src/core/config.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
import json
import os

@dataclass
class PathConfig:
    """Конфигурация путей."""
    project_root: Path
    output_dir: Path
    test_data_dir: Path
    log_dir: Path
    
    @classmethod
    def create(cls) -> 'PathConfig':
        project_root = Path(__file__).parent.parent.parent.resolve()
        return cls(
            project_root=project_root,
            output_dir=project_root / "output",
            test_data_dir=project_root / "default_test_data",
            log_dir=project_root / "logs"
        )

@dataclass
class ProcessingConfig:
    """Конфигурация обработки."""
    default_block_size: int = 2048
    default_bitrate: str = "192k"
    default_select_mode: str = "energy"
    default_keep_energy: float = 0.95
    max_workers: int = 4
    
@dataclass
class UIConfig:
    """Конфигурация UI."""
    window_width: int = 1100
    window_height: int = 650
    theme: str = "light"
    show_logs_by_default: bool = True
    spectrum_max_points: int = 2000

@dataclass
class AppConfig:
    """Главная конфигурация приложения."""
    paths: PathConfig
    processing: ProcessingConfig
    ui: UIConfig
    
    @classmethod
    def create(cls) -> 'AppConfig':
        return cls(
            paths=PathConfig.create(),
            processing=ProcessingConfig(),
            ui=UIConfig()
        )
    
    @classmethod
    def load(cls, path: str) -> 'AppConfig':
        """Загрузить конфигурацию из файла."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(
            paths=PathConfig(**data.get('paths', {})),
            processing=ProcessingConfig(**data.get('processing', {})),
            ui=UIConfig(**data.get('ui', {}))
        )
    
    def save(self, path: str) -> None:
        """Сохранить конфигурацию в файл."""
        data = {
            'paths': self.paths.__dict__,
            'processing': self.processing.__dict__,
            'ui': self.ui.__dict__
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

# Глобальный экземпляр
config = AppConfig.create()
```

**Оценка времени:** 1.5 дня  
**Риск:** Низкий  
**Приоритет:** 🔴 Высокий

---

## 2. План UI/UX улучшений

### 2.1 Визуальная иерархия кнопок

**Проблема:** Все кнопки визуально равнозначны

**Решение:** Внедрить систему стилей для primary/secondary/tertiary кнопок

#### Этапы реализации:

```
Этап 1: Создание системы стилей (1 день)
├── Создать src/ui_new/styles/buttons.py
├── Определить стили для Primary, Secondary, Danger
└── Создать кастомные кнопки с применением стилей

Этап 2: Применение к существующим кнопкам (0.5 дня)
└── Заменить QPushButton на стилизованные
```

#### Пример реализации:

```python
# src/ui_new/styles/buttons.py
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

class ButtonStyle:
    """Стили кнопок."""
    
    PRIMARY = """
        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QPushButton:disabled {
            background-color: #a0a0a0;
        }
    """
    
    SECONDARY = """
        QPushButton {
            background-color: transparent;
            color: #0078d4;
            border: 1px solid #0078d4;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #f0f8ff;
        }
        QPushButton:pressed {
            background-color: #e0f0ff;
        }
    """
    
    DANGER = """
        QPushButton {
            background-color: #d13438;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #b02a2e;
        }
    """
    
    TEXT = """
        QPushButton {
            background-color: transparent;
            color: #666666;
            border: none;
            padding: 8px 12px;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #f0f0f0;
            color: #0078d4;
        }
    """

class PrimaryButton(QPushButton):
    """Primary кнопка - главное действие."""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(ButtonStyle.PRIMARY)
        self.setCursor(Qt.PointingHandCursor)

class SecondaryButton(QPushButton):
    """Secondary кнопка - вторичное действие."""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(ButtonStyle.SECONDARY)
        self.setCursor(Qt.PointingHandCursor)

class DangerButton(QPushButton):
    """Danger кнопка - опасное действие."""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(ButtonStyle.DANGER)
        self.setCursor(Qt.PointingHandCursor)

# Использование в main_window.py:
self.btn_convert = PrimaryButton("▶ Запустить")
self.btn_export_xlsx = SecondaryButton("📄 Экспорт в Excel")
self.btn_clear_output = DangerButton("🗑️ Очистить output")
```

**Оценка времени:** 1.5 дня  
**Риск:** Низкий  
**Приоритет:** 🔴 Высокий

---

### 2.2 Feedback при длительных операциях

**Проблема:** Пользователь не видит прогресс операций

**Решение:** Добавить анимированные индикаторы и детальный прогресс

#### Этапы реализации:

```
Этап 1: Создание компонентов прогресса (1 день)
├── Создать src/ui_new/widgets/progress_overlay.py
├── Анимированный спиннер
├── Оверлей с прогрессом
└── Детальный статус операции

Этап 2: Интеграция в Worker (1 день)
├── Добавить сигнал current_operation
├── Добавить сигнал estimated_time
└── Обновить UI при получении сигналов
```

#### Пример реализации:

```python
# src/ui_new/widgets/progress_overlay.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QPen, QColor

class CircularProgress(QWidget):
    """Анимированный круговой прогресс."""
    
    def __init__(self, size: int = 60, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(30)
    
    def _rotate(self):
        self._angle = (self._angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(QColor("#0078d4"), 3)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.drawArc(rect, self._angle * 16, 270 * 16)

class ProgressOverlay(QWidget):
    """Оверлей с прогрессом операции."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 150);")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Спиннер
        self.spinner = CircularProgress(60)
        layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        
        # Текст операции
        self.operation_label = QLabel("Обработка...")
        self.operation_label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(self.operation_label, alignment=Qt.AlignCenter)
        
        # Прогресс бар
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedWidth(200)
        self.progress.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 50);
                border: none;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: #0078d4;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress, alignment=Qt.AlignCenter)
        
        # ETA
        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(self.eta_label, alignment=Qt.AlignCenter)
    
    def set_operation(self, text: str) -> None:
        self.operation_label.setText(text)
    
    def set_progress(self, value: int) -> None:
        self.progress.setValue(value)
    
    def set_eta(self, text: str) -> None:
        self.eta_label.setText(f"Осталось: {text}")

# Использование в main_window.py:
def _on_worker_status(self, status: str) -> None:
    self.progress_overlay.set_operation(status)

def _on_worker_progress(self, value: int) -> None:
    self.progress_overlay.set_progress(value)
```

**Оценка времени:** 2 дня  
**Риск:** Низкий  
**Приоритет:** 🔴 Высокий

---

### 2.3 Тёмная тема

**Проблема:** Нет переключения между темами

**Решение:** Система тем с переключателем

#### Этапы реализации:

```
Этап 1: Создание системы тем (1 день)
├── Создать src/ui_new/styles/themes.py
├── Определить палитры Light и Dark
└── Создать ThemeManager

Этап 2: Применение темы (1 день)
├── Добавить переключатель в настройки
├── Применить тему ко всем виджетам
└── Сохранять выбор в конфигурации
```

#### Пример реализации:

```python
# src/ui_new/styles/themes.py
from dataclasses import dataclass
from typing import Dict

@dataclass
class ColorScheme:
    """Цветовая схема."""
    background: str
    background_alt: str
    text: str
    text_secondary: str
    accent: str
    accent_hover: str
    border: str
    success: str
    warning: str
    error: str

class Theme:
    """Тема оформления."""
    
    LIGHT = ColorScheme(
        background="#ffffff",
        background_alt="#f5f5f5",
        text="#1a1a1a",
        text_secondary="#666666",
        accent="#0078d4",
        accent_hover="#106ebe",
        border="#e0e0e0",
        success="#107c10",
        warning="#ffb900",
        error="#d13438"
    )
    
    DARK = ColorScheme(
        background="#1e1e1e",
        background_alt="#2d2d2d",
        text="#ffffff",
        text_secondary="#b0b0b0",
        accent="#60a5fa",
        accent_hover="#3b82f6",
        border="#404040",
        success="#4ade80",
        warning="#fbbf24",
        error="#f87171"
    )

class ThemeManager:
    """Менеджер тем."""
    
    def __init__(self):
        self._current_theme = Theme.LIGHT
        self._listeners = []
    
    def set_theme(self, theme_name: str) -> None:
        if theme_name == "dark":
            self._current_theme = Theme.DARK
        else:
            self._current_theme = Theme.LIGHT
        self._notify_listeners()
    
    def get_stylesheet(self) -> str:
        c = self._current_theme
        return f"""
            QWidget {{
                background-color: {c.background};
                color: {c.text};
            }}
            QTableWidget {{
                background-color: {c.background};
                alternate-background-color: {c.background_alt};
                gridline-color: {c.border};
            }}
            QLineEdit {{
                background-color: {c.background_alt};
                border: 1px solid {c.border};
                padding: 6px;
                color: {c.text};
            }}
            QComboBox {{
                background-color: {c.background_alt};
                border: 1px solid {c.border};
                padding: 6px;
                color: {c.text};
            }}
            QTabWidget::pane {{
                border: 1px solid {c.border};
            }}
            QTabBar::tab {{
                background-color: {c.background_alt};
                color: {c.text};
                padding: 8px 16px;
                border: 1px solid {c.border};
            }}
            QTabBar::tab:selected {{
                background-color: {c.background};
                border-bottom-color: {c.background};
            }}
            QScrollBar:vertical {{
                background-color: {c.background_alt};
                width: 12px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {c.border};
                border-radius: 6px;
            }}
        """
    
    def register_listener(self, callback) -> None:
        self._listeners.append(callback)
    
    def _notify_listeners(self) -> None:
        for callback in self._listeners:
            callback(self._current_theme)

# Глобальный менеджер
theme_manager = ThemeManager()

# Использование:
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        theme_manager.register_listener(self._on_theme_changed)
        self.setStyleSheet(theme_manager.get_stylesheet())
    
    def _on_theme_changed(self, theme: ColorScheme):
        self.setStyleSheet(theme_manager.get_stylesheet())
```

**Оценка времени:** 2 дня  
**Риск:** Низкий  
**Приоритет:** 🟡 Средний

---

### 2.4 Контекстное меню таблицы результатов

**Проблема:** Нет быстрых действий над результатами

**Решение:** Добавить контекстное меню с действиями

#### Этапы реализации:

```
Этап 1: Создание контекстного меню (1 день)
├── Копировать значение ячейки
├── Копировать строку
├── Открыть файл
├── Открыть папку
├── Воспроизвести файл
└── Показать в спектре

Этап 2: Интеграция (0.5 дня)
└── Подключить к таблице результатов
```

#### Пример реализации:

```python
# src/ui_new/widgets/results_table.py
from PySide6.QtWidgets import QTableWidget, QMenu, QApplication
from PySide6.QtCore import Qt, Signal
import os
import subprocess
import platform

class ResultsTable(QTableWidget):
    """Таблица результатов с контекстным меню."""
    
    open_file_requested = Signal(str)
    play_file_requested = Signal(str)
    show_in_spectrum_requested = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item:
            return
        
        row = item.row()
        path_item = self.item(row, 12)  # Колонка "Путь"
        if not path_item:
            return
        
        file_path = path_item.text()
        
        menu = QMenu(self)
        
        # Копирование
        copy_value = menu.addAction("📋 Копировать значение")
        copy_row = menu.addAction("📄 Копировать строку")
        menu.addSeparator()
        
        # Файловые операции
        open_file = menu.addAction("🎵 Открыть файл")
        open_folder = menu.addAction("📁 Открыть папку")
        play_file = menu.addAction("▶ Воспроизвести")
        menu.addSeparator()
        
        # Анализ
        show_spectrum = menu.addAction("📊 Показать в спектре")
        
        action = menu.exec(self.viewport().mapToGlobal(pos))
        
        if action == copy_value:
            QApplication.clipboard().setText(item.text())
        elif action == copy_row:
            row_data = [self.item(row, col).text() for col in range(self.columnCount())]
            QApplication.clipboard().setText("\t".join(row_data))
        elif action == open_file:
            self._open_file_in_system(file_path)
        elif action == open_folder:
            self._open_folder_in_system(file_path)
        elif action == play_file:
            self.play_file_requested.emit(file_path)
        elif action == show_spectrum:
            self.show_in_spectrum_requested.emit(file_path)
    
    def _open_file_in_system(self, path: str) -> None:
        """Открыть файл в системном приложении."""
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    
    def _open_folder_in_system(self, path: str) -> None:
        """Открыть папку в файловом менеджере."""
        folder = os.path.dirname(path)
        if platform.system() == "Windows":
            subprocess.run(["explorer", folder])
        elif platform.system() == "Darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])
```

**Оценка времени:** 1.5 дня  
**Риск:** Низкий  
**Приоритет:** 🟡 Средний

---

## 3. План нового функционала

### 3.1 Рекомендательная система методов

**Описание:** Автоматический выбор оптимального метода на основе характеристик аудио

#### Этапы реализации:

```
Этап 1: Анализ аудио характеристик (2 дня)
├── Создать src/processing/audio_analyzer.py
├── Duration detection
├── Dynamic range calculation
├── Spectral centroid
├── Zero crossing rate
├── Energy distribution
└── Voice/Music classification

Этап 2: Система правил рекомендаций (2 дня)
├── Создать src/services/recommender_service.py
├── Определить правила для каждого типа аудио
├── Весовые коэффициенты для метрик
└── Механизм ранжирования

Этап 3: UI интеграция (1 день)
├── Добавить вкладку "Рекомендации"
├── Показать анализ файла
├── Показать рекомендуемые методы
└── Кнопка "Применить рекомендацию"
```

#### Пример реализации:

```python
# src/processing/audio_analyzer.py
from dataclasses import dataclass
from typing import Tuple
import numpy as np

@dataclass
class AudioCharacteristics:
    """Характеристики аудиофайла."""
    duration_sec: float
    sample_rate: int
    channels: int
    dynamic_range_db: float
    spectral_centroid_hz: float
    spectral_rolloff_hz: float
    zero_crossing_rate: float
    rms_energy: float
    peak_amplitude: float
    is_likely_speech: bool
    is_likely_music: bool

class AudioAnalyzer:
    """Анализатор характеристик аудио."""
    
    def analyze(self, audio_path: str) -> AudioCharacteristics:
        """Проанализировать аудиофайл."""
        signal, sr = self._load_audio(audio_path)
        
        duration = len(signal) / sr
        dynamic_range = self._calc_dynamic_range(signal)
        centroid = self._calc_spectral_centroid(signal, sr)
        rolloff = self._calc_spectral_rolloff(signal, sr)
        zcr = self._calc_zero_crossing_rate(signal)
        rms = np.sqrt(np.mean(signal ** 2))
        peak = np.max(np.abs(signal))
        
        # Классификация тип контента
        is_speech = self._classify_speech(centroid, zcr, dynamic_range)
        is_music = not is_speech and centroid > 1000
        
        return AudioCharacteristics(
            duration_sec=duration,
            sample_rate=sr,
            channels=1,  # После моно-конверсии
            dynamic_range_db=dynamic_range,
            spectral_centroid_hz=centroid,
            spectral_rolloff_hz=rolloff,
            zero_crossing_rate=zcr,
            rms_energy=rms,
            peak_amplitude=peak,
            is_likely_speech=is_speech,
            is_likely_music=is_music
        )
    
    def _calc_dynamic_range(self, signal: np.ndarray) -> float:
        """Вычислить динамический диапазон в дБ."""
        rms = np.sqrt(np.mean(signal ** 2))
        peak = np.max(np.abs(signal))
        if rms > 0:
            return 20 * np.log10(peak / rms)
        return 0.0
    
    def _calc_spectral_centroid(self, signal: np.ndarray, sr: int) -> float:
        """Вычислить спектральный центроид."""
        fft = np.abs(np.fft.rfft(signal))
        freqs = np.fft.rfftfreq(len(signal), 1/sr)
        return float(np.sum(freqs * fft) / (np.sum(fft) + 1e-10))
    
    def _classify_speech(self, centroid: float, zcr: float, dr: float) -> bool:
        """Классифицировать как речь."""
        # Речь обычно имеет:
        # - Низкий центроид (< 4000 Hz)
        # - Средний ZCR
        # - Ограниченный динамический диапазон
        return centroid < 4000 and 0.02 < zcr < 0.15

# src/services/recommender_service.py
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class MethodRecommendation:
    """Рекомендация метода."""
    method: str
    score: float
    reason: str

class RecommenderService:
    """Сервис рекомендаций методов."""
    
    # Правила рекомендаций
    RULES = {
        'speech': {
            'preferred': ['fwht', 'huffman'],
            'reason': 'Речь: оптимальны быстрые методы с компандированием'
        },
        'music_high_quality': {
            'preferred': ['dct', 'fft'],
            'reason': 'Музыка: высокое качество через спектральные методы'
        },
        'speech_fast': {
            'preferred': ['fwht', 'standard'],
            'reason': 'Быстрая обработка речи'
        },
        'bass_heavy': {
            'preferred': ['dwt'],
            'reason': 'Низкочастотный контент: хорошее разрешение DWT'
        },
        'short_file': {
            'preferred': ['fwht', 'huffman', 'standard'],
            'reason': 'Короткий файл: быстрые методы'
        },
    }
    
    def recommend(self, characteristics: AudioCharacteristics) -> List[MethodRecommendation]:
        """Получить рекомендации по методам."""
        scores = {}
        reasons = {}
        
        # Речь
        if characteristics.is_likely_speech:
            for m in ['fwht', 'huffman']:
                scores[m] = scores.get(m, 0) + 0.3
                reasons[m] = self.RULES['speech']['reason']
        
        # Музыка
        if characteristics.is_likely_music:
            for m in ['dct', 'fft']:
                scores[m] = scores.get(m, 0) + 0.25
                reasons[m] = self.RULES['music_high_quality']['reason']
        
        # Короткий файл - скорость
        if characteristics.duration_sec < 10:
            for m in ['fwht', 'huffman', 'standard']:
                scores[m] = scores.get(m, 0) + 0.2
        
        # Высокий динамический диапазон
        if characteristics.dynamic_range_db > 30:
            scores['huffman'] = scores.get('huffman', 0) + 0.2
            reasons['huffman'] = 'Высокий DR: μ-law сжимает диапазон'
        
        # Низкочастотный контент
        if characteristics.spectral_centroid_hz < 2000:
            scores['dwt'] = scores.get('dwt', 0) + 0.2
            reasons['dwt'] = self.RULES['bass_heavy']['reason']
        
        # Стандартный всегда доступен
        scores['standard'] = scores.get('standard', 0) + 0.1
        
        # Ранжирование
        recommendations = [
            MethodRecommendation(
                method=m,
                score=s,
                reason=reasons.get(m, 'Баланс качества и скорости')
            )
            for m, s in scores.items()
        ]
        
        return sorted(recommendations, key=lambda x: x.score, reverse=True)
```

**Оценка времени:** 5 дней  
**Риск:** Средний  
**Приоритет:** 🟡 Средний

---

### 3.2 CLI интерфейс

**Описание:** Командная строка для автоматизации и batch-обработки

#### Этапы реализации:

```
Этап 1: Создание CLI структуры (1 день)
├── Создать src/cli/__init__.py
├── Создать src/cli/main.py
└── Добавить click в requirements

Этап 2: Реализация команд (2 дня)
├── process - обработка файлов
├── analyze - анализ файла
├── compare - сравнение методов
├── export - экспорт результатов
└── config - управление конфигурацией

Этап 3: Интеграция (0.5 дня)
├── Точка входа __main__.py
└── Документация в README
```

#### Пример реализации:

```python
# src/cli/main.py
import click
from pathlib import Path
from typing import List
import json

@click.group()
@click.version_option('1.0.0')
def cli():
    """
    AudioAnalyzer CLI - Инструмент анализа аудио методов.
    
    Примеры:
        audioanalyzer process -i audio.wav -o ./output
        audioanalyzer analyze audio.wav
        audioanalyzer compare results.json
    """
    pass

@cli.command()
@click.option('--input', '-i', required=True, 
              help='Входной WAV файл или папка')
@click.option('--output', '-o', required=True,
              help='Выходная папка для MP3')
@click.option('--methods', '-m', multiple=True,
              default=['all'],
              help='Методы: fwht, fft, dct, dwt, huffman, rosenbrock, standard, all')
@click.option('--bitrate', '-b', default='192k',
              help='Битрейт MP3 (default: 192k)')
@click.option('--parallel', '-p', is_flag=True,
              help='Параллельная обработка методов')
@click.option('--quiet', '-q', is_flag=True,
              help='Тихий режим')
def process(input, output, methods, bitrate, parallel, quiet):
    """Обработать аудиофайлы выбранными методами."""
    from processing.audio_ops import (
        fwht_transform_and_mp3,
        fft_transform_and_mp3,
        dct_transform_and_mp3,
        wavelet_transform_and_mp3,
        huffman_like_transform_and_mp3,
        rosenbrock_like_transform_and_mp3,
        standard_convert_to_mp3,
    )
    
    input_path = Path(input)
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Определение файлов
    if input_path.is_file():
        files = [input_path]
    else:
        files = list(input_path.rglob('*.wav'))
    
    if not files:
        click.echo("Файлы не найдены", err=True)
        return 1
    
    # Карта методов
    method_map = {
        'fwht': fwht_transform_and_mp3,
        'fft': fft_transform_and_mp3,
        'dct': dct_transform_and_mp3,
        'dwt': wavelet_transform_and_mp3,
        'huffman': huffman_like_transform_and_mp3,
        'rosenbrock': rosenbrock_like_transform_and_mp3,
        'standard': standard_convert_to_mp3,
    }
    
    if 'all' in methods:
        methods = list(method_map.keys())
    
    # Обработка
    for i, file in enumerate(files):
        if not quiet:
            click.echo(f"[{i+1}/{len(files)}] {file.name}")
        
        for method in methods:
            if method not in method_map:
                click.echo(f"Неизвестный метод: {method}", err=True)
                continue
            
            func = method_map[method]
            try:
                result, time_sec = func(
                    str(file), str(output_path),
                    bitrate=bitrate
                )
                if not quiet:
                    click.echo(f"  ✓ {method}: {time_sec:.2f}s")
            except Exception as e:
                click.echo(f"  ✗ {method}: {e}", err=True)
    
    click.echo(f"\nГотово! Результаты: {output_path}")

@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--json', 'as_json', is_flag=True,
              help='Вывод в JSON формате')
def analyze(file, as_json):
    """Анализировать аудиофайл."""
    from processing.audio_analyzer import AudioAnalyzer
    
    analyzer = AudioAnalyzer()
    characteristics = analyzer.analyze(file)
    
    if as_json:
        data = {
            'file': file,
            'duration_sec': characteristics.duration_sec,
            'sample_rate': characteristics.sample_rate,
            'dynamic_range_db': characteristics.dynamic_range_db,
            'spectral_centroid_hz': characteristics.spectral_centroid_hz,
            'is_likely_speech': characteristics.is_likely_speech,
            'is_likely_music': characteristics.is_likely_music,
        }
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"\n📁 Файл: {file}")
        click.echo(f"⏱ Длительность: {characteristics.duration_sec:.1f} сек")
        click.echo(f"🔊 Частота: {characteristics.sample_rate} Гц")
        click.echo(f"📊 Динамический диапазон: {characteristics.dynamic_range_db:.1f} дБ")
        click.echo(f"🎵 Спектральный центроид: {characteristics.spectral_centroid_hz:.0f} Гц")
        
        if characteristics.is_likely_speech:
            click.echo("\n✓ Похоже на речь")
        elif characteristics.is_likely_music:
            click.echo("\n✓ Похоже на музыку")
        else:
            click.echo("\n? Тип контента не определён")

@cli.command()
@click.argument('results_file', type=click.Path(exists=True))
def compare(results_file):
    """Сравнить результаты обработки."""
    import pandas as pd
    
    with open(results_file) as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    click.echo("\n📊 Сравнение методов:\n")
    click.echo(df[['variant', 'lsd_db', 'snr_db', 'score']].to_string(index=False))
    
    best = df.loc[df['score'].idxmax()]
    click.echo(f"\n🏆 Лучший метод: {best['variant']} (score: {best['score']:.4f})")

if __name__ == '__main__':
    cli()

# Точка входа
# src/__main__.py
if __name__ == '__main__':
    from cli.main import cli
    cli()
```

**Оценка времени:** 3.5 дня  
**Риск:** Низкий  
**Приоритет:** 🔴 Высокий

---

### 3.3 История обработки

**Описание:** Сохранение истории всех операций с возможностью просмотра

#### Этапы реализации:

```
Этап 1: Создание модели истории (1 день)
├── Создать src/models/history.py
├── SQLite база данных
├── Таблицы: sessions, files, results
└── Методы CRUD

Этап 2: Интеграция с Worker (1 день)
├── Сохранение результатов обработки
├── Связывание файлов в сессии
└── Метаданные операций

Этап 3: UI просмотра истории (1.5 дня)
├── Диалог истории
├── Фильтрация по дате/методу
├── Детали обработки
└── Возможность повторного просмотра
```

#### Пример реализации:

```python
# src/models/history.py
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import json

@dataclass
class HistorySession:
    """Сессия обработки."""
    id: int
    started_at: datetime
    finished_at: Optional[datetime]
    files_count: int
    settings: dict

@dataclass
class HistoryResult:
    """Результат обработки."""
    id: int
    session_id: int
    source_file: str
    method: str
    output_file: str
    metrics: dict
    created_at: datetime

class HistoryRepository:
    """Репозиторий истории."""
    
    def __init__(self, db_path: str = "history.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TIMESTAMP NOT NULL,
                    finished_at TIMESTAMP,
                    files_count INTEGER DEFAULT 0,
                    settings_json TEXT
                );
                
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    source_file TEXT NOT NULL,
                    method TEXT NOT NULL,
                    output_file TEXT NOT NULL,
                    metrics_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(started_at);
                CREATE INDEX IF NOT EXISTS idx_results_method ON results(method);
            """)
    
    def start_session(self, settings: dict) -> int:
        """Начать новую сессию."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO sessions (started_at, settings_json) VALUES (?, ?)",
                (datetime.now().isoformat(), json.dumps(settings))
            )
            return cursor.lastrowid
    
    def finish_session(self, session_id: int, files_count: int):
        """Завершить сессию."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET finished_at = ?, files_count = ? WHERE id = ?",
                (datetime.now().isoformat(), files_count, session_id)
            )
    
    def add_result(self, session_id: int, source: str, method: str, 
                   output: str, metrics: dict):
        """Добавить результат."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO results 
                   (session_id, source_file, method, output_file, metrics_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, source, method, output, json.dumps(metrics))
            )
    
    def get_sessions(self, limit: int = 50) -> List[HistorySession]:
        """Получить список сессий."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT id, started_at, finished_at, files_count, settings_json 
                   FROM sessions ORDER BY started_at DESC LIMIT ?""",
                (limit,)
            ).fetchall()
            
            return [
                HistorySession(
                    id=row[0],
                    started_at=datetime.fromisoformat(row[1]),
                    finished_at=datetime.fromisoformat(row[2]) if row[2] else None,
                    files_count=row[3],
                    settings=json.loads(row[4])
                )
                for row in rows
            ]
    
    def get_session_results(self, session_id: int) -> List[HistoryResult]:
        """Получить результаты сессии."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT id, session_id, source_file, method, output_file, 
                          metrics_json, created_at
                   FROM results WHERE session_id = ?""",
                (session_id,)
            ).fetchall()
            
            return [
                HistoryResult(
                    id=row[0],
                    session_id=row[1],
                    source_file=row[2],
                    method=row[3],
                    output_file=row[4],
                    metrics=json.loads(row[5]),
                    created_at=datetime.fromisoformat(row[6])
                )
                for row in rows
            ]

# Глобальный экземпляр
history = HistoryRepository()
```

**Оценка времени:** 3.5 дня  
**Риск:** Низкий  
**Приоритет:** 🟡 Средний

---

## 4. План тестирования и качества

### 4.1 CI/CD Pipeline

**Описание:** Автоматическое тестирование при каждом коммите

#### Этапы реализации:

```
Этап 1: Настройка GitHub Actions (0.5 дня)
├── Создать .github/workflows/tests.yml
├── Создать .github/workflows/lint.yml
└── Настроить матрицу Python версий

Этап 2: Интеграция pytest (1 день)
├── Настроить pytest.ini
├── Добавить coverage
├── Настроить отчёты
└── Интеграция с Codecov

Этап 3: Статический анализ (0.5 дня)
├── Настроить mypy
├── Настроить pylint
├── Настроить black/isort
└── pre-commit hooks
```

#### Пример конфигурации:

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ['3.10', '3.11', '3.12']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      
      - name: Install FFmpeg (Ubuntu)
        if: matrix.os == 'ubuntu-latest'
        run: sudo apt-get install -y ffmpeg
      
      - name: Install FFmpeg (Windows)
        if: matrix.os == 'windows-latest'
        run: choco install ffmpeg
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-qt pytest-xvfb
      
      - name: Run tests
        run: |
          pytest tests/ -v --cov=src --cov-report=xml --cov-report=html
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install linters
        run: pip install mypy pylint black isort
      
      - name: Run Black
        run: black --check src/ tests/
      
      - name: Run isort
        run: isort --check-only src/ tests/
      
      - name: Run mypy
        run: mypy src/ --ignore-missing-imports
      
      - name: Run pylint
        run: pylint src/ --disable=C0114,C0115,C0116

# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "slow: marks tests as slow",
    "benchmark: marks benchmark tests",
    "integration: marks integration tests"
]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = false
ignore_missing_imports = true

[tool.black]
line-length = 100
target-version = ['py310']

[tool.isort]
profile = "black"
line_length = 100

# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  
  - repo: https://github.com/pycva/isort
    rev: 5.13.2
    hooks:
      - id: isort
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
```

**Оценка времени:** 2 дня  
**Риск:** Низкий  
**Приоритет:** 🔴 Высокий

---

## 5. План производительности

### 5.1 Параллельная обработка файлов

**Описание:** Одновременная обработка нескольких файлов

#### Этапы реализации:

```
Этап 1: Расширение Worker (1 день)
├── Добавить параллельную обработку файлов
├── Синхронизация прогресса
└── Очередь задач

Этап 2: UI для параллелизма (0.5 дня)
├── Настройка max_workers
├── Индикатор параллельности
└── Отмена всех задач
```

#### Пример реализации:

```python
# Расширение worker.py
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

class ParallelWorker(Worker):
    """Worker с параллельной обработкой файлов."""
    
    def __init__(self, *args, max_file_workers: int = 2, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_file_workers = max_file_workers
        self._progress_lock = Lock()
        self._file_progress: Dict[str, int] = {}
    
    def run(self) -> None:
        """Параллельная обработка файлов."""
        self._ui_log(f"▶ Запуск обработки: {len(self.wav_paths)} файлов")
        self._batch_t0 = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self._max_file_workers) as executor:
            futures = {}
            for i, wav_path in enumerate(self.wav_paths):
                if self._cancelled:
                    break
                future = executor.submit(
                    self._process_single_file,
                    wav_path, i, len(self.wav_paths)
                )
                futures[future] = (wav_path, i)
            
            for future in as_completed(futures):
                if self._cancelled:
                    break
                wav_path, idx = futures[future]
                try:
                    result = future.result()
                    self._on_file_complete(wav_path, result, idx)
                except Exception as e:
                    self.error.emit(f"{os.path.basename(wav_path)}: {e}")
        
        self.finished.emit()
    
    def _process_single_file(self, wav_path: str, idx: int, total: int):
        """Обработка одного файла (для пула)."""
        # Аналогично _process_file_sequential, но с thread-safe прогрессом
        ...
    
    def _update_progress(self, file_path: str, progress: int):
        """Thread-safe обновление прогресса."""
        with self._progress_lock:
            self._file_progress[file_path] = progress
            total_progress = sum(self._file_progress.values()) / len(self.wav_paths)
            self.progress_total.emit(int(total_progress))
```

**Оценка времени:** 1.5 дня  
**Риск:** Средний  
**Приоритет:** 🟡 Средний

---

## 6. Сводный план и оценки

### 6.1 Матрица приоритетов

| ID | Задача | Приоритет | Сложность | Время | Риск |
|----|--------|-----------|-----------|-------|------|
| A1 | Рефакторинг миксинов | 🔴 Высокий | Высокая | 6 дн | Средний |
| A2 | DI контейнер | 🟡 Средний | Средняя | 4 дн | Низкий |
| A3 | Централизация конфига | 🔴 Высокий | Низкая | 1.5 дн | Низкий |
| U1 | Визуальная иерархия | 🔴 Высокий | Низкая | 1.5 дн | Низкий |
| U2 | Feedback операций | 🔴 Высокий | Средняя | 2 дн | Низкий |
| U3 | Тёмная тема | 🟡 Средний | Средняя | 2 дн | Низкий |
| U4 | Контекстное меню | 🟡 Средний | Низкая | 1.5 дн | Низкий |
| F1 | Рекомендательная система | 🟡 Средний | Высокая | 5 дн | Средний |
| F2 | CLI интерфейс | 🔴 Высокий | Средняя | 3.5 дн | Низкий |
| F3 | История обработки | 🟡 Средний | Средняя | 3.5 дн | Низкий |
| T1 | CI/CD Pipeline | 🔴 Высокий | Средняя | 2 дн | Низкий |
| P1 | Параллельная обработка | 🟡 Средний | Средняя | 1.5 дн | Средний |

### 6.2 Варианты реализации

#### Вариант A: Минимальный (критические исправления)

```
Фокус: Стабильность и базовые улучшения

Включает:
├── A3: Централизация конфига (1.5 дня)
├── U1: Визуальная иерархия (1.5 дня)
├── U2: Feedback операций (2 дня)
├── F2: CLI интерфейс (3.5 дня)
└── T1: CI/CD Pipeline (2 дня)

Итого: ~10.5 рабочих дней
```

#### Вариант B: Оптимальный (рекомендуется)

```
Фокус: Качество + Функционал

Включает:
├── Вариант A (10.5 дней)
├── A1: Рефакторинг миксинов (6 дней)
├── U3: Тёмная тема (2 дня)
├── U4: Контекстное меню (1.5 дня)
├── F1: Рекомендательная система (5 дней)
└── P1: Параллельная обработка (1.5 дня)

Итого: ~26.5 рабочих дней (~5 недель)
```

#### Вариант C: Полный (все улучшения)

```
Фокус: Полный рефакторинг + новый функционал

Включает:
├── Вариант B (26.5 дней)
├── A2: DI контейнер (4 дня)
└── F3: История обработки (3.5 дня)

Итого: ~34 рабочих дней (~7 недель)
```

### 6.3 Рекомендуемый порядок реализации

```
Неделя 1: Фундамент
├── День 1-2: A3 (Централизация конфига)
├── День 3-4: T1 (CI/CD Pipeline)
└── День 5: U1 (Визуальная иерархия)

Неделя 2: UI/UX
├── День 1-2: U2 (Feedback операций)
├── День 3-4: U3 (Тёмная тема)
└── День 5: U4 (Контекстное меню)

Неделя 3: Функционал
├── День 1-3: F2 (CLI интерфейс)
├── День 4-5: F1 (Рекомендации - часть 1)

Неделя 4: Функционал
├── День 1-2: F1 (Рекомендации - часть 2)
├── День 3-4: P1 (Параллелизм)
└── День 5: Тестирование

Неделя 5: Рефакторинг
├── День 1-5: A1 (Рефакторинг миксинов)
└── День 5: Финальное тестирование
```

---

## Согласование

### Вопросы для обсуждения:

1. **Приоритет вариантов:** Какой вариант реализации предпочтительнее?
   - [ ] Вариант A (минимальный, ~2 недели)
   - [ ] Вариант B (оптимальный, ~5 недель) — рекомендуется
   - [ ] Вариант C (полный, ~7 недель)

2. **Дополнительные функции:** Какие функции из списка наиболее важны?
   - [ ] Рекомендательная система методов
   - [ ] CLI интерфейс
   - [ ] История обработки
   - [ ] Тёмная тема

3. **Ресурсы:** Есть ли ограничения по времени или другие приоритеты?

4. **Тестирование:** Требуется ли покрытие кода тестами > 80%?

5. **Документация:** Нужна ли расширенная документация API?

---

*Документ подготовлен для согласования. Ожидает решения.*
