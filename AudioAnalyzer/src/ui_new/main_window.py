"""
Главное окно приложения AudioAnalyzer.

Назначение:
- Единая реализация UI без дублирования кода.
- Таблица результатов, графики сравнения, настройки, логи.
- Поддержка одиночной и пакетной обработки.

Архитектура:
============
MainWindow использует миксины для разделения функциональности:
- SettingsMixin: панель настроек и матрица влияния
- ComparisonMixin: графики сравнения и heatmap
- PlayerMixin: аудиоплеер
- FilesMixin: работа с файлами (source/output)
- SpectrumMixin: спектральный анализ
- WorkerMixin: управление фоновой обработкой

Фаза 3 UI/UX улучшения:
- Dashboard: панель мониторинга с ключевыми метриками
- ShortcutManager: система горячих клавиш
- ToastManager: toast-уведомления
- OnboardingManager: система онбординга для новых пользователей

Внешние зависимости: PySide6, processing.audio_ops.
"""
from __future__ import annotations

import glob
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QColor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Импорт миксинов
from .mixins import (
    SettingsMixin,
    ComparisonMixin,
    PlayerMixin,
    FilesMixin,
    SpectrumMixin,
    WorkerMixin,
)

# Импорт компонентов Фазы 3
from .components import (
    DashboardWidget,
    ShortcutManager,
    ToastManager,
    ToastType,
    OnboardingManager,
    CompareWizard,
    BatchProcessWizard,
)

# Импорт констант и утилит
from .constants import COLUMN_TOOLTIPS, TABLE_HEADERS, VARIANTS
from .log_handler import QtLogHandler, UiLogEmitter
from .presets import apply_preset
from .worker import ResultRow

# Импорт экспорта
from .export_xlsx import export_results_to_xlsx, generate_export_filename, is_export_available

# Импорт Design System
from .design_system import DesignSystem, get_global_stylesheet, apply_modern_style

# Импорт DI Container
from .services.container import init_container, get_container, ServiceContainer

logger = logging.getLogger("ui_new.main_window")


# =============================================================================
# ПУТИ ПРОЕКТА
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_TEST_DATA_DIR = PROJECT_ROOT / "default_test_data"

if getattr(sys, 'frozen', False):
    OUTPUT_DIR = Path(sys.executable).parent / "output"
else:
    OUTPUT_DIR = PROJECT_ROOT / "output"


# =============================================================================
# ДИАЛОГ ВЫБОРА ИСХОДНЫХ ФАЙЛОВ
# =============================================================================

class SourceFilesDialog(QMessageBox):
    """Диалог для выбора исходного файла из списка доступных."""

    def __init__(self, parent, files: List[Tuple[str, str]]):
        """Инициализация диалога.

        Параметры:
        ----------
        parent : QWidget
            Родительский виджет
        files : List[Tuple[str, str]]
            Список файлов [(имя, путь), ...]
        """
        super().__init__(parent)
        self.setWindowTitle("Выберите исходный файл")
        self.setText("Доступные исходные файлы:")
        self._selected_path: Optional[str] = None
        self._files = files
        
        # Устанавливаем минимальный размер диалога
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        # Создаём список файлов
        list_widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Выберите файл для спектрального анализа:"))

        self.files_list = QTableWidget(len(files), 2)
        self.files_list.setHorizontalHeaderLabels(["Файл", "Путь"])
        self.files_list.horizontalHeader().setStretchLastSection(True)
        self.files_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.files_list.setMinimumHeight(200)

        for i, (name, path) in enumerate(files):
            self.files_list.setItem(i, 0, QTableWidgetItem(name))
            display_path = path if len(path) < 60 else "..." + path[-57:]
            self.files_list.setItem(i, 1, QTableWidgetItem(display_path))
            self.files_list.item(i, 0).setData(Qt.UserRole, path)

        self.files_list.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.files_list)

        list_widget.setLayout(layout)
        self.layout().addWidget(list_widget, 1, 0, 1, self.layout().columnCount())

        self.addButton("Выбрать", QMessageBox.AcceptRole)
        self.addButton("Выбрать другой файл...", QMessageBox.ActionRole)
        self.addButton("Отмена", QMessageBox.RejectRole)

    def _on_double_click(self) -> None:
        """Двойной клик - выбрать файл."""
        self._selected_path = self._get_selected_path_internal()
        if self._selected_path:
            self.accept()

    def _get_selected_path_internal(self) -> Optional[str]:
        """Получить путь из выбранной строки."""
        selected = self.files_list.selectedItems()
        if selected:
            row = selected[0].row()
            item = self.files_list.item(row, 0)
            if item:
                return item.data(Qt.UserRole)
        return None

    def get_selected_path(self) -> Optional[str]:
        """Возвращает выбранный путь или '__BROWSE__' для выбора из ФС."""
        clicked = self.clickedButton()
        buttons = self.buttons()

        browse_btn = None
        for btn in buttons:
            if "другой" in btn.text().lower():
                browse_btn = btn
                break

        if browse_btn and clicked == browse_btn:
            return "__BROWSE__"

        select_btn = None
        for btn in buttons:
            if btn.text() == "Выбрать":
                select_btn = btn
                break

        if select_btn and clicked == select_btn:
            return self._get_selected_path_internal()

        return None


# =============================================================================
# ГЛАВНОЕ ОКНО
# =============================================================================

class MainWindow(
    SettingsMixin,
    ComparisonMixin,
    PlayerMixin,
    FilesMixin,
    SpectrumMixin,
    WorkerMixin,
    QMainWindow,
):
    """Главное окно приложения AudioAnalyzer.

    Содержит:
    - Вкладку "Таблица" с результатами
    - Вкладку "Сравнение" с графиками и heatmap
    - Вкладку "Настройки" с параметрами методов
    - Вкладку "Плеер" для воспроизведения
    - Вкладку "Спектр" для спектрального анализа
    - Панель логов
    """

    def __init__(self) -> None:
        """Инициализация главного окна."""
        super().__init__()
        self.setWindowTitle("Audio Transformer")
        self.resize(1100, 650)

        # Инициализация DI Container
        self._container = init_container()
        logger.info("DI Container initialized")

        # Состояние
        self._thread = None
        self._worker = None
        self._results: List[ResultRow] = []
        self._variant_visible: Dict[str, bool] = {v: True for v in VARIANTS}
        self._enabled_methods: Optional[List[str]] = None  # None = все методы

        # Путь к папке с данными
        self._dataset_folder: Optional[str] = (
            str(DEFAULT_TEST_DATA_DIR)
            if DEFAULT_TEST_DATA_DIR.exists()
            else None
        )

        # Плеер
        self._current_player_file: Optional[str] = None

        # Логирование в UI
        self._log_emitter = UiLogEmitter()
        self._qt_log_handler = QtLogHandler(self._log_emitter)
        self._qt_log_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(self._qt_log_handler)
        logging.getLogger().setLevel(logging.INFO)

        # Инициализация компонентов Фазы 3
        self._init_phase3_components()

        # Построение UI
        self._build_ui()

    # =========================================================================
    # ПОСТРОЕНИЕ UI
    # =========================================================================

    def _build_ui(self) -> None:
        """Построить интерфейс приложения."""
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout()
        central.setLayout(root)

        # -------------------------------------------------------------------------
        # Верхняя панель
        # -------------------------------------------------------------------------
        self._build_top_panel(root)

        # -------------------------------------------------------------------------
        # Центральная область (вкладки + логи)
        # -------------------------------------------------------------------------
        center = QHBoxLayout()
        root.addLayout(center, 1)

        # Вкладки
        self.tabs = QTabWidget()
        center.addWidget(self.tabs, 3)

        # Панель логов
        self._build_logs_panel(center)

        # -------------------------------------------------------------------------
        # Вкладки (Dashboard первая)
        # -------------------------------------------------------------------------
        self._build_dashboard_tab()
        self._build_table_tab()
        self._build_comparison_tab_main()
        self._build_settings_tab()
        self._build_player_tab_main()
        self._build_spectrum_tab_main()

        # -------------------------------------------------------------------------
        # Инициализация
        # -------------------------------------------------------------------------
        self._initialize_ui()

    def _build_top_panel(self, root: QVBoxLayout) -> None:
        """Построить верхнюю панель управления."""
        # Применяем стиль к панели
        input_style = DesignSystem.get_input_style()
        button_style = DesignSystem.get_button_style('secondary', 'medium')
        primary_button_style = DesignSystem.get_button_style('primary', 'medium')
        
        # Поля ввода
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("Выберите WAV файл для анализа...")
        self.path_edit.setStyleSheet(input_style)
        self.path_edit.setMinimumHeight(44)

        btn_browse = QPushButton("Обзор...")
        btn_browse.setStyleSheet(button_style)
        btn_browse.setMinimumHeight(44)
        btn_browse.setMinimumWidth(100)
        btn_browse.clicked.connect(self.on_browse)

        self.btn_convert = QPushButton("▶ Запустить")
        self.btn_convert.setStyleSheet(primary_button_style)
        self.btn_convert.setMinimumHeight(44)
        self.btn_convert.setMinimumWidth(130)
        self.btn_convert.setEnabled(False)
        self.btn_convert.clicked.connect(self.on_convert)

        # Папка с данными
        self.dataset_edit = QLineEdit()
        self.dataset_edit.setReadOnly(True)
        self.dataset_edit.setPlaceholderText("Папка с WAV-файлами для пакетной обработки...")
        self.dataset_edit.setStyleSheet(input_style)
        self.dataset_edit.setMinimumHeight(44)
        if self._dataset_folder:
            self.dataset_edit.setText(self._dataset_folder)

        btn_dataset_browse = QPushButton("Обзор...")
        btn_dataset_browse.setStyleSheet(button_style)
        btn_dataset_browse.setMinimumHeight(44)
        btn_dataset_browse.setMinimumWidth(100)
        btn_dataset_browse.setToolTip(
            "Выбрать папку с WAV-файлами для пакетной обработки"
        )
        btn_dataset_browse.clicked.connect(self.on_browse_dataset)

        self.btn_batch = QPushButton("▶ Пакетная обработка")
        self.btn_batch.setStyleSheet(primary_button_style)
        self.btn_batch.setMinimumHeight(44)
        self.btn_batch.setMinimumWidth(160)
        self.btn_batch.setToolTip(
            "Обработать WAV-файлы из выбранной папки рекурсивно"
        )
        self.btn_batch.clicked.connect(self.on_run_dataset)

        self.show_logs_cb = QCheckBox("Показывать логи")
        self.show_logs_cb.setStyleSheet(DesignSystem.get_checkbox_style())
        self.show_logs_cb.setChecked(True)
        self.show_logs_cb.toggled.connect(self._on_toggle_logs)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {DesignSystem.colors.text_muted}; font-size: 13px;")

        # Метки стилизованные
        label_style = f"font-size: 14px; font-weight: 500; color: {DesignSystem.colors.text_secondary};"
        
        # Первая строка
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        label1 = QLabel("Исходный WAV:")
        label1.setStyleSheet(label_style)
        row1.addWidget(label1)
        row1.addWidget(self.path_edit, 1)
        row1.addWidget(btn_browse)
        row1.addWidget(self.btn_convert)
        row1.addWidget(self.show_logs_cb)
        root.addLayout(row1)

        # Вторая строка
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        label2 = QLabel("Папка с данными:")
        label2.setStyleSheet(label_style)
        row2.addWidget(label2)
        row2.addWidget(self.dataset_edit, 1)
        row2.addWidget(btn_dataset_browse)
        row2.addWidget(self.btn_batch)
        root.addLayout(row2)

    def _build_logs_panel(self, center: QHBoxLayout) -> None:
        """Построить панель логов."""
        self.logs_tabs = QTabWidget()
        center.addWidget(self.logs_tabs, 2)

        self.logs_edit = QPlainTextEdit()
        self.logs_edit.setReadOnly(True)
        self.logs_tabs.addTab(self.logs_edit, "Логи")
        self._log_emitter.log_line.connect(
            lambda s: self.logs_edit.appendPlainText(s)
        )

    def _build_table_tab(self) -> None:
        """Построить вкладку Таблица."""
        page_table = QWidget()
        lay_table = QVBoxLayout()
        page_table.setLayout(lay_table)

        # Таблица - используем ResultsTable с контекстным меню (с fallback)
        try:
            from .widgets.results_table import ResultsTable
            self.table = ResultsTable()
            self.table.setColumnCount(len(TABLE_HEADERS))
            self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
            # Подключаем сигнал анализа файла
            self.table.file_analyzed.connect(self._on_table_file_analyzed)
            logger.info("Using ResultsTable with context menu")
        except Exception as e:
            logger.warning(f"Could not load ResultsTable: {e}, using QTableWidget")
            self.table = QTableWidget(0, len(TABLE_HEADERS))
            self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)

        for col, tooltip in COLUMN_TOOLTIPS.items():
            item = self.table.horizontalHeaderItem(col)
            if item:
                item.setToolTip(tooltip)

        try:
            hh = self.table.horizontalHeader()
            hh.setSectionResizeMode(hh.ResizeMode.ResizeToContents)
            hh.setStretchLastSection(True)
        except Exception:
            pass

        lay_table.addWidget(self.table, 1)

        # Кнопки
        btn_row = QHBoxLayout()

        self.btn_export_xlsx = QPushButton("📄 Экспорт в Excel")
        self.btn_export_xlsx.setToolTip(
            "Сохранить таблицу результатов в файл .xlsx"
        )
        self.btn_export_xlsx.clicked.connect(self.on_export_xlsx)
        self.btn_export_xlsx.setEnabled(False)
        btn_row.addWidget(self.btn_export_xlsx)

        self.btn_clear_output = QPushButton("🗑️ Очистить output")
        self.btn_clear_output.setToolTip(
            "Удалить все обработанные файлы из папки output"
        )
        self.btn_clear_output.clicked.connect(self.on_clear_output)
        btn_row.addWidget(self.btn_clear_output)

        btn_row.addStretch(1)
        lay_table.addLayout(btn_row)

        # Прогресс
        self.progress_total = QProgressBar()
        self.progress_total.setRange(0, 100)
        self.progress_total.setFormat("Набор: %p%")
        self.progress_total.setVisible(False)
        lay_table.addWidget(self.progress_total)

        self.progress_file = QProgressBar()
        self.progress_file.setRange(0, 100)
        self.progress_file.setFormat("Файл: %p%")
        self.progress_file.setVisible(False)
        lay_table.addWidget(self.progress_file)

        lay_table.addWidget(self.status_label)

        self.tabs.addTab(page_table, "Таблица")

    def _build_comparison_tab_main(self) -> None:
        """Построить вкладку Сравнение (используя ComparisonMixin)."""
        page, widgets = self._build_comparison_tab()

        # Сохраняем виджеты
        self.combo_scope = widgets['combo_scope']
        self.combo_metric = widgets['combo_metric']
        self.cb_heatmap = widgets['cb_heatmap']
        self.cb_hints = widgets['cb_hints']
        self._variant_cbs = widgets['variant_cbs']
        self.chart = widgets['chart']
        self.chart_view = widgets['chart_view']
        self.table_heatmap = widgets['table_heatmap']
        self.hints_table = widgets['hints_table']

        # Подключаем сигналы
        self.combo_scope.currentIndexChanged.connect(self._refresh_chart)
        self.combo_scope.currentIndexChanged.connect(self._refresh_heatmap)
        self.combo_metric.currentIndexChanged.connect(self._refresh_chart)
        self.combo_metric.currentIndexChanged.connect(self._refresh_heatmap)
        self.cb_heatmap.toggled.connect(self._toggle_heatmap)
        self.cb_hints.toggled.connect(self._toggle_hints)
        for v, cb in self._variant_cbs.items():
            cb.toggled.connect(self._on_variant_visibility)

        self.tabs.addTab(page, "Сравнение")

    def _build_settings_tab(self) -> None:
        """Построить вкладку Настройки."""
        page_settings = QWidget()
        lay_settings = QHBoxLayout()
        page_settings.setLayout(lay_settings)

        # Форма настроек
        settings_panel, widgets = self._build_settings_form()

        # Сохраняем виджеты
        self.ed_block = widgets['block']
        self.ed_bitrate = widgets['bitrate']
        self.cb_select = widgets['select']
        self.ed_keep_energy = widgets['keep_energy']
        self.ed_seq_keep = widgets['seq_keep']
        self.ed_levels = widgets['levels']
        self.ed_mu = widgets['mu']
        self.ed_bits = widgets['bits']
        self.ed_ra = widgets['ra']
        self.ed_rb = widgets['rb']
        self.cb_preset = widgets['preset']

        # Подключаем сигнал пресета
        self.cb_preset.currentIndexChanged.connect(
            lambda _: apply_preset(self, self.cb_preset.currentText())
        )

        lay_settings.addWidget(settings_panel)

        # Матрица влияния
        matrix_widget = self._build_settings_matrix_widget()
        lay_settings.addWidget(matrix_widget, 1)

        # Подключаем сигнал легенды
        self.cb_matrix_legend.toggled.connect(self._toggle_matrix_legend)

        # Подключаем сигналы обновления матрицы
        for ed in (
            self.ed_block, self.ed_bitrate, self.ed_keep_energy,
            self.ed_seq_keep, self.ed_levels, self.ed_mu,
            self.ed_bits, self.ed_ra, self.ed_rb
        ):
            try:
                ed.editingFinished.connect(self._update_settings_matrix_table)
            except Exception:
                pass

        self.cb_select.currentIndexChanged.connect(
            lambda _: self._update_settings_matrix_table()
        )
        self.cb_preset.currentIndexChanged.connect(
            lambda _: self._update_settings_matrix_table()
        )

        self.tabs.addTab(page_settings, "Настройки")

    def _build_player_tab_main(self) -> None:
        """Построить вкладку Плеер."""
        page_player, widgets = self._build_player_tab()

        # Сохраняем виджеты
        self.player_file_edit = widgets['player_file_edit']
        self.btn_browse_player = widgets['btn_browse_player']
        self.player_info_label = widgets['player_info_label']
        self.btn_play = widgets['btn_play']
        self.btn_pause = widgets['btn_pause']
        self.btn_stop = widgets['btn_stop']
        self.volume_slider = widgets['volume_slider']
        self.volume_label = widgets['volume_label']
        self.position_label = widgets['position_label']
        self.position_slider = widgets['position_slider']
        self.duration_label = widgets['duration_label']

        # Подключаем сигналы
        self.btn_browse_player.clicked.connect(self.on_browse_player_file)
        self.btn_play.clicked.connect(self.on_player_play)
        self.btn_pause.clicked.connect(self.on_player_pause)
        self.btn_stop.clicked.connect(self.on_player_stop)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        self.position_slider.sliderMoved.connect(self.on_position_slider_moved)

        # Подключаем сигналы плеера
        self._media_player.positionChanged.connect(self.on_player_position_changed)
        self._media_player.durationChanged.connect(self.on_player_duration_changed)
        self._media_player.playbackStateChanged.connect(self.on_player_state_changed)
        self._media_player.errorChanged.connect(self.on_player_error)

        # Панели файлов
        source_widget, output_widget, files_widgets = self._build_files_panels()

        # Сохраняем виджеты файлов
        self.source_files_list = files_widgets['source_files_list']
        self.btn_refresh_source = files_widgets['btn_refresh_source']
        self.btn_add_source = files_widgets['btn_add_source']
        self.output_files_list = files_widgets['output_files_list']
        self.btn_refresh_output = files_widgets['btn_refresh_output']
        self.btn_open_folder = files_widgets['btn_open_folder']

        # Подключаем сигналы файлов
        self.source_files_list.doubleClicked.connect(self.on_source_file_double_clicked)
        self.source_files_list.itemSelectionChanged.connect(self.on_source_file_selected)
        self.btn_refresh_source.clicked.connect(self.refresh_source_files_list)
        self.btn_add_source.clicked.connect(self.on_add_source_file)
        self.output_files_list.doubleClicked.connect(self.on_output_file_double_clicked)
        self.btn_refresh_output.clicked.connect(self.refresh_output_files_list)
        self.btn_open_folder.clicked.connect(self.on_open_output_folder)

        # Добавляем панели файлов
        files_splitter = QHBoxLayout()
        files_splitter.addWidget(source_widget, 1)
        files_splitter.addWidget(output_widget, 1)

        # Добавляем к странице плеера
        player_layout = page_player.layout()
        player_layout.addLayout(files_splitter, 1)

        self.tabs.addTab(page_player, "Плеер")

    def _build_spectrum_tab_main(self) -> None:
        """Построить вкладку Спектр."""
        page_spectrum, widgets = self._build_spectrum_tab()

        # Сохраняем виджеты
        self.spectrum_source_edit = widgets['spectrum_source_edit']
        self.btn_browse_spectrum_source = widgets['btn_browse_spectrum_source']
        self.spectrum_files_table = widgets['spectrum_files_table']
        self.btn_refresh_spectrum = widgets['btn_refresh_spectrum']
        self.btn_compare_spectrum = widgets['btn_compare_spectrum']
        self.btn_select_all_spectrum = widgets['btn_select_all_spectrum']
        
        # График (интерактивный или QChart fallback)
        if 'spectrum_chart_widget' in widgets:
            self.spectrum_chart_widget = widgets['spectrum_chart_widget']
            self.spectrum_chart = None
            self.spectrum_chart_view = None
        else:
            self.spectrum_chart = widgets.get('spectrum_chart')
            self.spectrum_chart_view = widgets.get('spectrum_chart_view')
            self.spectrum_chart_widget = None

        # Подключаем сигналы
        self.btn_browse_spectrum_source.clicked.connect(self.on_browse_spectrum_source)
        self.btn_refresh_spectrum.clicked.connect(self.refresh_spectrum_files_list)
        self.btn_compare_spectrum.clicked.connect(self.on_compare_spectrum)
        self.btn_select_all_spectrum.clicked.connect(self.on_select_all_spectrum)

        self.tabs.addTab(page_spectrum, "Спектр")

    def _initialize_ui(self) -> None:
        """Инициализация UI после построения."""
        # Применяем современный дизайн через Design System
        self.setStyleSheet(get_global_stylesheet())
        logger.info("Applied modern design system")
        
        # Применяем пресет
        apply_preset(self, "Стандартный")

        # Обновляем матрицу
        self._update_settings_matrix_table()

        # Заполняем подсказки
        self._fill_metric_hints()

        # Обновляем список файлов
        self.refresh_output_files_list()

        # Начальная видимость
        self._toggle_heatmap(self.cb_heatmap.isChecked())
        self._toggle_hints(self.cb_hints.isChecked())

    # =========================================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # =========================================================================

    def on_browse(self) -> None:
        """Диалог выбора WAV-файла."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите WAV-файл", str(PROJECT_ROOT), "WAV файлы (*.wav)"
        )
        if path:
            self.path_edit.setText(path)
            self.btn_convert.setEnabled(True)

    def on_browse_dataset(self) -> None:
        """Диалог выбора папки с данными."""
        # Всегда открываем диалог с понятной начальной папкой
        if self._dataset_folder and os.path.isdir(self._dataset_folder):
            start_dir = self._dataset_folder
        elif DEFAULT_TEST_DATA_DIR.exists():
            start_dir = str(DEFAULT_TEST_DATA_DIR)
        else:
            start_dir = str(Path.home())
            
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку с WAV-файлами",
            start_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self._dataset_folder = folder
            self.dataset_edit.setText(folder)
            wavs = glob.glob(os.path.join(folder, "**", "*.wav"), recursive=True)
            self.btn_batch.setToolTip(
                f"Обработать {len(wavs)} WAV-файлов из {folder}"
            )

    def on_convert(self) -> None:
        """Запустить обработку выбранного файла."""
        path = self.path_edit.text().strip()
        if not path:
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "Ошибка", "Файл не найден")
            return
        self._start_worker([path], dataset_root=None)

    def on_run_dataset(self) -> None:
        """Запустить пакетную обработку."""
        dataset_root = self._dataset_folder
        if not dataset_root:
            dataset_root = str(DEFAULT_TEST_DATA_DIR)

        if not os.path.isdir(dataset_root):
            QMessageBox.warning(
                self,
                "Папка не найдена",
                f"Папка '{dataset_root}' не существует.\n"
                "Выберите папку с WAV-файлами.",
            )
            return

        wavs = sorted(
            glob.glob(os.path.join(dataset_root, "**", "*.wav"), recursive=True)
        )

        if not wavs:
            QMessageBox.information(
                self,
                "Нет файлов",
                f"В папке '{dataset_root}' не найдено WAV-файлов.\n\n"
                "Структура должна быть:\n"
                "  папка/\n"
                "  ├── жанр1/\n"
                "  │   ├── track1.wav\n"
                "  │   └── track2.wav\n"
                "  └── жанр2/\n"
                "      └── track3.wav",
            )
            return

        # Информация о жанрах
        genres = set()
        for w in wavs:
            rel = os.path.relpath(w, dataset_root)
            parts = rel.split(os.sep)
            if len(parts) > 1:
                genres.add(parts[0])

        genre_info = f" ({len(genres)} жанров)" if genres else ""
        self._log_emitter.log_line.emit(
            f"Найдено {len(wavs)} WAV-файлов{genre_info} в {dataset_root}"
        )

        self._start_worker(wavs, dataset_root=dataset_root)

    def on_export_xlsx(self) -> None:
        """Экспортировать результаты в Excel файл."""
        if not self._results:
            QMessageBox.information(
                self,
                "Нет данных",
                "Нет результатов для экспорта.\n"
                "Сначала обработайте аудио файлы.",
            )
            return

        if not is_export_available():
            QMessageBox.warning(
                self,
                "Недоступно",
                "Для экспорта в Excel необходимо установить библиотеку openpyxl.\n\n"
                "Установите: pip install openpyxl",
            )
            return

        default_name = generate_export_filename("audio_analysis")
        default_path = os.path.join(str(OUTPUT_DIR), default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить результаты",
            default_path,
            "Excel файлы (*.xlsx)",
        )

        if not file_path:
            return

        if not file_path.lower().endswith(".xlsx"):
            file_path += ".xlsx"

        success = export_results_to_xlsx(self._results, file_path)

        if success:
            QMessageBox.information(
                self, "Успешно", f"Результаты сохранены в:\n{file_path}"
            )
            self._log_emitter.log_line.emit(f"Экспорт завершён: {file_path}")
        else:
            QMessageBox.warning(
                self, "Ошибка", "Не удалось сохранить файл.\nПодробнее см. в логах."
            )

    def closeEvent(self, event) -> None:
        """Аккуратно завершить поток при закрытии."""
        logger.info("closeEvent called")
        
        # Сначала отключаем log handler и emitter чтобы избежать сигналов из Worker
        try:
            if hasattr(self, '_qt_log_handler') and self._qt_log_handler:
                self._qt_log_handler.disable()
        except Exception:
            pass
        try:
            if hasattr(self, '_log_emitter') and self._log_emitter:
                self._log_emitter.disable()
        except Exception:
            pass
        
        try:
            if self._thread and self._thread.isRunning():
                logger.info("Thread is running, requesting stop...")
                
                # Блокируем сигналы Worker для предотвращения race conditions
                if self._worker:
                    try:
                        self._worker.blockSignals(True)
                    except Exception:
                        pass
                
                # Сначала просим Worker остановиться
                if self._worker:
                    try:
                        self._worker.cancel()
                    except Exception as e:
                        logger.error("Error canceling worker: %s", e)
                
                # Запрашиваем остановку потока
                self._thread.quit()
                
                # Ждём завершения
                if not self._thread.wait(3000):
                    logger.warning("Thread did not finish, terminating...")
                    self._thread.terminate()
                    self._thread.wait(1000)
                
                # Отключаем все сигналы Worker
                if self._worker:
                    try:
                        self._worker.disconnect()
                    except Exception:
                        pass
                
                # ВАЖНО: не вызываем deleteLater() для Worker!
                # Worker будет удалён автоматически.
                # deleteLater() на объекте из другого потока вызывает краш.
                self._worker = None
                self._thread = None
                logger.info("Thread stopped")
        except Exception as e:
            logger.error("Error in closeEvent: %s", e)
        
        # Останавливаем плеер
        try:
            if hasattr(self, '_media_player') and self._media_player:
                self._media_player.stop()
        except Exception:
            pass
            
        super().closeEvent(event)

    def _on_toggle_logs(self, checked: bool) -> None:
        """Показать/скрыть панель логов."""
        self.logs_tabs.setVisible(bool(checked))
    
    def _on_table_file_analyzed(self, path: str) -> None:
        """Обработать запрос анализа файла из таблицы.
        
        Параметры:
        ----------
        path : str
            Путь к файлу для анализа
        """
        # Переключаемся на вкладку Спектр и устанавливаем файл
        try:
            self.tabs.setCurrentIndex(4)  # Вкладка Спектр
            self.spectrum_source_edit.setText(path)
            self.spectrum_source_edit.setToolTip(path)
            self.refresh_spectrum_files_list()
            self._log_emitter.log_line.emit(f"📊 Анализ файла: {os.path.basename(path)}")
        except Exception as e:
            logger.error(f"Error analyzing file from table: {e}")

    # =========================================================================
    # ФАЗА 3: КОМПОНЕНТЫ UI/UX
    # =========================================================================

    def _init_phase3_components(self) -> None:
        """Инициализировать компоненты Фазы 3."""
        # Shortcut Manager
        self._shortcut_manager = ShortcutManager(self)
        self._setup_shortcuts()

        # Toast Manager (создаётся после построения UI)
        self._toast_manager: Optional[ToastManager] = None

        # Onboarding Manager
        config_path = PROJECT_ROOT / "config" / "user_settings.json"
        self._onboarding_manager = OnboardingManager(self, config_path)
        self._onboarding_manager.completed.connect(self._on_onboarding_completed)

        logger.info("Phase 3 components initialized")

    def _setup_shortcuts(self) -> None:
        """Настроить горячие клавиши."""
        # Регистрируем обработчики для стандартных действий
        self._shortcut_manager.register(
            self, "file.open", self.on_browse
        )
        self._shortcut_manager.register(
            self, "file.export_xlsx", self.on_export_xlsx
        )
        self._shortcut_manager.register(
            self, "file.batch", self.on_run_dataset
        )
        self._shortcut_manager.register(
            self, "analysis.run", self.on_convert
        )
        self._shortcut_manager.register(
            self, "view.dashboard", lambda: self.tabs.setCurrentIndex(0)
        )
        self._shortcut_manager.register(
            self, "view.table", lambda: self.tabs.setCurrentIndex(1)
        )
        self._shortcut_manager.register(
            self, "view.comparison", lambda: self.tabs.setCurrentIndex(2)
        )
        self._shortcut_manager.register(
            self, "view.settings", lambda: self.tabs.setCurrentIndex(3)
        )
        self._shortcut_manager.register(
            self, "view.logs", lambda: self.show_logs_cb.toggle()
        )
        self._shortcut_manager.register(
            self, "help.shortcuts", self._show_shortcuts_dialog
        )

        logger.debug("Shortcuts configured")

    def _build_dashboard_tab(self) -> None:
        """Построить вкладку Dashboard (Фаза 3)."""
        self.dashboard = DashboardWidget()

        # Подключаем сигналы Dashboard
        self.dashboard.open_file_requested.connect(self.on_browse)
        self.dashboard.batch_process_requested.connect(self.on_run_dataset)
        self.dashboard.compare_requested.connect(self._open_compare_wizard)
        self.dashboard.file_selected.connect(self._on_dashboard_file_selected)
        self.dashboard.methods_changed.connect(self._on_methods_changed)

        self.tabs.addTab(self.dashboard, "🏠 Dashboard")
    
    def _on_methods_changed(self, methods: List[str]) -> None:
        """Обработать изменение выбранных методов."""
        self._enabled_methods = methods
        logger.info(f"Enabled methods changed: {methods}")

    def _open_compare_wizard(self) -> None:
        """Открыть мастер сравнения файлов."""
        wizard = CompareWizard(self)
        wizard.files_selected.connect(self._on_wizard_files_selected)
        wizard.exec()

    def _on_wizard_files_selected(self, files: List[str]) -> None:
        """Обработать выбор файлов в мастере."""
        if files:
            self._log_emitter.log_line.emit(
                f"📊 Выбрано файлов для сравнения: {len(files)}"
            )
            # TODO: Запустить сравнительный анализ

    def _on_dashboard_file_selected(self, filename: str) -> None:
        """Обработать выбор файла на Dashboard."""
        self.path_edit.setText(filename)
        self.btn_convert.setEnabled(True)
        self.tabs.setCurrentIndex(1)  # Переключаемся на Таблицу

    def _show_shortcuts_dialog(self) -> None:
        """Показать диалог со списком горячих клавиш."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Горячие клавиши")
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(dialog)

        # Заголовок
        title = QLabel("Список горячих клавиш")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 16px;")
        layout.addWidget(title)

        # Таблица с горячими клавишами
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Действие", "Комбинация"])
        table.horizontalHeader().setStretchLastSection(True)

        actions = self._shortcut_manager.get_all_actions()
        table.setRowCount(len(actions))

        for i, action in enumerate(actions):
            table.setItem(i, 0, QTableWidgetItem(action.name))
            table.setItem(i, 1, QTableWidgetItem(action.display_text))

        layout.addWidget(table)

        # Кнопка закрытия
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec()

    def _on_onboarding_completed(self) -> None:
        """Обработать завершение онбординга."""
        self._show_toast("Добро пожаловать в AudioAnalyzer!", ToastType.SUCCESS)

    def _show_toast(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO
    ) -> None:
        """Показать toast-уведомление.

        Параметры:
        ----------
        message : str
            Текст уведомления
        toast_type : ToastType
            Тип уведомления
        """
        if self._toast_manager is None:
            from .components.toast import ToastPosition
            self._toast_manager = ToastManager(
                self,
                position=ToastPosition.TOP_RIGHT
            )

        self._toast_manager.show(message, toast_type)

    def showEvent(self, event) -> None:
        """Обработать показ окна."""
        super().showEvent(event)

        # Онбординг отключён по умолчанию для предотвращения
        # проблем с оверлеем на Linux (независимое окно может
        # перекрыть интерфейс чёрным экраном).
        # Для ручного запуска используйте: self._onboarding_manager.start(force=True)
        # QTimer.singleShot(500, self._check_onboarding)

    def _check_onboarding(self) -> None:
        """Проверить нужно ли запустить онбординг."""
        # Показываем онбординг только если это первый запуск
        # и пользователь не завершил его ранее
        if not self._onboarding_manager.is_completed():
            self._onboarding_manager.start()

    # =========================================================================
    # УПРАВЛЕНИЕ НАСТРОЙКАМИ
    # =========================================================================

    def _current_settings(self) -> Dict[str, Any]:
        """Получить текущие настройки из виджетов."""
        def fnum(ed, cast):
            try:
                return cast(ed.text().strip())
            except Exception:
                return cast(type(cast())())

        return {
            "block_size": fnum(self.ed_block, int),
            "bitrate": self.ed_bitrate.text().strip() or "192k",
            "select_mode": self.cb_select.currentData() or "none",
            "keep_energy_ratio": fnum(self.ed_keep_energy, float),
            "sequency_keep_ratio": fnum(self.ed_seq_keep, float),
            "levels": fnum(self.ed_levels, int),
            "mu": fnum(self.ed_mu, float),
            "bits": fnum(self.ed_bits, int),
            "rosen_alpha": fnum(self.ed_ra, float),
            "rosen_beta": fnum(self.ed_rb, float),
            "enabled_methods": self._enabled_methods,  # Список выбранных методов или None
        }


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    "MainWindow",
    "SourceFilesDialog",
    "PROJECT_ROOT",
    "OUTPUT_DIR",
    "DEFAULT_TEST_DATA_DIR",
]
