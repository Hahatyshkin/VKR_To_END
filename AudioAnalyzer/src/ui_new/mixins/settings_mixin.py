"""
Миксин для панели настроек MainWindow.

Содержит:
- Построение панели настроек (Settings Panel)
- Матрицу влияния параметров на метрики
- Расчёт impact score для каждого метода
- Публикацию событий через Event Bus

Использование:
    class MainWindow(SettingsMixin, QMainWindow):
        ...
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Event Bus integration
from ..events import (
    EventBus,
    EventType,
    SettingsEvent,
    emit_settings_changed,
    emit_theme_changed,
    emit_profile_changed,
)

logger = logging.getLogger("ui_new.mixins.settings")


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

METHOD_HEADERS = [
    ("std", "Стандартный"),
    ("fwht", "FWHT"),
    ("fft", "FFT"),
    ("dct", "DCT"),
    ("dwt", "DWT"),
    ("huff", "Хаффман"),
    ("rb", "Розенброк"),
]

METRICS_COLS = [
    ("lsd", "LSD↓", "Ниже лучше"),
    ("snr", "SNR↑", "Выше лучше"),
    ("rmse", "RMSE↓", "Ниже лучше"),
    ("sisdr", "SI-SDR↑", "Выше лучше"),
    ("spec_conv", "Спектр↓", "Ниже лучше"),
    ("centroid", "Центр↓", "Ниже лучше"),
    ("cosine", "Косин↑", "Выше лучше"),
    ("time", "Время↓", "Ниже лучше"),
    ("size", "Размер↓", "Ниже лучше"),
]

PARAMS_ROWS = [
    ("block_size", "Размер блока", "Размер блока для OLA (2^n)"),
    ("bitrate", "Битрейт MP3", "Битрейт кодирования"),
    ("select_mode", "Режим отбора", "Метод отбора коэффициентов"),
    ("keep_energy", "Доля энергии", "Для режима 'energy'"),
    ("seq_keep", "Доля частот", "Для режима 'lowpass'"),
    ("levels", "DWT уровни", "Число уровней вейвлета"),
    ("mu", "μ (Хаффман)", "Параметр μ-law компандирования"),
    ("bits", "Биты (Хаффман)", "Биты квантования"),
    ("alpha", "α (Розенброк)", "Параметр сглаживания"),
    ("beta", "β (Розенброк)", "Параметр сдвига"),
]


class SettingsMixin:
    """Миксин для панели настроек и матрицы влияния.

    Предоставляет:
    - Методы для создания виджетов настроек
    - Матрицу влияния параметров на метрики
    - Расчёт impact score

    Требуемые атрибуты в классе-носителе:
    - self._current_settings() -> Dict[str, Any]
    - self._log_emitter (UiLogEmitter)
    """

    # =========================================================================
    # ПОСТРОЕНИЕ ПАНЕЛИ НАСТРОЕК
    # =========================================================================

    def _build_settings_form(self) -> Tuple[QWidget, Dict[str, QLineEdit]]:
        """Построить форму настроек.

        Возвращает:
        - QWidget с формой настроек
        - Dict с виджетами полей ввода
        """
        from ..presets import PRESET_NAMES, apply_preset

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)

        # Поля ввода
        widgets = {}

        # Размер блока
        widgets['block'] = QLineEdit("2048")
        widgets['block'].setMaximumWidth(160)
        widgets['block'].setToolTip(
            "Размер блока для OLA (Overlap-Add). "
            "Должен быть степенью двойки (512, 1024, 2048, 4096). "
            "Больше блок = лучше частотное разрешение, но медленнее."
        )

        # Битрейт
        widgets['bitrate'] = QLineEdit("192k")
        widgets['bitrate'].setMaximumWidth(160)
        widgets['bitrate'].setToolTip(
            "Битрейт выходного MP3 файла. "
            "Чем выше, тем лучше качество, но больше размер. "
            "Типичные значения: 128k, 192k, 256k, 320k."
        )

        # Режим отбора
        widgets['select'] = QComboBox()
        widgets['select'].addItem("Без отбора", "none")
        widgets['select'].addItem("По энергии", "energy")
        widgets['select'].addItem("Низкочастотный", "lowpass")
        widgets['select'].setToolTip(
            "Режим отбора коэффициентов:\n"
            "• Без отбора — полная реконструкция\n"
            "• По энергии — сохранение доли энергии (сжатие)\n"
            "• Низкочастотный — обрезание высоких частот (фильтрация)"
        )

        # Доля энергии
        widgets['keep_energy'] = QLineEdit("1.0")
        widgets['keep_energy'].setMaximumWidth(160)
        widgets['keep_energy'].setToolTip(
            "Доля сохраняемой энергии (0.0-1.0) для режима 'По энергии'. "
            "Например, 0.95 = 95% энергии."
        )

        # Доля частот
        widgets['seq_keep'] = QLineEdit("1.0")
        widgets['seq_keep'].setMaximumWidth(160)
        widgets['seq_keep'].setToolTip(
            "Доля сохраняемых низких частот (0.0-1.0) для режима 'Низкочастотный'. "
            "Например, 0.5 = первые 50% частот."
        )

        # DWT уровни
        widgets['levels'] = QLineEdit("4")
        widgets['levels'].setMaximumWidth(160)
        widgets['levels'].setToolTip(
            "Число уровней вейвлет-декомпозиции для DWT (Haar). "
            "Типичные значения: 3-6."
        )

        # μ для Хаффмана
        widgets['mu'] = QLineEdit("255")
        widgets['mu'].setMaximumWidth(160)
        widgets['mu'].setToolTip(
            "Параметр μ для μ-law компандирования (Хаффман-подобный метод). "
            "Типично 255."
        )

        # Биты для Хаффмана
        widgets['bits'] = QLineEdit("8")
        widgets['bits'].setMaximumWidth(160)
        widgets['bits'].setToolTip(
            "Число бит квантования (Хаффман-подобный метод). "
            "Больше бит = выше качество. Типично 8-12."
        )

        # Rosenbrock α
        widgets['ra'] = QLineEdit("0.2")
        widgets['ra'].setMaximumWidth(160)
        widgets['ra'].setToolTip(
            "Параметр α для Розенброк-преобразования. "
            "Контролирует сглаживание."
        )

        # Rosenbrock β
        widgets['rb'] = QLineEdit("1.0")
        widgets['rb'].setMaximumWidth(160)
        widgets['rb'].setToolTip(
            "Параметр β для Розенброк-преобразования. "
            "Контролирует сдвиг."
        )

        # Пресеты
        widgets['preset'] = QComboBox()
        widgets['preset'].addItems(PRESET_NAMES)
        # Сигнал будет подключён в MainWindow

        # Добавляем поля в форму
        form.addRow(QLabel("Пресет:"), widgets['preset'])
        form.addRow(QLabel("Размер блока (2^n):"), widgets['block'])
        form.addRow(QLabel("Битрейт MP3:"), widgets['bitrate'])
        form.addRow(QLabel("Режим отбора:"), widgets['select'])
        form.addRow(QLabel("Доля энергии (0..1):"), widgets['keep_energy'])
        form.addRow(QLabel("Доля частот (0..1):"), widgets['seq_keep'])
        form.addRow(QLabel("DWT уровни:"), widgets['levels'])
        form.addRow(QLabel("μ (Хаффман-подобн.):"), widgets['mu'])
        form.addRow(QLabel("Биты (Хаффман-подобн.):"), widgets['bits'])
        form.addRow(QLabel("Rosenbrock α:"), widgets['ra'])
        form.addRow(QLabel("Rosenbrock β:"), widgets['rb'])

        panel = QWidget()
        panel.setLayout(form)
        panel.setMinimumWidth(380)

        return panel, widgets

    # =========================================================================
    # МАТРИЦА ВЛИЯНИЯ
    # =========================================================================

    def _build_settings_matrix_widget(self) -> QWidget:
        """Построить виджет матрицы влияния.

        Матрица показывает качественное влияние параметров на метрики:
        ↑↑ - существенное улучшение качества
        ↑  - улучшение
        →  - без изменений (стандартные параметры)
        ↓  - ухудшение
        ↓↓ - существенное ухудшение

        Цветовая кодировка: зелёный = улучшение, серый = без изменений,
        красный = ухудшение.
        """
        container = QVBoxLayout()
        container.setSpacing(5)

        # Заголовок матрицы
        matrix_title = QLabel("📊 Матрица влияния параметров")
        matrix_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        container.addWidget(matrix_title)

        # Таблица: строки = методы, столбцы = метрики
        self.table_settings_matrix = QTableWidget(
            len(METHOD_HEADERS) + 1, len(METRICS_COLS) + 1
        )

        # Подсказка для всей таблицы
        self.table_settings_matrix.setToolTip(
            "Матрица влияния параметров на метрики качества.\n\n"
            "Символы:\n"
            "↑↑ — существенное улучшение (зелёный)\n"
            "↑ — улучшение (светло-зелёный)\n"
            "→ — без изменений (серый)\n"
            "↓ — ухудшение (оранжевый)\n"
            "↓↓ — существенное ухудшение (красный)\n\n"
            "Наведите на ячейку для просмотра факторов влияния."
        )

        # Заголовки метрик (столбцы)
        for ci, (_, mlabel, _) in enumerate(METRICS_COLS, start=1):
            it = QTableWidgetItem(mlabel)
            it.setTextAlignment(Qt.AlignCenter)
            self.table_settings_matrix.setItem(0, ci, it)

        # Заголовки методов (строки)
        for ri, (_, mlabel) in enumerate(METHOD_HEADERS, start=1):
            it = QTableWidgetItem(mlabel)
            it.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table_settings_matrix.setItem(ri, 0, it)

        try:
            self.table_settings_matrix.verticalHeader().setVisible(False)
            self.table_settings_matrix.setCornerButtonEnabled(False)
            # Ширина столбцов
            self.table_settings_matrix.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.ResizeToContents
            )
            for i in range(1, len(METRICS_COLS) + 1):
                self.table_settings_matrix.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeMode.ResizeToContents
                )
        except Exception:
            pass

        container.addWidget(self.table_settings_matrix, 1)

        # Чекбокс для показа легенды
        self.cb_matrix_legend = QCheckBox("Показать легенду матрицы")
        self.cb_matrix_legend.setChecked(False)
        # Сигнал будет подключён в MainWindow
        container.addWidget(self.cb_matrix_legend)

        # Таблица легенды (изначально скрыта)
        self.matrix_legend_table = QTableWidget(5, 3)
        self.matrix_legend_table.setHorizontalHeaderLabels(
            ["Символ", "Значение", "Цвет"]
        )
        self.matrix_legend_table.setVisible(False)
        self.matrix_legend_table.setMaximumHeight(150)

        legend_data = [
            ("↑↑", "Существенное улучшение", "🟢 Зелёный"),
            ("↑", "Улучшение", "🟢 Светло-зелёный"),
            ("→", "Без изменений", "⚫ Серый"),
            ("↓", "Ухудшение", "🟠 Оранжевый"),
            ("↓↓", "Существенное ухудшение", "🔴 Красный"),
        ]

        for row, (symbol, meaning, color) in enumerate(legend_data):
            self.matrix_legend_table.setItem(row, 0, QTableWidgetItem(symbol))
            self.matrix_legend_table.setItem(row, 1, QTableWidgetItem(meaning))
            self.matrix_legend_table.setItem(row, 2, QTableWidgetItem(color))

        self.matrix_legend_table.horizontalHeader().setStretchLastSection(True)
        self.matrix_legend_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        container.addWidget(self.matrix_legend_table)

        widget = QWidget()
        widget.setLayout(container)
        return widget

    def _toggle_matrix_legend(self, visible: bool) -> None:
        """Показать/скрыть легенду матрицы."""
        self.matrix_legend_table.setVisible(visible)

    # =========================================================================
    # РАСЧЁТ ВЛИЯНИЯ ПАРАМЕТРОВ
    # =========================================================================

    def _calculate_impact_score(
        self, method: str, metric: str, settings: Dict
    ) -> Tuple[str, str, QColor]:
        """Рассчитать влияние параметров на метрику для метода.

        Параметры:
        ----------
        method : str
            Ключ метода ('std', 'fwht', 'fft', 'dct', 'dwt', 'huff', 'rb')
        metric : str
            Ключ метрики ('lsd', 'snr', 'rmse', etc.)
        settings : Dict
            Текущие настройки обработки

        Возвращает:
        -----------
        Tuple[str, str, QColor]
            (символ, текстовое описание, цвет)
        """
        block_size = settings.get("block_size", 2048)
        bitrate = str(settings.get("bitrate", "192k"))
        select_mode = settings.get("select_mode", "none")
        keep_energy = float(settings.get("keep_energy_ratio", 1.0))
        seq_keep = float(settings.get("sequency_keep_ratio", 1.0))
        levels = int(settings.get("levels", 4))
        mu = float(settings.get("mu", 255))
        bits = int(settings.get("bits", 8))
        alpha = float(settings.get("rosen_alpha", 0.2))
        beta = float(settings.get("rosen_beta", 1.0))

        # Базовые значения
        base_block = 2048
        base_bitrate_kbps = 192

        # Парсинг битрейта
        try:
            bitrate_kbps = int(bitrate.replace('k', '').replace('K', ''))
        except Exception:
            bitrate_kbps = 192

        # Инициализация влияния
        impact = 0.0
        factors = []

        # ========================================
        # РАСЧЁТ ВЛИЯНИЯ ДЛЯ КАЖДОЙ МЕТРИКИ
        # ========================================

        # --- LSD (Log-Spectral Distance) - ниже лучше ---
        if metric == "lsd":
            impact, factors = self._calc_lsd_impact(
                method, bitrate_kbps, base_bitrate_kbps,
                block_size, base_block, select_mode, keep_energy,
                seq_keep, levels, mu, bits, alpha, beta
            )

        # --- SNR (Signal-to-Noise Ratio) - выше лучше ---
        elif metric == "snr":
            impact, factors = self._calc_snr_impact(
                method, bitrate_kbps, base_bitrate_kbps,
                block_size, base_block, select_mode, keep_energy,
                seq_keep, mu, bits
            )

        # --- RMSE - ниже лучше ---
        elif metric == "rmse":
            impact, factors = self._calc_rmse_impact(
                method, bitrate_kbps, base_bitrate_kbps,
                block_size, base_block, select_mode, keep_energy,
                seq_keep, bits
            )

        # --- SI-SDR - выше лучше ---
        elif metric == "sisdr":
            impact, factors = self._calc_sisdr_impact(
                method, bitrate_kbps, base_bitrate_kbps,
                select_mode, keep_energy, seq_keep
            )

        # --- Spectral Convergence - ниже лучше ---
        elif metric == "spec_conv":
            impact, factors = self._calc_spec_conv_impact(
                method, select_mode, keep_energy, seq_keep
            )

        # --- Centroid Δ - ниже лучше ---
        elif metric == "centroid":
            impact, factors = self._calc_centroid_impact(
                method, select_mode, seq_keep
            )

        # --- Cosine Similarity - выше лучше ---
        elif metric == "cosine":
            impact, factors = self._calc_cosine_impact(
                method, bitrate_kbps, base_bitrate_kbps,
                select_mode, keep_energy
            )

        # --- Время обработки - ниже лучше ---
        elif metric == "time":
            impact, factors = self._calc_time_impact(
                method, block_size, base_block, levels
            )

        # --- Размер файла - ниже лучше ---
        elif metric == "size":
            impact, factors = self._calc_size_impact(
                bitrate_kbps, base_bitrate_kbps
            )

        # ========================================
        # ФОРМАТИРОВАНИЕ РЕЗУЛЬТАТА
        # ========================================

        return self._format_impact_result(impact, factors, metric)

    def _calc_lsd_impact(
        self, method, bitrate_kbps, base_bitrate_kbps,
        block_size, base_block, select_mode, keep_energy,
        seq_keep, levels, mu, bits, alpha, beta
    ) -> Tuple[float, List[str]]:
        """Расчёт влияния на LSD (Log-Spectral Distance)."""
        impact = 0.0
        factors = []

        # Битрейт: выше битрейт → ниже LSD (лучше)
        if method != "std":
            bitrate_impact = (bitrate_kbps - base_bitrate_kbps) / base_bitrate_kbps * -1.5
            impact += bitrate_impact
            if abs(bitrate_impact) > 0.1:
                factors.append(f"битрейт:{bitrate_kbps}k")

        # Размер блока
        if method in ("fwht", "fft", "dct", "dwt"):
            block_impact = (block_size - base_block) / base_block * -0.5
            impact += block_impact
            if abs(block_impact) > 0.1:
                factors.append(f"блок:{block_size}")

            # Режим отбора
            if select_mode == "energy" and keep_energy < 1.0:
                energy_impact = (1.0 - keep_energy) * 2.0
                impact += energy_impact
                factors.append(f"энергия:{keep_energy:.0%}")
            elif select_mode == "lowpass" and seq_keep < 1.0:
                lowpass_impact = (1.0 - seq_keep) * 2.5
                impact += lowpass_impact
                factors.append(f"частоты:{seq_keep:.0%}")

        # DWT уровни
        if method == "dwt" and levels != 4:
            level_impact = (levels - 4) * -0.1
            impact += level_impact
            if abs(level_impact) > 0.1:
                factors.append(f"уровни:{levels}")

        # Хаффман μ и биты
        if method == "huff":
            if mu != 255:
                mu_impact = abs(mu - 255) / 255 * 0.3
                impact += mu_impact
                factors.append(f"μ:{mu:.0f}")
            if bits != 8:
                bits_impact = (8 - bits) * 0.2
                impact += bits_impact
                factors.append(f"биты:{bits}")

        # Розенброк
        if method == "rb":
            if alpha != 0.2:
                alpha_impact = abs(alpha - 0.2) * 0.5
                impact += alpha_impact
                factors.append(f"α:{alpha:.1f}")
            if beta != 1.0:
                beta_impact = abs(beta - 1.0) * 0.3
                impact += beta_impact
                factors.append(f"β:{beta:.1f}")

        return impact, factors

    def _calc_snr_impact(
        self, method, bitrate_kbps, base_bitrate_kbps,
        block_size, base_block, select_mode, keep_energy,
        seq_keep, mu, bits
    ) -> Tuple[float, List[str]]:
        """Расчёт влияния на SNR."""
        impact = 0.0
        factors = []

        # Битрейт: выше битрейт → выше SNR
        bitrate_impact = (bitrate_kbps - base_bitrate_kbps) / base_bitrate_kbps * 1.5
        impact += bitrate_impact
        if abs(bitrate_impact) > 0.1:
            factors.append(f"битрейт:{bitrate_kbps}k")

        # Размер блока
        if method in ("fwht", "fft", "dct", "dwt"):
            block_impact = (block_size - base_block) / base_block * 0.3
            impact += block_impact
            if abs(block_impact) > 0.1:
                factors.append(f"блок:{block_size}")

            # Режим отбора
            if select_mode == "energy" and keep_energy < 1.0:
                energy_impact = (keep_energy - 1.0) * 2.0
                impact += energy_impact
                factors.append(f"энергия:{keep_energy:.0%}")
            elif select_mode == "lowpass" and seq_keep < 1.0:
                lowpass_impact = (seq_keep - 1.0) * 2.5
                impact += lowpass_impact
                factors.append(f"частоты:{seq_keep:.0%}")

        # Хаффман
        if method == "huff":
            if bits != 8:
                bits_impact = (bits - 8) * 0.3
                impact += bits_impact
                factors.append(f"биты:{bits}")
            if mu != 255:
                mu_impact = -abs(mu - 255) / 255 * 0.2
                impact += mu_impact
                factors.append(f"μ:{mu:.0f}")

        return impact, factors

    def _calc_rmse_impact(
        self, method, bitrate_kbps, base_bitrate_kbps,
        block_size, base_block, select_mode, keep_energy,
        seq_keep, bits
    ) -> Tuple[float, List[str]]:
        """Расчёт влияния на RMSE."""
        impact = 0.0
        factors = []

        bitrate_impact = (bitrate_kbps - base_bitrate_kbps) / base_bitrate_kbps * -1.2
        impact += bitrate_impact

        if method in ("fwht", "fft", "dct", "dwt"):
            block_impact = (block_size - base_block) / base_block * -0.3
            impact += block_impact

            if select_mode == "energy" and keep_energy < 1.0:
                impact += (1.0 - keep_energy) * 1.8
                factors.append(f"энергия:{keep_energy:.0%}")
            elif select_mode == "lowpass" and seq_keep < 1.0:
                impact += (1.0 - seq_keep) * 2.0
                factors.append(f"частоты:{seq_keep:.0%}")

        if method == "huff" and bits != 8:
            impact += (8 - bits) * 0.15
            factors.append(f"биты:{bits}")

        return impact, factors

    def _calc_sisdr_impact(
        self, method, bitrate_kbps, base_bitrate_kbps,
        select_mode, keep_energy, seq_keep
    ) -> Tuple[float, List[str]]:
        """Расчёт влияния на SI-SDR."""
        impact = 0.0
        factors = []

        bitrate_impact = (bitrate_kbps - base_bitrate_kbps) / base_bitrate_kbps * 1.3
        impact += bitrate_impact

        if method in ("fwht", "fft", "dct", "dwt"):
            if select_mode == "energy" and keep_energy < 1.0:
                impact += (keep_energy - 1.0) * 1.5
                factors.append(f"энергия:{keep_energy:.0%}")
            elif select_mode == "lowpass" and seq_keep < 1.0:
                impact += (seq_keep - 1.0) * 1.8
                factors.append(f"частоты:{seq_keep:.0%}")

        return impact, factors

    def _calc_spec_conv_impact(
        self, method, select_mode, keep_energy, seq_keep
    ) -> Tuple[float, List[str]]:
        """Расчёт влияния на Spectral Convergence."""
        impact = 0.0
        factors = []

        if method in ("fwht", "fft", "dct", "dwt"):
            if select_mode == "energy" and keep_energy < 1.0:
                impact += (1.0 - keep_energy) * 1.5
                factors.append(f"энергия:{keep_energy:.0%}")
            elif select_mode == "lowpass" and seq_keep < 1.0:
                impact += (1.0 - seq_keep) * 2.0
                factors.append(f"частоты:{seq_keep:.0%}")

        return impact, factors

    def _calc_centroid_impact(
        self, method, select_mode, seq_keep
    ) -> Tuple[float, List[str]]:
        """Расчёт влияния на Spectral Centroid Δ."""
        impact = 0.0
        factors = []

        if method in ("fwht", "fft", "dct", "dwt"):
            if select_mode == "lowpass" and seq_keep < 1.0:
                impact += (seq_keep - 1.0) * -0.5
                factors.append(f"lowpass:{seq_keep:.0%}")

        return impact, factors

    def _calc_cosine_impact(
        self, method, bitrate_kbps, base_bitrate_kbps,
        select_mode, keep_energy
    ) -> Tuple[float, List[str]]:
        """Расчёт влияния на Cosine Similarity."""
        impact = 0.0
        factors = []

        bitrate_impact = (bitrate_kbps - base_bitrate_kbps) / base_bitrate_kbps * 0.5
        impact += bitrate_impact

        if method in ("fwht", "fft", "dct", "dwt"):
            if select_mode == "energy" and keep_energy < 1.0:
                impact += (keep_energy - 1.0) * 1.0
                factors.append(f"энергия:{keep_energy:.0%}")

        return impact, factors

    def _calc_time_impact(
        self, method, block_size, base_block, levels
    ) -> Tuple[float, List[str]]:
        """Расчёт влияния на время обработки."""
        impact = 0.0
        factors = []

        if method in ("fwht", "fft", "dct", "dwt"):
            block_impact = (block_size - base_block) / base_block * 0.8
            impact += block_impact
            if block_impact > 0.1:
                factors.append(f"блок:{block_size}")

            if method == "dwt" and levels != 4:
                level_impact = (levels - 4) * 0.15
                impact += level_impact
                factors.append(f"уровни:{levels}")

        return impact, factors

    def _calc_size_impact(
        self, bitrate_kbps, base_bitrate_kbps
    ) -> Tuple[float, List[str]]:
        """Расчёт влияния на размер файла."""
        impact = 0.0
        factors = []

        bitrate_impact = (bitrate_kbps - base_bitrate_kbps) / base_bitrate_kbps * 2.0
        impact += bitrate_impact
        if abs(bitrate_impact) > 0.05:
            factors.append(f"битрейт:{bitrate_kbps}k")

        return impact, factors

    def _format_impact_result(
        self, impact: float, factors: List[str], metric: str
    ) -> Tuple[str, str, QColor]:
        """Форматирование результата влияния.

        Возвращает:
        -----------
        Tuple[str, str, QColor]
            (символ, tooltip, цвет)
        """
        # Определяем пороги для классификации
        if impact > 0.5:
            symbol = "↑↑"
            color = QColor(0, 150, 0)  # Зелёный
            desc = "Существенное улучшение"
        elif impact > 0.15:
            symbol = "↑"
            color = QColor(50, 180, 50)  # Светло-зелёный
            desc = "Улучшение"
        elif impact > -0.15:
            symbol = "→"
            color = QColor(100, 100, 100)  # Серый
            desc = "Без изменений"
        elif impact > -0.5:
            symbol = "↓"
            color = QColor(200, 100, 0)  # Оранжевый
            desc = "Ухудшение"
        else:
            symbol = "↓↓"
            color = QColor(200, 0, 0)  # Красный
            desc = "Существенное ухудшение"

        # Для метрик где "выше лучше" - инвертируем отображение
        higher_better = metric in ("snr", "sisdr", "cosine")
        if higher_better:
            symbol, color = self._invert_impact_symbol(symbol, color)

        # Формируем tooltip
        tooltip = f"{desc}\nВлияние: {impact:+.2f}"
        if factors:
            tooltip += f"\nФакторы: {', '.join(factors)}"

        return symbol, tooltip, color

    def _invert_impact_symbol(
        self, symbol: str, color: QColor
    ) -> Tuple[str, QColor]:
        """Инвертировать символ для метрик 'выше лучше'."""
        if symbol == "↑↑":
            return "↓↓", QColor(0, 150, 0)
        elif symbol == "↑":
            return "↓", QColor(50, 180, 50)
        elif symbol == "↓↓":
            return "↑↑", QColor(200, 0, 0)
        elif symbol == "↓":
            return "↑", QColor(200, 100, 0)
        return symbol, color

    # =========================================================================
    # ОБНОВЛЕНИЕ ТАБЛИЦЫ
    # =========================================================================

    def _update_settings_matrix_table(self) -> None:
        """Обновить таблицу влияния параметров на метрики.

        Показывает качественное влияние текущих параметров на метрики
        для каждого метода.
        """
        settings = self._current_settings()

        # Проверяем, есть ли отличия от стандартных настроек
        is_default = (
            settings.get("block_size", 2048) == 2048 and
            str(settings.get("bitrate", "192k")) == "192k" and
            settings.get("select_mode", "none") == "none" and
            float(settings.get("keep_energy_ratio", 1.0)) == 1.0 and
            float(settings.get("sequency_keep_ratio", 1.0)) == 1.0 and
            int(settings.get("levels", 4)) == 4 and
            float(settings.get("mu", 255)) == 255 and
            int(settings.get("bits", 8)) == 8 and
            float(settings.get("rosen_alpha", 0.2)) == 0.2 and
            float(settings.get("rosen_beta", 1.0)) == 1.0
        )

        # Заполняем таблицу
        for ri, (method_key, _) in enumerate(METHOD_HEADERS, start=1):
            for ci, (metric_key, _, _) in enumerate(METRICS_COLS, start=1):
                if is_default:
                    symbol = "→"
                    color = QColor(100, 100, 100)
                    tooltip = "Стандартные параметры\nВлияние нейтральное"
                else:
                    symbol, tooltip, color = self._calculate_impact_score(
                        method_key, metric_key, settings
                    )

                it = QTableWidgetItem(symbol)
                it.setTextAlignment(Qt.AlignCenter)
                it.setForeground(color)
                it.setToolTip(tooltip)
                self.table_settings_matrix.setItem(ri, ci, it)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "SettingsMixin",
    "METHOD_HEADERS",
    "METRICS_COLS",
    "PARAMS_ROWS",
]
