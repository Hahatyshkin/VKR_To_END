"""
Миксин для спектрального анализа.

Содержит:
- Построение вкладки Спектр
- Выбор исходного файла
- Сравнение спектров с интерактивным графиком

Использование:
    class MainWindow(SpectrumMixin, QMainWindow):
        ...
"""
from __future__ import annotations

import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger("ui_new.mixins.spectrum")


class SpectrumMixin:
    """Миксин для спектрального анализа.

    Предоставляет:
    - Построение вкладки Спектр
    - Сравнение спектров методов с интерактивным графиком

    Требуемые атрибуты в классе-носителе:
    - self._results: List[ResultRow]
    - self._dataset_folder: Optional[str]
    - self.path_edit (QLineEdit)
    - self._log_emitter (UiLogEmitter)
    """

    # =========================================================================
    # ПОСТРОЕНИЕ ВКЛАДКИ СПЕКТР
    # =========================================================================

    def _build_spectrum_tab(self) -> Tuple[QWidget, Dict[str, Any]]:
        """Построить вкладку Спектр.

        Возвращает:
        -----------
        Tuple[QWidget, Dict[str, Any]]
            (виджет вкладки, словарь виджетов)
        """
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)

        widgets = {}

        # Заголовок
        spectrum_header = QLabel("📊 Спектральный анализ")
        spectrum_header.setStyleSheet(
            "font-weight: bold; font-size: 14px; margin: 5px;"
        )
        layout.addWidget(spectrum_header)

        # -------------------------------------------------------------------------
        # Панель выбора файлов
        # -------------------------------------------------------------------------
        spectrum_files_panel = QHBoxLayout()

        # Исходный файл
        spectrum_files_panel.addWidget(QLabel("Исходный:"))
        widgets['spectrum_source_edit'] = QLineEdit()
        widgets['spectrum_source_edit'].setReadOnly(True)
        widgets['spectrum_source_edit'].setPlaceholderText(
            "Выберите исходный файл..."
        )
        spectrum_files_panel.addWidget(widgets['spectrum_source_edit'], 1)

        widgets['btn_browse_spectrum_source'] = QPushButton("Обзор...")
        spectrum_files_panel.addWidget(widgets['btn_browse_spectrum_source'])

        layout.addLayout(spectrum_files_panel)

        # -------------------------------------------------------------------------
        # Таблица файлов для сравнения
        # -------------------------------------------------------------------------
        spectrum_compare_label = QLabel("Выберите методы для сравнения:")
        layout.addWidget(spectrum_compare_label)

        widgets['spectrum_files_table'] = QTableWidget(0, 4)
        widgets['spectrum_files_table'].setHorizontalHeaderLabels(
            ["✓", "Метод", "Файл", "Размер"]
        )
        widgets['spectrum_files_table'].horizontalHeader().setStretchLastSection(
            True
        )
        widgets['spectrum_files_table'].setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(widgets['spectrum_files_table'], 1)

        # -------------------------------------------------------------------------
        # Кнопки управления
        # -------------------------------------------------------------------------
        spectrum_buttons = QHBoxLayout()

        widgets['btn_refresh_spectrum'] = QPushButton("🔄 Обновить список")
        spectrum_buttons.addWidget(widgets['btn_refresh_spectrum'])

        widgets['btn_compare_spectrum'] = QPushButton("📊 Сравнить спектры")
        spectrum_buttons.addWidget(widgets['btn_compare_spectrum'])

        widgets['btn_select_all_spectrum'] = QPushButton("✅ Выбрать все")
        spectrum_buttons.addWidget(widgets['btn_select_all_spectrum'])

        spectrum_buttons.addStretch(1)
        layout.addLayout(spectrum_buttons)

        # -------------------------------------------------------------------------
        # Интерактивный график спектра (pyqtgraph)
        # -------------------------------------------------------------------------
        try:
            from ..widgets.spectrum_widget import InteractiveSpectrumWidget
            
            widgets['spectrum_chart_widget'] = InteractiveSpectrumWidget()
            layout.addWidget(widgets['spectrum_chart_widget'], 2)
            
            # Флаг использования pyqtgraph
            self._use_interactive_spectrum = True
            logger.info("InteractiveSpectrumWidget loaded successfully (pyqtgraph)")
            
        except Exception as e:
            # Fallback на QChart если pyqtgraph недоступен
            logger.warning(f"Could not load InteractiveSpectrumWidget: {e}, using QChart fallback")
            from PySide6.QtCharts import QChart, QChartView
            
            widgets['spectrum_chart'] = QChart()
            widgets['spectrum_chart'].setTitle("Спектральное сравнение")
            widgets['spectrum_chart'].legend().setVisible(True)
            widgets['spectrum_chart_view'] = QChartView(widgets['spectrum_chart'])
            layout.addWidget(widgets['spectrum_chart_view'], 2)
            
            self._use_interactive_spectrum = False

        return page, widgets

    # =========================================================================
    # ВЫБОР ИСХОДНОГО ФАЙЛА
    # =========================================================================

    def on_browse_spectrum_source(self) -> None:
        """Выбрать исходный файл для спектрального анализа.

        Сначала предлагает выбрать из уже обработанных файлов,
        если нет - открывает диалог выбора из файловой системы.
        """
        from ..main_window import PROJECT_ROOT
        from ..main_window import SourceFilesDialog

        # Собираем доступные исходные файлы
        available_sources = self._get_available_source_files()

        if available_sources:
            # Показываем диалог выбора из доступных файлов
            dialog = SourceFilesDialog(self, available_sources)
            if dialog.exec():
                selected_path = dialog.get_selected_path()
                if selected_path == "__BROWSE__":
                    # Пользователь выбрал "Выбрать другой файл"
                    self._browse_spectrum_from_filesystem()
                elif selected_path:
                    self.spectrum_source_edit.setText(selected_path)
                    self.spectrum_source_edit.setToolTip(selected_path)
                    self.refresh_spectrum_files_list()
        else:
            # Нет доступных файлов - открываем диалог
            self._browse_spectrum_from_filesystem()

    def _get_available_source_files(self) -> List[Tuple[str, str]]:
        """Получить список доступных исходных файлов.

        Возвращает список кортежей (имя_файла, путь).
        """
        from ..main_window import OUTPUT_DIR

        sources = {}  # name -> path

        # Из результатов обработки
        for r in self._results:
            if r.source and r.source not in sources:
                # Ищем исходный файл
                base_name = os.path.splitext(r.source)[0]

                possible_paths = [
                    # В директории обработанного файла
                    os.path.join(os.path.dirname(r.path), r.source),
                    # В директории output
                    os.path.join(str(OUTPUT_DIR), r.source),
                    # Исходный WAV в output (с тем же базовым именем)
                    os.path.join(str(OUTPUT_DIR), base_name + '.wav'),
                ]

                # Также ищем в директории данных
                if self._dataset_folder:
                    for root, dirs, files in os.walk(self._dataset_folder):
                        if r.source in files:
                            possible_paths.append(os.path.join(root, r.source))

                for p in possible_paths:
                    if os.path.exists(p):
                        sources[r.source] = p
                        break

        # Из выбранного файла
        current_path = self.path_edit.text().strip()
        if current_path and os.path.exists(current_path):
            name = os.path.basename(current_path)
            sources[name] = current_path

        # Из папки с данными
        if self._dataset_folder and os.path.isdir(self._dataset_folder):
            for root, dirs, files in os.walk(self._dataset_folder):
                for f in files:
                    if f.endswith('.wav') and f not in sources:
                        path = os.path.join(root, f)
                        sources[f] = path

        # Из папки output - ищем исходные WAV файлы (без суффикса метода)
        if os.path.isdir(str(OUTPUT_DIR)):
            for f in os.listdir(str(OUTPUT_DIR)):
                if f.endswith('.wav'):
                    # Проверяем что это не обработанный файл (без суффикса метода)
                    base = os.path.splitext(f)[0]
                    suffixes = ['_fwht', '_fft', '_dct', '_dwt', '_huffman', '_rosenbrock', '_standard', '_std']
                    is_processed = any(base.endswith(s) for s in suffixes)
                    if not is_processed and f not in sources:
                        path = os.path.join(str(OUTPUT_DIR), f)
                        sources[f] = path

        return list(sources.items())

    def _browse_spectrum_from_filesystem(self) -> None:
        """Открыть диалог выбора файла из файловой системы."""
        from ..main_window import PROJECT_ROOT

        start_dir = self._dataset_folder or str(PROJECT_ROOT)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите исходный аудиофайл",
            start_dir,
            "Аудиофайлы (*.wav *.mp3)",
        )
        if path:
            self.spectrum_source_edit.setText(path)
            self.spectrum_source_edit.setToolTip(path)
            self.refresh_spectrum_files_list()

    # =========================================================================
    # СПИСОК ФАЙЛОВ ДЛЯ СРАВНЕНИЯ
    # =========================================================================

    def refresh_spectrum_files_list(self) -> None:
        """Обновить список обработанных файлов для спектрального сравнения."""
        from ..main_window import OUTPUT_DIR

        self.spectrum_files_table.setRowCount(0)

        source_path = self.spectrum_source_edit.text()
        if not source_path or not os.path.exists(source_path):
            return

        # Получаем базовое имя исходного файла
        base_name = os.path.splitext(os.path.basename(source_path))[0]

        # Ищем обработанные файлы
        output_dir = str(OUTPUT_DIR)
        if not os.path.isdir(output_dir):
            return

        # Методы для сравнения (ключ: суффикс файла -> отображаемое имя)
        method_names = {
            'standard': 'Стандартный',
            'std': 'Стандартный',  # альтернативный суффикс
            'fwht': 'FWHT',
            'fft': 'FFT',
            'dct': 'DCT',
            'dwt': 'DWT',
            'huffman': 'Хаффман',
            'rosenbrock': 'Розенброк',
        }

        files = []
        for f in os.listdir(output_dir):
            if f.startswith(base_name + '_') and f.endswith('.mp3'):
                # Извлекаем метод из имени
                method_key = f.replace(base_name + '_', '').replace('.mp3', '')
                method_name = method_names.get(method_key, method_key)

                path = os.path.join(output_dir, f)
                try:
                    size = os.path.getsize(path) / (1024 * 1024)
                    files.append((method_key, method_name, f, size, path))
                except Exception:
                    continue

        # Сортируем по методу
        files.sort(key=lambda x: x[0])

        # Заполняем таблицу
        for method_key, method_name, filename, size, path in files:
            row = self.spectrum_files_table.rowCount()
            self.spectrum_files_table.insertRow(row)

            # Чекбокс
            chk = QCheckBox()
            chk.setChecked(True)
            self.spectrum_files_table.setCellWidget(row, 0, chk)

            # Метод
            self.spectrum_files_table.setItem(
                row, 1, QTableWidgetItem(method_name)
            )

            # Файл
            self.spectrum_files_table.setItem(
                row, 2, QTableWidgetItem(filename)
            )

            # Размер
            self.spectrum_files_table.setItem(
                row, 3, QTableWidgetItem(f"{size:.2f} МБ")
            )

            # Сохраняем путь
            self.spectrum_files_table.item(row, 1).setData(Qt.UserRole, path)
            self.spectrum_files_table.item(row, 1).setData(
                Qt.UserRole + 1, method_key
            )

    # =========================================================================
    # СРАВНЕНИЕ СПЕКТРОВ (ФОНОВАЯ ОБРАБОТКА)
    # =========================================================================

    def on_compare_spectrum(self) -> None:
        """Сравнить спектры выбранных файлов (в фоновом потоке)."""
        source_path = self.spectrum_source_edit.text()
        if not source_path or not os.path.exists(source_path):
            QMessageBox.warning(self, "Ошибка", "Выберите исходный файл")
            return

        # Собираем выбранные файлы
        selected_files = []
        for row in range(self.spectrum_files_table.rowCount()):
            chk = self.spectrum_files_table.cellWidget(row, 0)
            if chk and chk.isChecked():
                item = self.spectrum_files_table.item(row, 1)
                if item:
                    path = item.data(Qt.UserRole)
                    method = item.data(Qt.UserRole + 1)
                    if path and os.path.exists(path):
                        selected_files.append((method, path))

        if not selected_files:
            QMessageBox.warning(
                self, "Ошибка", "Выберите хотя бы один метод для сравнения"
            )
            return

        # Проверяем что уже не идёт обработка
        if hasattr(self, '_spectrum_thread') and self._spectrum_thread and self._spectrum_thread.isRunning():
            QMessageBox.information(self, "Занято", "Спектр уже вычисляется")
            return

        # Запускаем фоновую обработку
        self._start_spectrum_worker(source_path, selected_files)

    def _start_spectrum_worker(
        self, source_path: str, selected_files: List[Tuple[str, str]]
    ) -> None:
        """Запустить фоновое вычисление спектров."""
        from ..widgets.spectrum_worker import SpectrumWorker

        logger.info(f"Starting spectrum worker for {source_path}")

        # Очищаем график
        if self._use_interactive_spectrum:
            self.spectrum_chart_widget.clear_all_curves()
            self.spectrum_chart_widget.set_title("Вычисление спектра...")

        # Создаём поток и worker
        self._spectrum_thread = QThread()
        self._spectrum_worker = SpectrumWorker(source_path, selected_files)
        self._spectrum_worker.moveToThread(self._spectrum_thread)

        # Подключаем сигналы
        self._spectrum_thread.started.connect(self._spectrum_worker.run)
        self._spectrum_worker.progress.connect(self._on_spectrum_progress, Qt.QueuedConnection)
        self._spectrum_worker.spectrum_ready.connect(self._on_spectrum_ready, Qt.QueuedConnection)
        self._spectrum_worker.error.connect(self._on_spectrum_error, Qt.QueuedConnection)
        self._spectrum_worker.finished.connect(self._on_spectrum_finished, Qt.QueuedConnection)

        # Запускаем
        self._spectrum_thread.start()
        self._log_emitter.log_line.emit("▶ Вычисление спектра...")

    def _on_spectrum_progress(self, message: str) -> None:
        """Обработчик прогресса спектра."""
        self._log_emitter.log_line.emit(message)

    def _on_spectrum_ready(self, name: str, freqs: np.ndarray, spectrum_db: np.ndarray) -> None:
        """Обработчик готового спектра - добавляем кривую на график."""
        if not self._use_interactive_spectrum:
            return

        # Цвета для кривых
        colors = [
            (0, 0, 0),        # Исходный - черный
            (255, 0, 0),      # Красный
            (0, 128, 0),      # Зелёный
            (0, 0, 255),      # Синий
            (255, 165, 0),    # Оранжевый
            (128, 0, 128),    # Фиолетовый
            (0, 128, 128),    # Бирюзовый
            (255, 192, 203),  # Розовый
        ]

        # Определяем цвет по имени
        if name == "Исходный":
            color = colors[0]
        else:
            # Считаем кривые и назначаем цвет
            curve_count = len(self.spectrum_chart_widget.get_curve_names())
            color = colors[(curve_count) % len(colors)]

        self.spectrum_chart_widget.add_curve(name, freqs, spectrum_db, color=color)

    def _on_spectrum_error(self, message: str) -> None:
        """Обработчик ошибки спектра."""
        self._log_emitter.log_line.emit(f"⚠ {message}")

    def _on_spectrum_finished(self) -> None:
        """Завершение вычисления спектра."""
        logger.info("Spectrum worker finished")

        # Ждём завершения потока
        if self._spectrum_thread and self._spectrum_thread.isRunning():
            self._spectrum_thread.quit()
            self._spectrum_thread.wait(2000)

        # Очистка
        if self._spectrum_worker:
            try:
                self._spectrum_worker.disconnect()
            except Exception:
                pass
            self._spectrum_worker = None
        self._spectrum_thread = None

        # Финальные действия
        if self._use_interactive_spectrum:
            self.spectrum_chart_widget.reset_zoom()
            self.spectrum_chart_widget.set_title("Спектральное сравнение")

        self._log_emitter.log_line.emit("✅ Спектр построен")

    def _build_interactive_spectrum(
        self,
        source_signal: np.ndarray,
        source_sr: int,
        selected_files: List[Tuple[str, str]]
    ) -> None:
        """Построить интерактивный спектр с pyqtgraph."""
        from ..widgets.spectrum_widget import SpectrumCalculator

        # Очищаем график
        self.spectrum_chart_widget.clear_all_curves()

        # Вычисляем спектр исходного файла
        freqs, spectrum_db = SpectrumCalculator.compute_spectrum_simple(
            source_signal, source_sr
        )

        # Добавляем исходный спектр
        self.spectrum_chart_widget.add_curve(
            "Исходный",
            freqs,
            spectrum_db,
            color=(0, 0, 0)
        )

        self._log_emitter.log_line.emit(
            f"Спектр исходного: {len(freqs)} точек"
        )

        # Цвета для методов
        colors = [
            (255, 0, 0),      # Красный
            (0, 128, 0),      # Зелёный
            (0, 0, 255),      # Синий
            (255, 165, 0),    # Оранжевый
            (128, 0, 128),    # Фиолетовый
            (0, 128, 128),    # Бирюзовый
            (255, 192, 203),  # Розовый
        ]

        # Добавляем спектры обработанных файлов
        for idx, (method, path) in enumerate(selected_files):
            try:
                self._log_emitter.log_line.emit(f"Загрузка {method}: {path}")
                from processing.codecs import decode_audio_to_mono, load_wav_mono

                try:
                    signal, sr = decode_audio_to_mono(path)
                except Exception:
                    signal, sr = load_wav_mono(path)

                freqs, spectrum_db = SpectrumCalculator.compute_spectrum_simple(
                    signal, sr
                )

                color = colors[idx % len(colors)]
                self.spectrum_chart_widget.add_curve(
                    method.upper(),
                    freqs,
                    spectrum_db,
                    color=color
                )

                self._log_emitter.log_line.emit(
                    f"{method}: добавлено {len(freqs)} точек"
                )

            except Exception as e:
                self._log_emitter.log_line.emit(
                    f"Ошибка при анализе {method}: {e}"
                )

        # Сбрасываем масштаб
        self.spectrum_chart_widget.reset_zoom()
        self.spectrum_chart_widget.set_title("Спектральное сравнение")
        self._log_emitter.log_line.emit("Спектр построен успешно")

    def _build_qtchart_spectrum(
        self,
        source_signal: np.ndarray,
        source_sr: int,
        selected_files: List[Tuple[str, str]]
    ) -> None:
        """Построить спектр с QChart (fallback)."""
        from PySide6.QtCharts import QLineSeries, QValueAxis
        from PySide6.QtGui import QPen

        # Очищаем график
        self.spectrum_chart.removeAllSeries()
        for axis in list(self.spectrum_chart.axes()):
            self.spectrum_chart.removeAxis(axis)

        # Вычисляем спектр исходного файла
        source_spectrum = self._compute_spectrum(source_signal, source_sr)
        self._log_emitter.log_line.emit(
            f"Спектр исходного: {len(source_spectrum)} точек"
        )

        # Цвета для графиков
        colors = [
            QColor(0, 0, 0),  # Исходный - черный
            QColor(255, 0, 0),  # Красный
            QColor(0, 128, 0),  # Зелёный
            QColor(0, 0, 255),  # Синий
            QColor(255, 165, 0),  # Оранжевый
            QColor(128, 0, 128),  # Фиолетовый
            QColor(0, 128, 128),  # Бирюзовый
            QColor(255, 192, 203),  # Розовый
        ]

        # Добавляем исходный спектр
        source_series = QLineSeries()
        source_series.setName("Исходный")
        source_series.setColor(colors[0])
        pen = QPen(colors[0])
        pen.setWidth(2)
        source_series.setPen(pen)

        # Нормализуем частоты для отображения
        max_points = 500
        step = max(1, len(source_spectrum) // max_points)

        points_added = 0
        for i in range(0, len(source_spectrum), step):
            freq = i * source_sr / (2 * len(source_spectrum))
            if freq < 20000:
                try:
                    val = 20 * math.log10(max(source_spectrum[i], 1e-10))
                    source_series.append(freq, val)
                    points_added += 1
                except Exception:
                    pass

        if points_added > 0:
            self.spectrum_chart.addSeries(source_series)

        # Добавляем спектры обработанных файлов
        for idx, (method, path) in enumerate(selected_files):
            try:
                self._log_emitter.log_line.emit(f"Загрузка {method}: {path}")
                from processing.codecs import decode_audio_to_mono, load_wav_mono

                try:
                    signal, sr = decode_audio_to_mono(path)
                except Exception:
                    signal, sr = load_wav_mono(path)

                spectrum = self._compute_spectrum(signal, sr)

                series = QLineSeries()
                series.setName(method.upper())
                color = colors[(idx + 1) % len(colors)]
                series.setColor(color)
                pen = QPen(color)
                pen.setWidth(2)
                series.setPen(pen)

                points_added = 0
                for i in range(0, len(spectrum), step):
                    freq = i * sr / (2 * len(spectrum))
                    if freq < 20000:
                        try:
                            val = 20 * math.log10(max(spectrum[i], 1e-10))
                            series.append(freq, val)
                            points_added += 1
                        except Exception:
                            pass

                if points_added > 0:
                    self.spectrum_chart.addSeries(series)

            except Exception as e:
                self._log_emitter.log_line.emit(
                    f"Ошибка при анализе {method}: {e}"
                )

        # Настраиваем оси
        if self.spectrum_chart.series():
            axis_x = QValueAxis()
            axis_x.setTitleText("Частота (Гц)")
            axis_x.setRange(20, 20000)
            self.spectrum_chart.addAxis(axis_x, Qt.AlignBottom)

            axis_y = QValueAxis()
            axis_y.setTitleText("Амплитуда (дБ)")
            all_vals = []
            for series in self.spectrum_chart.series():
                for i in range(series.count()):
                    point = series.at(i)
                    all_vals.append(point.y())

            if all_vals:
                y_min = min(all_vals)
                y_max = max(all_vals)
                margin = 0.1 * (y_max - y_min) if y_max != y_min else 10
                axis_y.setRange(y_min - margin, y_max + margin)

            self.spectrum_chart.addAxis(axis_y, Qt.AlignLeft)

            for series in self.spectrum_chart.series():
                series.attachAxis(axis_x)
                series.attachAxis(axis_y)

            self.spectrum_chart.setTitle("Спектральное сравнение")
            self._log_emitter.log_line.emit("Спектр построен успешно")
        else:
            self._log_emitter.log_line.emit("Нет данных для построения спектра")

    def _compute_spectrum(self, signal: np.ndarray, sr: int) -> np.ndarray:
        """Вычислить спектр сигнала."""
        n = len(signal)
        fft_result = np.fft.rfft(signal)
        spectrum = np.abs(fft_result)
        spectrum = spectrum / n * 2
        return spectrum

    def on_select_all_spectrum(self) -> None:
        """Выбрать все файлы для спектрального сравнения."""
        for row in range(self.spectrum_files_table.rowCount()):
            chk = self.spectrum_files_table.cellWidget(row, 0)
            if chk:
                chk.setChecked(True)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "SpectrumMixin",
]
