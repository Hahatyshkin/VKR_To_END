"""
Интерактивный виджет спектра с использованием pyqtgraph.

Возможности:
- Масштабирование (zoom) мышью
- Прокрутка (pan) мышью
- Легенда с чекбоксами для включения/отключения кривых
- Отображение координат курсора
- Кнопки сброса масштаба
- Экспорт графика
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from ui_new.design_system import DesignSystem
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger("ui_new.widgets.spectrum")


class InteractiveSpectrumWidget(QWidget):
    """Интерактивный виджет для отображения спектров.

    Features:
    - Zoom: левая кнопка мыши + перетаскивание по оси Y
    - Pan: средняя кнопка мыши или Ctrl + левая кнопка
    - Crosshair: отображение координат курсора
    - Legend: чекбоксы для управления видимостью кривых
    - Reset: кнопка сброса масштаба
    """

    # Сигнал при изменении видимости кривой
    curve_visibility_changed = Signal(str, bool)

    # Цвета для кривых — 10 различных, без белого и чёрного
    DEFAULT_COLORS = [
        (0, 114, 178),    # Синий (стальной)
        (230, 57, 70),    # Красный
        (39, 164, 75),    # Зелёный
        (240, 165, 0),    # Оранжевый
        (148, 55, 183),   # Фиолетовый
        (0, 168, 168),    # Бирюзовый
        (220, 90, 150),   # Розовый
        (130, 130, 30),   # Оливковый
        (0, 180, 130),    # Мятный
        (180, 100, 50),   # Коричневый
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        """Инициализация виджета."""
        super().__init__(parent)

        self._curves: Dict[str, pg.PlotDataItem] = {}
        self._curve_data: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        self._curve_visibility: Dict[str, bool] = {}
        self._checkboxes: Dict[str, QCheckBox] = {}

        self._build_ui()
        self._setup_plot()

    def _build_ui(self) -> None:
        """Построить интерфейс виджета."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Верхняя панель с контролами
        controls_layout = QHBoxLayout()

        # Метка координат курсора
        self.coords_label = QLabel("Частота: — Гц, Амплитуда: — дБ")
        self.coords_label.setStyleSheet(f"color: {DesignSystem.colors.text_muted}; font-size: 11px;")
        controls_layout.addWidget(self.coords_label, 1)

        # Кнопки управления
        self.btn_reset_zoom = QPushButton("⟲ Сброс")
        self.btn_reset_zoom.setToolTip("Сбросить масштаб и позицию")
        self.btn_reset_zoom.clicked.connect(self.reset_zoom)
        controls_layout.addWidget(self.btn_reset_zoom)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setToolTip("Увеличить")
        self.btn_zoom_in.setFixedWidth(30)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        controls_layout.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setToolTip("Уменьшить")
        self.btn_zoom_out.setFixedWidth(30)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        controls_layout.addWidget(self.btn_zoom_out)

        layout.addLayout(controls_layout)

        # Основная область: график + легенда
        main_layout = QHBoxLayout()

        # График
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Амплитуда', units='дБ')
        self.plot_widget.setLabel('bottom', 'Частота', units='Гц')
        self.plot_widget.setTitle('Спектральное сравнение')
        main_layout.addWidget(self.plot_widget, 1)

        # Панель легенды с чекбоксами
        legend_widget = QWidget()
        legend_layout = QVBoxLayout()
        legend_layout.setContentsMargins(5, 5, 5, 5)
        legend_widget.setLayout(legend_layout)

        legend_header = QLabel("Кривые:")
        legend_header.setStyleSheet("font-weight: bold;")
        legend_layout.addWidget(legend_header)

        # Scroll area для легенды
        self.legend_scroll = QScrollArea()
        self.legend_scroll.setWidgetResizable(True)
        self.legend_scroll.setFixedWidth(150)
        self.legend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.legend_container = QWidget()
        self.legend_container_layout = QVBoxLayout()
        self.legend_container_layout.setContentsMargins(0, 0, 0, 0)
        self.legend_container.setLayout(self.legend_container_layout)
        self.legend_scroll.setWidget(self.legend_container)

        legend_layout.addWidget(self.legend_scroll)

        # Кнопки "Все" и "Никто"
        legend_buttons = QHBoxLayout()
        btn_all = QPushButton("Все")
        btn_all.clicked.connect(self.show_all_curves)
        legend_buttons.addWidget(btn_all)

        btn_none = QPushButton("Никто")
        btn_none.clicked.connect(self.hide_all_curves)
        legend_buttons.addWidget(btn_none)
        legend_layout.addLayout(legend_buttons)

        legend_widget.setFixedWidth(160)
        main_layout.addWidget(legend_widget)

        layout.addLayout(main_layout, 1)

    def _setup_plot(self) -> None:
        """Настроить график и обработчики событий."""
        # Crosshair (перекрестие)
        self.vline = pg.InfiniteLine(angle=90, movable=False)
        self.hline = pg.InfiniteLine(angle=0, movable=False)
        crosshair_color = DesignSystem.colors.text_disabled
        self.vline.setPen(pg.mkPen(color=crosshair_color, style=Qt.DashLine))
        self.hline.setPen(pg.mkPen(color=crosshair_color, style=Qt.DashLine))
        self.plot_widget.addItem(self.vline, ignoreBounds=True)
        self.plot_widget.addItem(self.hline, ignoreBounds=True)

        # Proxy для обработки событий мыши (с rate limiting для производительности)
        self.proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved
        )

    def _on_mouse_moved(self, evt) -> None:
        """Обработчик движения мыши - обновление перекрестия и координат."""
        from PySide6.QtCore import QPointF
        
        # SignalProxy может передавать кортеж или QPointF
        if isinstance(evt, tuple):
            pos = evt[0] if len(evt) > 0 else None
        else:
            pos = evt
            
        if pos is None:
            self.coords_label.setText("Частота: — Гц, Амплитуда: — дБ")
            return
            
        # Преобразуем в QPointF если нужно
        if not isinstance(pos, QPointF):
            try:
                pos = QPointF(pos[0], pos[1]) if isinstance(pos, (tuple, list)) else QPointF(pos.x(), pos.y())
            except Exception:
                self.coords_label.setText("Частота: — Гц, Амплитуда: — дБ")
                return
        
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()

            # Обновляем перекрестие
            self.vline.setPos(x)
            self.hline.setPos(y)

            # Обновляем метку координат
            self.coords_label.setText(
                f"Частота: {x:.1f} Гц, Амплитуда: {y:.1f} дБ"
            )
        else:
            self.coords_label.setText("Частота: — Гц, Амплитуда: — дБ")

    def add_curve(
        self,
        name: str,
        frequencies: np.ndarray,
        amplitudes_db: np.ndarray,
        color: Optional[Tuple[int, int, int]] = None,
        visible: bool = True
    ) -> None:
        """Добавить кривую спектра.

        Параметры:
        ----------
        name : str
            Имя кривой (для легенды)
        frequencies : np.ndarray
            Массив частот (Гц)
        amplitudes_db : np.ndarray
            Массив амплитуд (дБ)
        color : Tuple[int, int, int], optional
            Цвет в RGB (по умолчанию - из DEFAULT_COLORS)
        visible : bool
            Начальная видимость кривой
        """
        if name in self._curves:
            # Удаляем существующую кривую
            self.remove_curve(name)

        # Выбираем цвет
        if color is None:
            color_idx = len(self._curves) % len(self.DEFAULT_COLORS)
            color = self.DEFAULT_COLORS[color_idx]

        # Создаём кривую
        pen = pg.mkPen(color=color, width=2)
        curve = self.plot_widget.plot(
            frequencies,
            amplitudes_db,
            pen=pen,
            name=name,
            clickable=True
        )

        self._curves[name] = curve
        self._curve_data[name] = (frequencies, amplitudes_db)
        self._curve_visibility[name] = visible

        # Создаём чекбокс в легенде
        self._create_legend_checkbox(name, color, visible)

        # Устанавливаем видимость
        curve.setVisible(visible)

    def _create_legend_checkbox(
        self,
        name: str,
        color: Tuple[int, int, int],
        visible: bool
    ) -> None:
        """Создать чекбокс для кривой в легенде."""
        checkbox = QCheckBox(name)
        checkbox.setChecked(visible)

        # Цветной индикатор
        r, g, b = color
        checkbox.setStyleSheet(
            f"QCheckBox {{ color: rgb({r}, {g}, {b}); font-weight: bold; }}"
        )

        checkbox.toggled.connect(lambda checked: self._on_checkbox_toggled(name, checked))

        self._checkboxes[name] = checkbox
        self.legend_container_layout.addWidget(checkbox)

    def _on_checkbox_toggled(self, name: str, checked: bool) -> None:
        """Обработчик изменения видимости кривой."""
        if name in self._curves:
            self._curves[name].setVisible(checked)
            self._curve_visibility[name] = checked
            self.curve_visibility_changed.emit(name, checked)

    def remove_curve(self, name: str) -> None:
        """Удалить кривую."""
        if name in self._curves:
            self.plot_widget.removeItem(self._curves[name])
            del self._curves[name]
            del self._curve_data[name]
            del self._curve_visibility[name]

        if name in self._checkboxes:
            self.legend_container_layout.removeWidget(self._checkboxes[name])
            self._checkboxes[name].deleteLater()
            del self._checkboxes[name]

    def clear_all_curves(self) -> None:
        """Удалить все кривые."""
        for name in list(self._curves.keys()):
            self.remove_curve(name)

    def show_all_curves(self) -> None:
        """Показать все кривые."""
        for name, checkbox in self._checkboxes.items():
            checkbox.setChecked(True)

    def hide_all_curves(self) -> None:
        """Скрыть все кривые."""
        for name, checkbox in self._checkboxes.items():
            checkbox.setChecked(False)

    def reset_zoom(self) -> None:
        """Сбросить масштаб и позицию."""
        self.plot_widget.autoRange()

        # Если есть данные, устанавливаем разумные границы
        if self._curve_data:
            all_freqs = []
            all_amps = []
            for freqs, amps in self._curve_data.values():
                all_freqs.extend(freqs)
                all_amps.extend(amps)

            if all_freqs and all_amps:
                freq_min, freq_max = min(all_freqs), max(all_freqs)
                amp_min, amp_max = min(all_amps), max(all_amps)

                # Добавляем отступы
                freq_margin = (freq_max - freq_min) * 0.05
                amp_margin = (amp_max - amp_min) * 0.1

                self.plot_widget.setXRange(
                    max(20, freq_min - freq_margin),
                    freq_max + freq_margin
                )
                self.plot_widget.setYRange(
                    amp_min - amp_margin,
                    amp_max + amp_margin
                )

    def zoom_in(self) -> None:
        """Увеличить масштаб (zoom in)."""
        view = self.plot_widget.plotItem.vb
        view.scaleBy((0.8, 0.8))

    def zoom_out(self) -> None:
        """Уменьшить масштаб (zoom out)."""
        view = self.plot_widget.plotItem.vb
        view.scaleBy((1.25, 1.25))

    def set_title(self, title: str) -> None:
        """Установить заголовок графика."""
        self.plot_widget.setTitle(title)

    def get_visible_curves(self) -> List[str]:
        """Получить список видимых кривых."""
        return [name for name, visible in self._curve_visibility.items() if visible]

    def get_curve_names(self) -> List[str]:
        """Получить список всех кривых."""
        return list(self._curves.keys())

    def set_log_mode(self, x_log: bool = False, y_log: bool = False) -> None:
        """Установить логарифмический масштаб."""
        self.plot_widget.setLogMode(x=x_log, y=y_log)

    def set_x_range(self, min_freq: float, max_freq: float) -> None:
        """Установить диапазон частот."""
        self.plot_widget.setXRange(min_freq, max_freq)

    def set_y_range(self, min_db: float, max_db: float) -> None:
        """Установить диапазон амплитуд."""
        self.plot_widget.setYRange(min_db, max_db)


class SpectrumCalculator:
    """Калькулятор спектров для аудиосигналов."""

    @staticmethod
    def compute_spectrum(
        signal: np.ndarray,
        sample_rate: int,
        n_fft: int = 4096,
        hop_length: int = 2048,
        window: str = 'hann'
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Вычислить усреднённый спектр сигнала.

        Параметры:
        ----------
        signal : np.ndarray
            Аудиосигнал (моно)
        sample_rate : int
            Частота дискретизации
        n_fft : int
            Размер окна FFT
        hop_length : int
            Шаг окна
        window : str
            Тип окна ('hann', 'hamming', 'blackman')

        Возвращает:
        -----------
        Tuple[np.ndarray, np.ndarray]
            (frequencies, spectrum_db) - частоты и спектр в дБ
        """
        # Нормализация сигнала
        if signal.dtype != np.float32:
            signal = signal.astype(np.float32)

        # Создаём окно
        if window == 'hann':
            win = np.hanning(n_fft)
        elif window == 'hamming':
            win = np.hamming(n_fft)
        elif window == 'blackman':
            win = np.blackman(n_fft)
        else:
            win = np.hanning(n_fft)

        # Дополнение сигнала
        pad_length = n_fft // 2
        signal_padded = np.pad(signal, (pad_length, pad_length), mode='reflect')

        # Количество фреймов
        n_frames = 1 + (len(signal_padded) - n_fft) // hop_length

        # Вычисляем спектры для каждого фрейма
        spectra = []
        for i in range(n_frames):
            start = i * hop_length
            frame = signal_padded[start:start + n_fft] * win

            # FFT
            spectrum = np.abs(np.fft.rfft(frame))
            spectra.append(spectrum)

        # Усредняем спектры
        avg_spectrum = np.mean(spectra, axis=0)

        # Частоты
        frequencies = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)

        # Преобразуем в дБ
        spectrum_db = 20 * np.log10(avg_spectrum + 1e-10)

        return frequencies, spectrum_db

    @staticmethod
    def compute_spectrum_simple(
        signal: np.ndarray,
        sample_rate: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Простой расчёт спектра (для совместимости).

        Параметры:
        ----------
        signal : np.ndarray
            Аудиосигнал
        sample_rate : int
            Частота дискретизации

        Возвращает:
        -----------
        Tuple[np.ndarray, np.ndarray]
            (frequencies, spectrum_db)
        """
        n = len(signal)

        # FFT
        fft_result = np.fft.rfft(signal)
        spectrum = np.abs(fft_result)
        spectrum = spectrum / n * 2

        # Частоты
        frequencies = np.fft.rfftfreq(n, 1.0 / sample_rate)

        # В дБ
        spectrum_db = 20 * np.log10(spectrum + 1e-10)

        return frequencies, spectrum_db


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "InteractiveSpectrumWidget",
    "SpectrumCalculator",
]
