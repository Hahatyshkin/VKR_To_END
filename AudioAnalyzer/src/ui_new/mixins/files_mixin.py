"""
Миксин для работы с файлами в MainWindow.

Содержит:
- Управление списком исходных файлов
- Управление списком обработанных файлов
- Очистку папки output
- Публикацию событий через Event Bus

Использование:
    class MainWindow(FilesMixin, QMainWindow):
        ...
"""
from __future__ import annotations

import datetime
import glob
import logging
import os
import platform
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Event Bus integration
from ..events import (
    EventBus,
    EventType,
    FileEvent,
    emit_file_loaded,
    emit_file_processed,
)

logger = logging.getLogger("ui_new.mixins.files")


class FilesMixin:
    """Миксин для работы с файлами.

    Предоставляет:
    - Построение панели файлов (исходные/обработанные)
    - Обновление списков файлов
    - Фильтрацию по исходному файлу
    - Очистку папки output

    Требуемые атрибуты в классе-носителе:
    - self._results: List[ResultRow]
    - self._dataset_folder: Optional[str]
    - self._log_emitter (UiLogEmitter)
    """

    # =========================================================================
    # ПОСТРОЕНИЕ ПАНЕЛИ ФАЙЛОВ
    # =========================================================================

    def _build_files_panels(self) -> Tuple[QWidget, QWidget, Dict[str, Any]]:
        """Построить панели файлов (исходные и обработанные).

        Возвращает:
        -----------
        Tuple[QWidget, QWidget, Dict[str, Any]]
            (source_widget, output_widget, словарь виджетов)
        """
        widgets = {}

        # -------------------------------------------------------------------------
        # Исходные файлы
        # -------------------------------------------------------------------------
        source_column = QVBoxLayout()
        source_header = QLabel("📁 Исходные файлы:")
        source_header.setStyleSheet("font-weight: bold;")
        source_column.addWidget(source_header)

        widgets['source_files_list'] = QTableWidget(0, 2)
        widgets['source_files_list'].setHorizontalHeaderLabels(
            ["Файл", "Размер"]
        )
        widgets['source_files_list'].horizontalHeader().setStretchLastSection(True)
        widgets['source_files_list'].setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        source_column.addWidget(widgets['source_files_list'], 1)

        # Кнопки для исходных файлов
        source_buttons = QHBoxLayout()
        widgets['btn_refresh_source'] = QPushButton("🔄 Обновить")
        source_buttons.addWidget(widgets['btn_refresh_source'])

        widgets['btn_add_source'] = QPushButton("➕ Добавить файл")
        source_buttons.addWidget(widgets['btn_add_source'])
        source_column.addLayout(source_buttons)

        source_widget = QWidget()
        source_widget.setLayout(source_column)

        # -------------------------------------------------------------------------
        # Обработанные файлы
        # -------------------------------------------------------------------------
        output_column = QVBoxLayout()
        output_header = QLabel("📂 Обработанные файлы:")
        output_header.setStyleSheet("font-weight: bold;")
        output_column.addWidget(output_header)

        widgets['output_files_list'] = QTableWidget(0, 3)
        widgets['output_files_list'].setHorizontalHeaderLabels(
            ["Метод", "Размер", "Дата"]
        )
        widgets['output_files_list'].horizontalHeader().setStretchLastSection(True)
        widgets['output_files_list'].setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        output_column.addWidget(widgets['output_files_list'], 1)

        # Кнопки для обработанных файлов
        output_buttons = QHBoxLayout()
        widgets['btn_refresh_output'] = QPushButton("🔄 Обновить")
        output_buttons.addWidget(widgets['btn_refresh_output'])

        widgets['btn_open_folder'] = QPushButton("📂 Открыть папку")
        output_buttons.addWidget(widgets['btn_open_folder'])
        output_column.addLayout(output_buttons)

        output_widget = QWidget()
        output_widget.setLayout(output_column)

        return source_widget, output_widget, widgets

    # =========================================================================
    # ИСХОДНЫЕ ФАЙЛЫ
    # =========================================================================

    def refresh_source_files_list(self) -> None:
        """Обновить список исходных файлов из результатов обработки."""
        from ..main_window import OUTPUT_DIR

        self.source_files_list.setRowCount(0)

        # Собираем уникальные исходные файлы из результатов
        source_files = {}  # name -> (size, path)
        for r in self._results:
            if r.source not in source_files:
                # Ищем исходный файл (поддерживаем оба варианта суффикса)
                source_path = (
                    r.path.replace('_standard.mp3', '.wav')
                    .replace('_std.mp3', '.wav')
                    .replace('_fwht.mp3', '.wav')
                    .replace('_fft.mp3', '.wav')
                    .replace('_dct.mp3', '.wav')
                    .replace('_dwt.mp3', '.wav')
                    .replace('_huffman.mp3', '.wav')
                    .replace('_rosenbrock.mp3', '.wav')
                )

                # Пробуем разные варианты
                possible_paths = [
                    os.path.join(os.path.dirname(r.path), r.source),
                    source_path,
                ]

                actual_path = None
                for p in possible_paths:
                    if os.path.exists(p):
                        actual_path = p
                        break

                if actual_path:
                    try:
                        size = os.path.getsize(actual_path) / (1024 * 1024)
                        source_files[r.source] = (size, actual_path)
                    except Exception:
                        source_files[r.source] = (0, actual_path)

        # Заполняем таблицу
        for name, (size, path) in sorted(source_files.items()):
            row = self.source_files_list.rowCount()
            self.source_files_list.insertRow(row)
            self.source_files_list.setItem(row, 0, QTableWidgetItem(name))
            self.source_files_list.setItem(
                row, 1, QTableWidgetItem(f"{size:.2f} МБ")
            )
            self.source_files_list.item(row, 0).setData(Qt.UserRole, path)

        # Добавляем папку с данными если есть
        if self._dataset_folder and os.path.isdir(self._dataset_folder):
            self._add_source_files_from_dir(self._dataset_folder)

    def _add_source_files_from_dir(self, directory: str) -> None:
        """Добавить исходные файлы из директории."""
        existing = set()
        for row in range(self.source_files_list.rowCount()):
            item = self.source_files_list.item(row, 0)
            if item:
                existing.add(item.text())

        for root, dirs, files in os.walk(directory):
            for f in files:
                if f.endswith('.wav') and f not in existing:
                    path = os.path.join(root, f)
                    try:
                        size = os.path.getsize(path) / (1024 * 1024)
                        row = self.source_files_list.rowCount()
                        self.source_files_list.insertRow(row)
                        self.source_files_list.setItem(row, 0, QTableWidgetItem(f))
                        self.source_files_list.setItem(
                            row, 1, QTableWidgetItem(f"{size:.2f} МБ")
                        )
                        self.source_files_list.item(row, 0).setData(
                            Qt.UserRole, path
                        )
                        existing.add(f)
                    except Exception:
                        continue

    def on_source_file_selected(self) -> None:
        """При выборе исходного файла - фильтруем список обработанных."""
        selected = self.source_files_list.selectedItems()
        if not selected:
            self.refresh_output_files_list()
            return

        row = selected[0].row()
        item = self.source_files_list.item(row, 0)
        if item:
            source_name = item.text()
            self._filter_output_files_by_source(source_name)

    def _filter_output_files_by_source(self, source_name: str) -> None:
        """Фильтровать обработанные файлы по исходному."""
        from ..main_window import OUTPUT_DIR

        self.output_files_list.setRowCount(0)

        # Извлекаем базовое имя без расширения
        base_name = os.path.splitext(source_name)[0]

        output_dir = str(OUTPUT_DIR)
        if not os.path.isdir(output_dir):
            return

        # Ищем файлы с совпадающим базовым именем
        files = []
        for f in os.listdir(output_dir):
            if f.startswith(base_name + '_') and f.endswith('.mp3'):
                path = os.path.join(output_dir, f)
                try:
                    size = os.path.getsize(path) / (1024 * 1024)
                    mtime = datetime.datetime.fromtimestamp(
                        os.path.getmtime(path)
                    )

                    # Извлекаем метод из имени файла
                    parts = f.replace(base_name + '_', '').replace('.mp3', '')
                    method_map = {
                        'standard': 'Стандартный',
                        'std': 'Стандартный',  # альтернативный суффикс
                        'fwht': 'FWHT',
                        'fft': 'FFT',
                        'dct': 'DCT',
                        'dwt': 'DWT',
                        'huffman': 'Хаффман',
                        'rosenbrock': 'Розенброк',
                    }
                    method = method_map.get(parts, parts)

                    files.append((method, size, mtime, path))
                except Exception:
                    continue

        # Сортируем по дате
        files.sort(key=lambda x: x[2], reverse=True)

        # Заполняем таблицу
        for method, size, mtime, path in files:
            row = self.output_files_list.rowCount()
            self.output_files_list.insertRow(row)
            self.output_files_list.setItem(row, 0, QTableWidgetItem(method))
            self.output_files_list.setItem(
                row, 1, QTableWidgetItem(f"{size:.2f} МБ")
            )
            self.output_files_list.setItem(
                row, 2, QTableWidgetItem(mtime.strftime('%Y-%m-%d %H:%M'))
            )
            self.output_files_list.item(row, 0).setData(Qt.UserRole, path)

    def on_source_file_double_clicked(self, index) -> None:
        """Двойной клик по исходному файлу - воспроизвести."""
        row = index.row()
        item = self.source_files_list.item(row, 0)
        if item:
            path = item.data(Qt.UserRole)
            if path and os.path.exists(path):
                self._load_player_file(path)

    def on_add_source_file(self) -> None:
        """Добавить исходный файл вручную."""
        from ..main_window import PROJECT_ROOT

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите исходный аудиофайл",
            str(PROJECT_ROOT),
            "Аудиофайлы (*.wav *.mp3);;WAV файлы (*.wav);;MP3 файлы (*.mp3)",
        )
        if path:
            self._add_source_file_to_list(path)

    def _add_source_file_to_list(self, path: str) -> None:
        """Добавить файл в список исходных.
        
        Также публикует событие FILE_LOADED через Event Bus.
        """
        name = os.path.basename(path)

        # Проверяем на дубликаты
        for row in range(self.source_files_list.rowCount()):
            item = self.source_files_list.item(row, 0)
            if item and item.text() == name:
                return  # Уже есть

        try:
            size = os.path.getsize(path) / (1024 * 1024)
            row = self.source_files_list.rowCount()
            self.source_files_list.insertRow(row)
            self.source_files_list.setItem(row, 0, QTableWidgetItem(name))
            self.source_files_list.setItem(
                row, 1, QTableWidgetItem(f"{size:.2f} МБ")
            )
            self.source_files_list.item(row, 0).setData(Qt.UserRole, path)
            
            # Публикуем событие через Event Bus
            emit_file_loaded(
                path=path,
                file_size=int(size * 1024 * 1024),
                file_type=os.path.splitext(path)[1],
                source="FilesMixin._add_source_file_to_list"
            )
            logger.debug("File added and event published: %s", name)
            
        except Exception as e:
            self._log_emitter.log_line.emit(f"Ошибка добавления файла: {e}")

    # =========================================================================
    # ОБРАБОТАННЫЕ ФАЙЛЫ
    # =========================================================================

    def refresh_output_files_list(self) -> None:
        """Обновить список файлов в папке output."""
        from ..main_window import OUTPUT_DIR

        self.output_files_list.setRowCount(0)

        output_dir = str(OUTPUT_DIR)
        if not os.path.isdir(output_dir):
            return

        # Получаем список файлов
        files = []
        for f in os.listdir(output_dir):
            if f.endswith(('.mp3', '.wav')):
                path = os.path.join(output_dir, f)
                try:
                    size = os.path.getsize(path) / (1024 * 1024)
                    mtime = datetime.datetime.fromtimestamp(
                        os.path.getmtime(path)
                    )
                    files.append((f, size, mtime, path))
                except Exception:
                    continue

        # Сортируем по дате (новые первыми)
        files.sort(key=lambda x: x[2], reverse=True)

        # Заполняем таблицу
        for f, size, mtime, path in files:
            row = self.output_files_list.rowCount()
            self.output_files_list.insertRow(row)
            self.output_files_list.setItem(row, 0, QTableWidgetItem(f))
            self.output_files_list.setItem(
                row, 1, QTableWidgetItem(f"{size:.2f} МБ")
            )
            self.output_files_list.setItem(
                row, 2, QTableWidgetItem(mtime.strftime('%Y-%m-%d %H:%M'))
            )
            # Сохраняем путь в data
            self.output_files_list.item(row, 0).setData(Qt.UserRole, path)

    def on_output_file_double_clicked(self, index) -> None:
        """Двойной клик по файлу в списке - воспроизвести."""
        row = index.row()
        item = self.output_files_list.item(row, 0)
        if item:
            path = item.data(Qt.UserRole)
            if path and os.path.exists(path):
                self._load_player_file(path)

    def on_open_output_folder(self) -> None:
        """Открыть папку output в файловом менеджере."""
        from ..main_window import OUTPUT_DIR

        output_dir = str(OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)

        try:
            if platform.system() == "Windows":
                os.startfile(output_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", output_dir])
            else:  # Linux
                subprocess.run(["xdg-open", output_dir])
        except Exception:
            QMessageBox.information(
                self,
                "Путь к папке",
                f"Папка output:\n{output_dir}",
            )

    # =========================================================================
    # ОЧИСТКА OUTPUT
    # =========================================================================

    def on_clear_output(self) -> None:
        """Очистить папку output."""
        from ..main_window import OUTPUT_DIR

        output_dir = str(OUTPUT_DIR)
        if not os.path.isdir(output_dir):
            QMessageBox.information(
                self, "Папка не найдена", "Папка output не существует."
            )
            return

        # Подсчитываем файлы
        files = [f for f in os.listdir(output_dir) if f.endswith(('.mp3', '.wav'))]
        if not files:
            QMessageBox.information(self, "Пусто", "Папка output уже пуста.")
            return

        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить {len(files)} файл(ов) из папки output?\n"
            "Это действие нельзя отменить.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        # Удаляем файлы
        deleted = 0
        for f in files:
            try:
                os.remove(os.path.join(output_dir, f))
                deleted += 1
            except Exception as e:
                self._log_emitter.log_line.emit(f"Ошибка удаления {f}: {e}")

        # Обновляем список
        self.refresh_output_files_list()

        QMessageBox.information(
            self,
            "Готово",
            f"Удалено {deleted} файл(ов) из папки output.",
        )
        self._log_emitter.log_line.emit(
            f"Очищена папка output: удалено {deleted} файлов"
        )


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "FilesMixin",
]
