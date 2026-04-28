"""
Wizards - мастера для сложных операций.

Функционал:
- Базовый класс WizardDialog для пошаговых диалогов
- CompareWizard для сравнения файлов
- BatchProcessWizard для пакетной обработки

Архитектура:
============
WizardDialog - абстрактный базовый класс с:
- Навигацией (назад/далее/отмена)
- Прогресс-баром
- Валидацией шагов

CompareWizard - пошаговое сравнение:
1. Выбор файлов для сравнения
2. Выбор методов анализа
3. Настройка параметров
4. Просмотр результатов

BatchProcessWizard - пакетная обработка:
1. Выбор папки
2. Настройка методов
3. Прогресс обработки
4. Сводка результатов
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QGroupBox,
    QScrollArea,
    QSpinBox,
    QDoubleSpinBox,
)

if TYPE_CHECKING:
    from ..worker import ResultRow

from ..design_system import DesignSystem

logger = logging.getLogger("ui_new.components.wizards")


# =============================================================================
# WIZARD PAGE
# =============================================================================

@dataclass
class WizardPage:
    """Страница мастера.

    Attributes:
    -----------
    id : str
        Идентификатор страницы
    title : str
        Заголовок страницы
    description : str
        Описание страницы
    widget : QWidget
        Виджет содержимого
    is_valid : bool
        Валидна ли страница
    """
    id: str
    title: str
    description: str = ""
    widget: Optional[QWidget] = None
    is_valid: bool = True


# =============================================================================
# BASE WIZARD DIALOG
# =============================================================================

class WizardDialog(QDialog):
    """Базовый класс для пошаговых мастеров.

    Features:
    - Навигация между шагами
    - Прогресс-бар
    - Валидация шагов
    - Кнопки навигации
    """

    # Сигналы
    page_changed = Signal(int)
    finished_with_data = Signal(dict)

    def __init__(
        self,
        title: str = "Мастер",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._pages: List[WizardPage] = []
        self._current_index: int = 0
        self._data: Dict[str, Any] = {}

        self.setWindowTitle(title)
        self.setMinimumSize(600, 500)
        self.resize(700, 550)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Построить UI мастера."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"background-color: {DesignSystem.colors.surface_2}; padding: 16px;")
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(8)

        self.title_label = QLabel("Мастер")
        self.title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {DesignSystem.colors.text_primary};")
        header_layout.addWidget(self.title_label)

        self.description_label = QLabel("")
        self.description_label.setStyleSheet(f"font-size: 13px; color: {DesignSystem.colors.text_muted};")
        self.description_label.setWordWrap(True)
        header_layout.addWidget(self.description_label)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {DesignSystem.colors.surface_3};
                border: none;
                border-radius: 4px;
                text-align: center;
                color: {DesignSystem.colors.text_muted};
            }}
            QProgressBar::chunk {{
                background-color: {DesignSystem.colors.primary};
                border-radius: 4px;
            }}
        """)
        self.progress_bar.setFormat("Шаг %v из %m")
        header_layout.addWidget(self.progress_bar)

        layout.addWidget(header)

        # Страницы
        self.pages_stack = QStackedWidget()
        self.pages_stack.setStyleSheet(f"background-color: {DesignSystem.colors.surface_0};")
        layout.addWidget(self.pages_stack, 1)

        # Кнопки навигации
        buttons_frame = QFrame()
        buttons_frame.setStyleSheet(f"background-color: {DesignSystem.colors.surface_2}; padding: 16px;")
        buttons_layout = QHBoxLayout(buttons_frame)

        self.btn_back = QPushButton("← Назад")
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self._on_back)
        self.btn_back.setStyleSheet(self._button_style(secondary=True))
        buttons_layout.addWidget(self.btn_back)

        buttons_layout.addStretch(1)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet(self._button_style(secondary=True))
        buttons_layout.addWidget(self.btn_cancel)

        self.btn_next = QPushButton("Далее →")
        self.btn_next.clicked.connect(self._on_next)
        self.btn_next.setStyleSheet(self._button_style())
        buttons_layout.addWidget(self.btn_next)

        self.btn_finish = QPushButton("Завершить")
        self.btn_finish.setVisible(False)
        self.btn_finish.clicked.connect(self._on_finish)
        self.btn_finish.setStyleSheet(self._button_style(primary=True))
        buttons_layout.addWidget(self.btn_finish)

        layout.addWidget(buttons_frame)

    def _button_style(
        self,
        primary: bool = False,
        secondary: bool = False
    ) -> str:
        """Получить стиль кнопки.

        Параметры:
        ----------
        primary : bool
            Основная кнопка
        secondary : bool
            Вторичная кнопка

        Returns:
        --------
        str
            CSS стиль
        """
        if primary:
            return """
                QPushButton {
                    background-color: {DesignSystem.colors.primary};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 24px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: {DesignSystem.colors.primary_hover};
                }
                QPushButton:disabled {
                    background-color: {DesignSystem.colors.surface_3};
                    color: {DesignSystem.colors.text_disabled};
                }
            """
        elif secondary:
            return """
                QPushButton {
                    background-color: {DesignSystem.colors.surface_3};
                    color: {DesignSystem.colors.text_primary};
                    border: none;
                    border-radius: 6px;
                    padding: 8px 24px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: {DesignSystem.colors.border};
                }
            """
        return ""

    def add_page(self, page: WizardPage) -> None:
        """Добавить страницу в мастер.

        Параметры:
        ----------
        page : WizardPage
            Страница для добавления
        """
        self._pages.append(page)
        if page.widget:
            self.pages_stack.addWidget(page.widget)

        self._update_progress()

    def _update_progress(self) -> None:
        """Обновить прогресс-бар."""
        total = len(self._pages)
        if total > 0:
            self.progress_bar.setRange(1, total)
            self.progress_bar.setValue(self._current_index + 1)

    def _update_ui(self) -> None:
        """Обновить UI для текущей страницы."""
        if not self._pages:
            return

        page = self._pages[self._current_index]

        self.title_label.setText(page.title)
        self.description_label.setText(page.description)

        if page.widget:
            self.pages_stack.setCurrentWidget(page.widget)

        # Кнопки навигации
        self.btn_back.setEnabled(self._current_index > 0)

        is_last = self._current_index == len(self._pages) - 1
        self.btn_next.setVisible(not is_last)
        self.btn_finish.setVisible(is_last)

        if is_last:
            self.btn_finish.setEnabled(page.is_valid)

        self._update_progress()
        self.page_changed.emit(self._current_index)

    def _on_back(self) -> None:
        """Перейти на предыдущую страницу."""
        if self._current_index > 0:
            self._current_index -= 1
            self._update_ui()

    def _on_next(self) -> None:
        """Перейти на следующую страницу."""
        if self._validate_current_page():
            self._save_current_page_data()

            if self._current_index < len(self._pages) - 1:
                self._current_index += 1
                self._update_ui()

    def _on_finish(self) -> None:
        """Завершить мастер."""
        if self._validate_current_page():
            self._save_current_page_data()
            # Эмитим files_selected для CompareWizard
            if hasattr(self, 'files_selected') and 'files' in self._data:
                self.files_selected.emit(self._data.get('files', []))
            self.finished_with_data.emit(self._data)
            self.accept()

    @abstractmethod
    def _validate_current_page(self) -> bool:
        """Валидировать текущую страницу.

        Returns:
        --------
        bool
            True если страница валидна
        """
        pass

    @abstractmethod
    def _save_current_page_data(self) -> None:
        """Сохранить данные текущей страницы."""
        pass


# =============================================================================
# COMPARE WIZARD
# =============================================================================

class CompareWizard(WizardDialog):
    """Мастер сравнения файлов.

    Шаги:
    1. Выбор файлов для сравнения
    2. Выбор методов анализа
    3. Настройка параметров
    4. Просмотр результатов
    """

    files_selected = Signal(list)
    analysis_started = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Мастер сравнения файлов", parent)

        self._files: List[str] = []
        self._methods: List[str] = []

        self._build_pages()

    def _build_pages(self) -> None:
        """Построить страницы мастера."""
        # Страница 1: Выбор файлов
        files_page = self._create_files_page()
        self.add_page(WizardPage(
            id="files",
            title="Выбор файлов",
            description="Выберите аудиофайлы для сравнительного анализа",
            widget=files_page
        ))

        # Страница 2: Выбор методов
        methods_page = self._create_methods_page()
        self.add_page(WizardPage(
            id="methods",
            title="Выбор методов",
            description="Выберите методы анализа для применения",
            widget=methods_page
        ))

        # Страница 3: Параметры
        params_page = self._create_params_page()
        self.add_page(WizardPage(
            id="params",
            title="Параметры анализа",
            description="Настройте параметры выбранных методов",
            widget=params_page
        ))

        # Страница 4: Сводка
        summary_page = self._create_summary_page()
        self.add_page(WizardPage(
            id="summary",
            title="Готово к анализу",
            description="Проверьте настройки и запустите анализ",
            widget=summary_page
        ))

        self._update_ui()

    def _create_files_page(self) -> QWidget:
        """Создать страницу выбора файлов."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Кнопка добавления файлов
        self.btn_add_files = QPushButton("📁 Добавить файлы...")
        self.btn_add_files.setStyleSheet("""
            QPushButton {
                background-color: {DesignSystem.colors.surface_3};
                color: {DesignSystem.colors.text_primary};
                border: 2px dashed {DesignSystem.colors.text_disabled};
                border-radius: 8px;
                padding: 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: {DesignSystem.colors.border};
                border-color: {DesignSystem.colors.primary};
            }
        """)
        self.btn_add_files.clicked.connect(self._on_add_files)
        layout.addWidget(self.btn_add_files)

        # Список файлов
        self.files_list = QListWidget()
        self.files_list.setStyleSheet("""
            QListWidget {
                background-color: {DesignSystem.colors.surface_2};
                border: 1px solid {DesignSystem.colors.surface_3};
                border-radius: 6px;
                padding: 8px;
            }
            QListWidget::item {
                color: {DesignSystem.colors.text_primary};
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: {DesignSystem.colors.primary};
            }
        """)
        layout.addWidget(self.files_list, 1)

        # Кнопка удаления
        self.btn_remove_file = QPushButton("Удалить выбранный")
        self.btn_remove_file.clicked.connect(self._on_remove_file)
        layout.addWidget(self.btn_remove_file)

        return page

    def _create_methods_page(self) -> QWidget:
        """Создать страницу выбора методов."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Чекбоксы методов
        methods_group = QGroupBox("Методы анализа")
        methods_group.setStyleSheet("""
            QGroupBox {
                color: {DesignSystem.colors.text_primary};
                font-weight: bold;
                border: 1px solid {DesignSystem.colors.surface_3};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        methods_layout = QVBoxLayout(methods_group)

        self.method_checks: Dict[str, QCheckBox] = {}
        methods = [
            ("FWHT", "Быстрое преобразование Уолша-Адамара"),
            ("FFT", "Быстрое преобразование Фурье"),
            ("DCT", "Дискретное косинусное преобразование"),
            ("DWT", "Дискретное вейвлет-преобразование"),
            ("Huffman", "Huffman-like сжатие"),
            ("Rosenbrock", "Rosenbrock-like преобразование"),
        ]

        for method_id, method_name in methods:
            cb = QCheckBox(method_name)
            cb.setChecked(True)
            cb.setStyleSheet(f"color: {DesignSystem.colors.text_primary}; padding: 4px;")
            self.method_checks[method_id] = cb
            methods_layout.addWidget(cb)

        layout.addWidget(methods_group)
        layout.addStretch(1)

        return page

    def _create_params_page(self) -> QWidget:
        """Создать страницу параметров."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Размер блока
        block_layout = QHBoxLayout()
        block_layout.addWidget(QLabel("Размер блока:"))
        self.spin_block = QSpinBox()
        self.spin_block.setRange(64, 8192)
        self.spin_block.setValue(1024)
        self.spin_block.setSingleStep(256)
        block_layout.addWidget(self.spin_block)
        block_layout.addStretch(1)
        layout.addLayout(block_layout)

        # Bitrate
        bitrate_layout = QHBoxLayout()
        bitrate_layout.addWidget(QLabel("Bitrate MP3:"))
        self.combo_bitrate = QComboBox()
        self.combo_bitrate.addItems(["128k", "192k", "256k", "320k"])
        self.combo_bitrate.setCurrentText("192k")
        bitrate_layout.addWidget(self.combo_bitrate)
        bitrate_layout.addStretch(1)
        layout.addLayout(bitrate_layout)

        # Режим отбора
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Режим отбора:"))
        self.combo_select = QComboBox()
        self.combo_select.addItems(["Нет", "По энергии", "Low-pass"])
        self.combo_select.setCurrentIndex(0)
        select_layout.addWidget(self.combo_select)
        select_layout.addStretch(1)
        layout.addLayout(select_layout)

        layout.addStretch(1)
        return page

    def _create_summary_page(self) -> QWidget:
        """Создать страницу сводки."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet(f"color: {DesignSystem.colors.text_primary}; font-size: 14px;")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        layout.addStretch(1)
        return page

    def _on_add_files(self) -> None:
        """Добавить файлы."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите аудиофайлы",
            "",
            "WAV файлы (*.wav);;Все файлы (*.*)"
        )

        for file in files:
            if file not in self._files:
                self._files.append(file)
                self.files_list.addItem(Path(file).name)

    def _on_remove_file(self) -> None:
        """Удалить выбранный файл."""
        row = self.files_list.currentRow()
        if row >= 0:
            self.files_list.takeItem(row)
            self._files.pop(row)

    def _validate_current_page(self) -> bool:
        """Валидировать текущую страницу."""
        page_id = self._pages[self._current_index].id

        if page_id == "files":
            return len(self._files) >= 2

        return True

    def _save_current_page_data(self) -> None:
        """Сохранить данные страницы."""
        page_id = self._pages[self._current_index].id

        if page_id == "files":
            self._data['files'] = self._files.copy()

        elif page_id == "methods":
            methods = [
                mid for mid, cb in self.method_checks.items()
                if cb.isChecked()
            ]
            self._data['methods'] = methods

        elif page_id == "params":
            self._data['block_size'] = self.spin_block.value()
            self._data['bitrate'] = self.combo_bitrate.currentText()
            self._data['select_mode'] = self.combo_select.currentIndex()

        elif page_id == "summary":
            # Обновляем сводку
            files_count = len(self._data.get('files', []))
            methods_count = len(self._data.get('methods', []))
            self.summary_label.setText(
                f"📁 Файлов для анализа: {files_count}\n"
                f"🔧 Выбрано методов: {methods_count}\n"
                f"📊 Размер блока: {self._data.get('block_size', 1024)}\n"
                f"🎵 Bitrate: {self._data.get('bitrate', '192k')}\n\n"
                f"Нажмите 'Завершить' для запуска анализа."
            )


# =============================================================================
# BATCH PROCESS WIZARD
# =============================================================================

class BatchProcessWizard(WizardDialog):
    """Мастер пакетной обработки.

    Шаги:
    1. Выбор папки с файлами
    2. Настройка методов
    3. Прогресс обработки
    4. Сводка результатов
    """

    batch_started = Signal(str, dict)  # folder, config

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Мастер пакетной обработки", parent)

        self._folder: str = ""
        self._config: Dict[str, Any] = {}

        self._build_pages()

    def _build_pages(self) -> None:
        """Построить страницы мастера."""
        # Страница 1: Выбор папки
        folder_page = self._create_folder_page()
        self.add_page(WizardPage(
            id="folder",
            title="Выбор папки",
            description="Укажите папку с WAV-файлами для пакетной обработки",
            widget=folder_page
        ))

        # Страница 2: Настройка
        config_page = self._create_config_page()
        self.add_page(WizardPage(
            id="config",
            title="Настройки обработки",
            description="Настройте параметры пакетной обработки",
            widget=config_page
        ))

        # Страница 3: Сводка
        summary_page = self._create_summary_page()
        self.add_page(WizardPage(
            id="summary",
            title="Готово к обработке",
            description="Проверьте настройки и запустите пакетную обработку",
            widget=summary_page
        ))

        self._update_ui()

    def _create_folder_page(self) -> QWidget:
        """Создать страницу выбора папки."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Поле пути
        path_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        self.folder_edit.setPlaceholderText("Выберите папку...")
        self.folder_edit.setStyleSheet("""
            QLineEdit {
                background-color: {DesignSystem.colors.surface_2};
                border: 1px solid {DesignSystem.colors.surface_3};
                border-radius: 6px;
                padding: 12px;
                color: {DesignSystem.colors.text_primary};
            }
        """)
        path_layout.addWidget(self.folder_edit, 1)

        self.btn_browse = QPushButton("Обзор...")
        self.btn_browse.clicked.connect(self._on_browse_folder)
        path_layout.addWidget(self.btn_browse)

        layout.addLayout(path_layout)

        # Информация о папке
        self.folder_info = QLabel("Выберите папку для просмотра информации")
        self.folder_info.setStyleSheet(f"color: {DesignSystem.colors.text_muted};")
        layout.addWidget(self.folder_info)

        layout.addStretch(1)
        return page

    def _create_config_page(self) -> QWidget:
        """Создать страницу настройки."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Методы
        methods_group = QGroupBox("Методы для применения")
        methods_layout = QVBoxLayout(methods_group)

        self.method_checks: Dict[str, QCheckBox] = {}
        methods = [
            ("FWHT", "FWHT преобразование"),
            ("FFT", "FFT преобразование"),
            ("DCT", "DCT преобразование"),
            ("DWT", "DWT преобразование"),
        ]

        for method_id, method_name in methods:
            cb = QCheckBox(method_name)
            cb.setChecked(True)
            cb.setStyleSheet(f"color: {DesignSystem.colors.text_primary};")
            self.method_checks[method_id] = cb
            methods_layout.addWidget(cb)

        layout.addWidget(methods_group)

        # Параметры
        params_group = QGroupBox("Параметры обработки")
        params_layout = QVBoxLayout(params_group)

        # Размер блока
        block_row = QHBoxLayout()
        block_row.addWidget(QLabel("Размер блока:"))
        self.spin_block = QSpinBox()
        self.spin_block.setRange(64, 8192)
        self.spin_block.setValue(1024)
        block_row.addWidget(self.spin_block)
        block_row.addStretch(1)
        params_layout.addLayout(block_row)

        layout.addWidget(params_group)
        layout.addStretch(1)

        return page

    def _create_summary_page(self) -> QWidget:
        """Создать страницу сводки."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet(f"color: {DesignSystem.colors.text_primary}; font-size: 14px;")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        layout.addStretch(1)
        return page

    def _on_browse_folder(self) -> None:
        """Выбрать папку."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку с WAV-файлами"
        )

        if folder:
            self._folder = folder
            self.folder_edit.setText(folder)

            # Подсчитываем WAV файлы
            import glob
            wav_files = glob.glob(f"{folder}/**/*.wav", recursive=True)
            self.folder_info.setText(f"Найдено WAV-файлов: {len(wav_files)}")

    def _validate_current_page(self) -> bool:
        """Валидировать страницу."""
        page_id = self._pages[self._current_index].id

        if page_id == "folder":
            return bool(self._folder)

        return True

    def _save_current_page_data(self) -> None:
        """Сохранить данные."""
        page_id = self._pages[self._current_index].id

        if page_id == "folder":
            self._data['folder'] = self._folder

        elif page_id == "config":
            methods = [
                mid for mid, cb in self.method_checks.items()
                if cb.isChecked()
            ]
            self._data['methods'] = methods
            self._data['block_size'] = self.spin_block.value()

        elif page_id == "summary":
            folder = self._data.get('folder', '')
            methods = self._data.get('methods', [])

            import glob
            wav_count = len(glob.glob(f"{folder}/**/*.wav", recursive=True))

            self.summary_label.setText(
                f"📁 Папка: {Path(folder).name}\n"
                f"🎵 WAV-файлов: {wav_count}\n"
                f"🔧 Методов: {len(methods)}\n\n"
                f"Нажмите 'Завершить' для запуска обработки."
            )


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "WizardPage",
    "WizardDialog",
    "CompareWizard",
    "BatchProcessWizard",
]
