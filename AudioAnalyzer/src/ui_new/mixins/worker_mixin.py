"""
Миксин для управления Worker в MainWindow.

Содержит:
- Запуск фоновой обработки
- Обработку результатов
- Управление прогрессом
- Публикацию событий через Event Bus

Использование:
    class MainWindow(WorkerMixin, QMainWindow):
        ...
"""
from __future__ import annotations

import logging
import math
import os
import threading
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QThread, Qt, Slot, QMetaObject, Q_ARG
from PySide6.QtWidgets import QMessageBox, QTableWidgetItem

from ..worker import ResultRow, Worker

# Event Bus integration
from ..events import (
    EventBus,
    EventType,
    ProcessingEvent,
    AnalysisEvent,
    emit_processing_started,
    emit_processing_finished,
    emit_processing_progress,
    emit_processing_error,
    emit_results_updated,
)

logger = logging.getLogger("ui_new.mixins.worker")


class WorkerMixin:
    """Миксин для управления фоновой обработкой.

    Предоставляет:
    - Запуск Worker в отдельном потоке
    - Обработку результатов
    - Управление прогрессом

    Требуемые атрибуты в классе-носителе:
    - self._results: List[ResultRow]
    - self._current_settings() -> Dict[str, Any]
    - self._log_emitter (UiLogEmitter)
    - self.table (QTableWidget)
    - self.progress_total, self.progress_file (QProgressBar)
    - self.status_label (QLabel)
    - self.btn_export_xlsx (QPushButton)
    """

    # =========================================================================
    # УПРАВЛЕНИЕ WORKER
    # =========================================================================

    def _start_worker(
        self, wav_paths: List[str], dataset_root: Optional[str]
    ) -> None:
        """Запустить фоновую обработку.

        Параметры:
        ----------
        wav_paths : List[str]
            Список путей к WAV файлам
        dataset_root : Optional[str]
            Корневая папка набора данных (для определения жанров)
        """
        from ..main_window import OUTPUT_DIR

        logger.info("_start_worker called with %d files", len(wav_paths))

        # Проверка на уже запущенный поток
        if self._thread and self._thread.isRunning():
            QMessageBox.information(self, "Занято", "Обработка уже идёт")
            return

        self._results = []
        # Буфер для накопления результатов из Worker потока
        self._pending_results: List[str] = []
        out_dir = str(OUTPUT_DIR)
        os.makedirs(out_dir, exist_ok=True)

        # Скрываем прогресс до начала
        self.progress_total.setValue(0)
        self.progress_total.setVisible(True)
        self.progress_file.setValue(0)
        self.progress_file.setVisible(True)
        self.table.setSortingEnabled(False)

        # Создаём поток БЕЗ parent - это важно!
        # QThread с parent может вызывать "setParent from different thread" ошибки
        self._thread = QThread()
        self._worker = Worker(
            wav_paths, out_dir, dataset_root, self._current_settings()
        )
        # moveToThread переводит Worker в контекст потока
        self._worker.moveToThread(self._thread)

        # Связываем сигналы
        # ВАЖНО: Для сигналов с данными используем DirectConnection, т.к. QueuedConnection
        # не работает надёжно с moveToThread. Прямое подключение безопасно, если
        # слот только накапливает данные без UI операций.
        self._thread.started.connect(self._worker.run)
        self._worker.result.connect(self._on_worker_result, Qt.DirectConnection)
        self._worker.error.connect(self._on_worker_error, Qt.DirectConnection)
        self._worker.status.connect(self.status_label.setText, Qt.QueuedConnection)
        self._worker.progress_file.connect(self._on_progress_file, Qt.QueuedConnection)
        self._worker.progress_total.connect(self._on_progress_total, Qt.QueuedConnection)
        self._worker.log.connect(self._append_log, Qt.QueuedConnection)
        # finished должен быть QueuedConnection, чтобы выполняться в главном потоке
        self._worker.finished.connect(self._thread.quit, Qt.QueuedConnection)
        self._worker.finished.connect(self._on_worker_finished, Qt.QueuedConnection)

        self._thread.start()
        logger.info("Worker thread started")
        
        # Публикуем событие начала обработки через Event Bus
        emit_processing_started(
            file_count=len(wav_paths),
            source="WorkerMixin._start_worker"
        )

    def _on_worker_error(self, message: str) -> None:
        """Обработать ошибку от Worker.
        
        Публикует событие PROCESSING_ERROR через Event Bus.
        """
        self._append_log(f"Ошибка: {message}")
        
        # Публикуем событие ошибки через Event Bus
        emit_processing_error(
            error_message=message,
            source="WorkerMixin._on_worker_error"
        )

    def _on_worker_finished(self) -> None:
        """Завершение обработки.
        
        Публикует событие PROCESSING_FINISHED через Event Bus.
        """
        logger.info("_on_worker_finished called")
        
        try:
            # Блокируем сигналы от Worker для предотвращения race conditions
            if self._worker:
                try:
                    self._worker.blockSignals(True)
                except Exception:
                    pass
            
            # Обрабатываем все накопленные результаты (теперь в главном потоке!)
            self._process_pending_results()
            
            # Сначала обновляем UI
            self.table.setSortingEnabled(True)
            self.status_label.setText("Готово")
            self.progress_file.setVisible(False)
            self.progress_total.setVisible(False)
            
            # Обновляем список файлов в плеере (с обработкой ошибок)
            try:
                self.refresh_output_files_list()
            except Exception as e:
                logger.error("Error refreshing files list: %s", e)
            
            # Обновляем Dashboard с результатами (с обработкой ошибок)
            try:
                if hasattr(self, 'dashboard') and self.dashboard:
                    self.dashboard.update_results(self._results)
                    # Обновляем время обработки (берём последнее или сумму)
                    if self._results:
                        # Суммируем время всех результатов для корректного отображения
                        total_time = sum(
                            r.time_sec for r in self._results 
                            if r.time_sec is not None and not math.isnan(r.time_sec)
                        )
                        if total_time > 0:
                            self.dashboard.update_processing_time(total_time)
            except Exception as e:
                logger.error("Error updating dashboard: %s", e)
            
            # Ждём завершения потока (он должен был уже остановиться через thread.quit())
            if self._thread and self._thread.isRunning():
                logger.info("Waiting for thread to finish...")
                if not self._thread.wait(3000):  # Ждём максимум 3 секунды
                    logger.warning("Thread did not finish in time, terminating...")
                    self._thread.terminate()
                    self._thread.wait(1000)
                logger.info("Thread finished")
            
            # Отключаем все соединения сигналов Worker
            if self._worker:
                try:
                    self._worker.disconnect()
                except Exception:
                    pass
            
            # Очистка ссылок - ВАЖНО: не вызываем deleteLater() для Worker!
            # Worker будет удалён автоматически когда поток завершится.
            # deleteLater() на объекте из другого потока может вызывать краш.
            self._worker = None
            self._thread = None
            
            # Очищаем буфер
            self._pending_results = []
            
            # Публикуем события через Event Bus
            emit_processing_finished(
                processed_count=len(self._results),
                source="WorkerMixin._on_worker_finished"
            )
            emit_results_updated(
                count=len(self._results),
                source="WorkerMixin._on_worker_finished"
            )
            
            logger.info("Worker cleanup completed successfully")
        except Exception as e:
            logger.error("Error in _on_worker_finished: %s", e)

    # =========================================================================
    # ОБРАБОТКА РЕЗУЛЬТАТОВ
    # =========================================================================

    @Slot(str)
    def _on_worker_result(self, json_payload: str) -> None:
        """Получить результат от Worker.

        ВАЖНО: Этот метод вызывается из Worker потока. Мы только накапливаем
        данные, а обработку откладываем до _on_worker_finished в главном потоке.

        Параметры:
        ----------
        json_payload : str
            JSON-строка с результатами обработки файла
        """
        # DEBUG: print to stdout
        print(f"[MAIN] _on_worker_result called, payload size={len(json_payload)}", flush=True)
        # Просто накапливаем результаты - не трогаем UI!
        self._pending_results.append(json_payload)
        logger.info("_on_worker_result: accumulated result #%d", len(self._pending_results))

    def _process_pending_results(self) -> None:
        """Обработать все накопленные результаты (в главном потоке)."""
        logger.info("_process_pending_results: processing %d results", len(self._pending_results))
        
        for json_payload in self._pending_results:
            try:
                self._process_single_result(json_payload)
            except Exception as e:
                logger.error("Error processing result: %s", e)

    def _process_single_result(self, json_payload: str) -> None:
        """Обработать один результат (безопасно для UI - только в главном потоке)."""
        logger.info("_process_single_result, JSON payload size: %d bytes", len(json_payload))

        try:
            import json
            d = json.loads(json_payload)
            logger.info("Payload parsed from JSON, keys: %s", list(d.keys()))
        except Exception as e:
            logger.error("Failed to parse JSON payload: %s", e)
            return

        source = str(d.get("source", ""))
        genre = d.get("genre")
        results_list = d.get("results", []) or []
        logger.info("Processing results: source=%s, genre=%s, count=%d", source, genre, len(results_list))

        rows: List[ResultRow] = []

        for item in results_list:
            try:
                row = ResultRow(
                    source=source,
                    genre=genre if isinstance(genre, str) else None,
                    variant=str(item.get("variant")),
                    path=str(item.get("path")),
                    size_bytes=int(item.get("size_bytes", 0) or 0),
                    lsd_db=self._safe_float(item.get("lsd_db")),
                    snr_db=self._safe_float(item.get("snr_db")),
                    spec_conv=self._safe_float(item.get("spec_conv")),
                    rmse=self._safe_float(item.get("rmse")),
                    si_sdr_db=self._safe_float(item.get("si_sdr_db")),
                    spec_centroid_diff_hz=self._safe_float(
                        item.get("spec_centroid_diff_hz")
                    ),
                    spec_cosine=self._safe_float(item.get("spec_cosine")),
                    score=self._safe_float(item.get("score")),
                    time_sec=self._safe_float(item.get("time_sec")),
                )
                rows.append(row)
                logger.debug("Created row: variant=%s", row.variant)
            except Exception as e:
                logger.error("Failed to create ResultRow: %s", e)
                continue

        if not rows:
            logger.warning("No rows created from payload")
            return

        logger.info("Adding %d rows to table", len(rows))
        try:
            for r in rows:
                self._results.append(r)
                self._append_table_row(r)

            logger.info("Refreshing chart and heatmap, total results: %d", len(self._results))
            self._refresh_chart()
            self._refresh_heatmap()
        except Exception as e:
            logger.error("Error updating UI with results: %s", e)
    
    def _safe_float(self, value) -> float:
        """Безопасное преобразование в float с обработкой None и NaN."""
        if value is None:
            return float("nan")
        try:
            f = float(value)
            return f if f == f else float("nan")  # NaN check
        except (ValueError, TypeError):
            return float("nan")

    def _append_table_row(self, r: ResultRow) -> None:
        """Добавить строку в таблицу результатов.

        Параметры:
        ----------
        r : ResultRow
            Строка с результатами одного метода
        """
        from ..constants import TABLE_HEADERS

        row = self.table.rowCount()
        self.table.insertRow(row)

        # Включаем кнопку экспорта при появлении данных
        if not self.btn_export_xlsx.isEnabled():
            self.btn_export_xlsx.setEnabled(True)

        def set_col(col: int, text: str, align_right: bool = False):
            it = QTableWidgetItem(text)
            if align_right:
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, col, it)

        from PySide6.QtCore import Qt
        import math

        size_mb = f"{(r.size_bytes or 0) / (1024 * 1024):.3f}"

        def fmt_val(val: float, fmt: str) -> str:
            """Форматировать значение с обработкой NaN."""
            try:
                if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
                    return "—"
                return fmt.format(val)
            except (ValueError, TypeError):
                return "—"

        set_col(0, r.source)
        set_col(1, r.variant)
        set_col(2, size_mb, True)
        set_col(3, fmt_val(r.lsd_db, "{:.3f}"), True)
        set_col(4, fmt_val(r.snr_db, "{:.3f}"), True)
        set_col(5, fmt_val(r.spec_conv, "{:.3f}"), True)
        set_col(6, fmt_val(r.rmse, "{:.5f}"), True)
        set_col(7, fmt_val(r.si_sdr_db, "{:.3f}"), True)
        set_col(8, fmt_val(r.spec_centroid_diff_hz, "{:.3f}"), True)
        set_col(9, fmt_val(r.spec_cosine, "{:.4f}"), True)
        set_col(10, fmt_val(r.score, "{:.4f}"), True)
        set_col(11, fmt_val(r.time_sec, "{:.3f}"), True)
        self.table.setItem(row, 12, QTableWidgetItem(r.path))

    # =========================================================================
    # ПРОГРЕСС
    # =========================================================================

    def _append_log(self, text: str) -> None:
        """Добавить строку в лог.

        Параметры:
        ----------
        text : str
            Текст для добавления
        """
        self.logs_edit.appendPlainText(text)

    def _on_progress_file(self, value: int) -> None:
        """Обновить прогресс файла.

        Параметры:
        ----------
        value : int
            Значение прогресса (0-100)
        """
        self.progress_file.setValue(value)

    def _on_progress_total(self, value: int) -> None:
        """Обновить прогресс набора.

        Параметры:
        ----------
        value : int
            Значение прогресса (0-100)
        """
        self.progress_total.setValue(value)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "WorkerMixin",
]
