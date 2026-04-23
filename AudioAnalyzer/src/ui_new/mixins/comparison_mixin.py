"""
Миксин для визуализации сравнения методов.

Содержит:
- Построение вкладки Сравнение
- График сравнения (Bar Chart)
- Тепловая карта (Heatmap)
- Таблица подсказок по метрикам

Использование:
    class MainWindow(ComparisonMixin, QMainWindow):
        ...
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..constants import METRIC_KEYS, SCOPE_OPTIONS, VARIANTS

logger = logging.getLogger("ui_new.mixins.comparison")


class ComparisonMixin:
    """Миксин для визуализации сравнения методов.

    Предоставляет:
    - Построение вкладки Сравнение
    - Обновление графиков и heatmap
    - Управление видимостью методов

    Требуемые атрибуты в классе-носителе:
    - self._results: List[ResultRow]
    - self._variant_visible: Dict[str, bool]
    """

    # =========================================================================
    # ПОСТРОЕНИЕ ВКЛАДКИ СРАВНЕНИЕ
    # =========================================================================

    def _build_comparison_tab(self) -> Tuple[QWidget, Dict[str, Any]]:
        """Построить вкладку Сравнение.

        Возвращает:
        -----------
        Tuple[QWidget, Dict[str, Any]]
            (виджет вкладки, словарь виджетов)
        """
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)

        widgets = {}

        # -------------------------------------------------------------------------
        # Панель управления
        # -------------------------------------------------------------------------
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Сравнить:"))

        # Combobox для области сравнения
        widgets['combo_scope'] = QComboBox()
        for text, data in SCOPE_OPTIONS:
            widgets['combo_scope'].addItem(text, data)
        # Сигналы будут подключены в MainWindow
        ctrl.addWidget(widgets['combo_scope'])

        ctrl.addWidget(QLabel("Метрика:"))
        widgets['combo_metric'] = QComboBox()
        for key, (title, _, _) in METRIC_KEYS.items():
            widgets['combo_metric'].addItem(title, key)
        ctrl.addWidget(widgets['combo_metric'])

        # Чекбоксы
        widgets['cb_heatmap'] = QCheckBox("Heatmap")
        widgets['cb_heatmap'].setChecked(True)
        ctrl.addWidget(widgets['cb_heatmap'])

        widgets['cb_hints'] = QCheckBox("Подсказки")
        widgets['cb_hints'].setChecked(True)
        ctrl.addWidget(widgets['cb_hints'])

        ctrl.addStretch(1)
        layout.addLayout(ctrl)

        # -------------------------------------------------------------------------
        # Панель методов
        # -------------------------------------------------------------------------
        left_w = QWidget()
        left_l = QVBoxLayout()
        left_w.setLayout(left_l)
        left_l.addWidget(QLabel("Методы:"))

        widgets['variant_cbs'] = {}
        for v in VARIANTS:
            cb = QCheckBox(v)
            cb.setChecked(True)
            widgets['variant_cbs'][v] = cb
            left_l.addWidget(cb)
        left_l.addStretch(1)

        # -------------------------------------------------------------------------
        # График
        # -------------------------------------------------------------------------
        widgets['chart'] = QChart()
        widgets['chart'].setTitle("Сравнение методов")
        widgets['chart'].legend().setVisible(True)
        widgets['chart_view'] = QChartView(widgets['chart'])

        row_chart = QHBoxLayout()
        row_chart.addWidget(left_w)
        row_chart.addWidget(widgets['chart_view'], 1)
        layout.addLayout(row_chart, 1)

        # -------------------------------------------------------------------------
        # Heatmap
        # -------------------------------------------------------------------------
        widgets['table_heatmap'] = QTableWidget(0, 0)
        layout.addWidget(widgets['table_heatmap'])

        # -------------------------------------------------------------------------
        # Подсказки
        # -------------------------------------------------------------------------
        widgets['hints_table'] = QTableWidget(0, 3)
        widgets['hints_table'].setHorizontalHeaderLabels(
            ["Метрика", "Краткое описание", "Что отражает"]
        )
        widgets['hints_table'].horizontalHeader().setStretchLastSection(True)
        layout.addWidget(widgets['hints_table'])

        return page, widgets

    # =========================================================================
    # ОБНОВЛЕНИЕ ГРАФИКА
    # =========================================================================

    def _refresh_chart(self) -> None:
        """Перестроить график сравнения.

        Создаёт столбчатую диаграмму для сравнения методов по выбранной метрике.
        Группировка данных: сводка (все треки), по жанрам, по отдельным трекам.
        """
        logger.info("_refresh_chart called, results_count: %d", len(self._results))

        metric_key = self.combo_metric.currentData() or "lsd"
        title, key, _ = METRIC_KEYS.get(metric_key, METRIC_KEYS["lsd"])
        scope = self.combo_scope.currentData() or "summary"
        logger.info("metric_key=%s, scope=%s, attr_key=%s", metric_key, scope, key)

        # Удаляем старые оси
        for ax in list(self.chart.axes()):
            try:
                self.chart.removeAxis(ax)
            except Exception:
                pass

        # Группируем данные по категориям
        groups: Dict[str, Dict[str, List[float]]] = {}
        for r in self._results:
            if not self._variant_visible.get(r.variant, True):
                continue
            grp = (
                "Все треки"
                if scope == "summary"
                else (r.genre or "—")
                if scope == "genres"
                else r.source
            )
            groups.setdefault(grp, {}).setdefault(r.variant, []).append(
                getattr(r, key)
            )

        # Строим диаграмму
        self.chart.removeAllSeries()
        categories = list(groups.keys())

        if not categories:
            self.chart.setTitle(f"Сравнение: {title} (нет данных)")
            return

        series = QBarSeries()
        variants_in_data = {v for g in groups.values() for v in g.keys()}

        for v in VARIANTS:
            if v not in variants_in_data:
                continue
            if not self._variant_visible.get(v, True):
                continue

            bs = QBarSet(v)
            for g in categories:
                vals = groups.get(g, {}).get(v, [])
                vals_f = [
                    float(x)
                    for x in vals
                    if isinstance(x, (int, float)) and math.isfinite(float(x))
                ]
                avg = sum(vals_f) / len(vals_f) if vals_f else 0.0
                bs << avg
            series.append(bs)

        self.chart.addSeries(series)

        # Включаем метки значений
        try:
            series.setLabelsVisible(True)
        except Exception:
            pass

        # Ось X (категории)
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.setAxisX(axis_x, series)

        # Ось Y - вычисляем диапазон
        all_vals = []
        for s in series.barSets():
            try:
                all_vals += [s.at(i) for i in range(len(categories))]
            except Exception:
                pass

        if not all_vals:
            all_vals = [0.0, 1.0]

        ymin = min(all_vals) if all_vals else 0.0
        ymax = max(all_vals) if all_vals else 1.0
        if ymin == ymax:
            ymax = ymin + 1.0

        padding = 0.15 * abs(ymax - ymin) if ymax != ymin else 0.1
        axis_y = QValueAxis()
        axis_y.setRange(ymin - 0.05 * abs(ymax - ymin), ymax + padding)
        axis_y.setLabelsVisible(True)

        self.chart.addAxis(axis_y, Qt.AlignLeft)
        self.chart.setAxisY(axis_y, series)

        self.chart.setTitle(f"Сравнение: {title}")
        self.chart.legend().setVisible(True)

    # =========================================================================
    # ОБНОВЛЕНИЕ HEATMAP
    # =========================================================================

    def _refresh_heatmap(self) -> None:
        """Перестроить тепловую карту."""
        scope = self.combo_scope.currentData() or "summary"
        metric_key = self.combo_metric.currentData() or "lsd"
        _, key, _ = METRIC_KEYS.get(metric_key, METRIC_KEYS["lsd"])

        # Определяем категории
        categories = set()
        for r in self._results:
            if scope == "summary":
                categories.add("Все треки")
            elif scope == "genres":
                categories.add(r.genre or "—")
            else:
                categories.add(r.source)

        categories = sorted(categories)
        variants = [v for v in VARIANTS if self._variant_visible.get(v, True)]

        # Настраиваем таблицу
        self.table_heatmap.setRowCount(len(variants))
        self.table_heatmap.setColumnCount(len(categories))
        self.table_heatmap.setHorizontalHeaderLabels(categories)
        self.table_heatmap.setVerticalHeaderLabels(variants)

        # Заполняем значениями
        for vi, variant in enumerate(variants):
            for ci, cat in enumerate(categories):
                vals = []
                for r in self._results:
                    if r.variant != variant:
                        continue
                    if scope == "summary":
                        vals.append(getattr(r, key))
                    elif scope == "genres":
                        if (r.genre or "—") == cat:
                            vals.append(getattr(r, key))
                    else:
                        if r.source == cat:
                            vals.append(getattr(r, key))

                vals_f = [
                    float(x)
                    for x in vals
                    if isinstance(x, (int, float)) and math.isfinite(float(x))
                ]
                avg = sum(vals_f) / len(vals_f) if vals_f else float("nan")

                it = QTableWidgetItem(f"{avg:.3f}" if math.isfinite(avg) else "—")
                it.setTextAlignment(Qt.AlignCenter)
                self.table_heatmap.setItem(vi, ci, it)

    # =========================================================================
    # ПЕРЕКЛЮЧЕНИЕ ВИДИМОСТИ
    # =========================================================================

    def _toggle_heatmap(self, visible: bool) -> None:
        """Показать/скрыть heatmap."""
        self.table_heatmap.setVisible(visible)

    def _toggle_hints(self, visible: bool) -> None:
        """Показать/скрыть подсказки."""
        self.hints_table.setVisible(visible)

    def _on_variant_visibility(self) -> None:
        """Обновить видимость методов на графиках."""
        for v, cb in self._variant_cbs.items():
            self._variant_visible[v] = cb.isChecked()
        self._refresh_chart()
        self._refresh_heatmap()

    # =========================================================================
    # ЗАПОЛНЕНИЕ ПОДСКАЗОК
    # =========================================================================

    def _fill_metric_hints(self) -> None:
        """Заполнить таблицу подсказок по метрикам."""
        hints = [
            ("LSD (дБ)", "Log-Spectral Distance", "Расстояние между спектрами, ниже лучше"),
            ("SNR (дБ)", "Signal-to-Noise Ratio", "Отношение сигнал/шум, выше лучше"),
            ("Спектр. сх.", "Spectral Convergence", "Ошибка амплитуд спектра, ниже лучше"),
            ("RMSE", "Root Mean Square Error", "Ошибка во временной области, ниже лучше"),
            ("SI-SDR (дБ)", "Scale-Invariant SDR", "Устойчивый к масштабу SDR, выше лучше"),
            ("Центроид Δ (Гц)", "Spectral Centroid Difference", "Разница центров спектра"),
            ("Косин. сход.", "Cosine Similarity", "Схожесть спектров (0-1), выше лучше"),
            ("STOI", "Short-Time Objective Intelligibility", "Разборчивость речи (0-1), выше лучше"),
            ("PESQ", "Perceptual Evaluation of Speech Quality", "Оценка качества речи (-0.5-4.5)"),
            ("MOS", "Mean Opinion Score", "Средняя оценка мнений (1-5), выше лучше"),
            ("Общий балл", "Aggregate Score", "Комплексная оценка качества, выше лучше"),
        ]

        self.hints_table.setRowCount(len(hints))
        for i, (metric, desc, meaning) in enumerate(hints):
            self.hints_table.setItem(i, 0, QTableWidgetItem(metric))
            self.hints_table.setItem(i, 1, QTableWidgetItem(desc))
            self.hints_table.setItem(i, 2, QTableWidgetItem(meaning))


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "ComparisonMixin",
]
