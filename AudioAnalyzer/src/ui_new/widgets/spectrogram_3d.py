"""
3D Spectrogram Widget - трёхмерная визуализация спектра.

Функционал:
- 3D визуализация спектрограммы с возможностью вращения
- Интерактивное управление (зум, поворот, пан)
- Экспорт в PNG/SVG
- Цветовая карта с настраиваемыми параметрами

Использование:
--------------
>>> from ui_new.widgets.spectrogram_3d import Spectrogram3DWidget
>>> 
>>> widget = Spectrogram3DWidget()
>>> widget.set_data(frequencies, times, spectrogram_data)
"""
from __future__ import annotations

import logging
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ui_new.widgets.spectrogram_3d")

# Check for matplotlib 3D support
try:
    import matplotlib
    matplotlib.use('QtAgg')
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from mpl_toolkits.mplot3d import Axes3D
    from matplotlib import cm
    from matplotlib.colors import Normalize
    HAS_MATPLOTLIB_3D = True
except ImportError:
    HAS_MATPLOTLIB_3D = False
    FigureCanvas = object
    Figure = object
    logger.debug("matplotlib 3D not available. 3D spectrogram disabled.")


class Spectrogram3DWidget(FigureCanvas):
    """3D Spectrogram Widget с использованием matplotlib.
    
    Features:
    - Интерактивное вращение (drag)
    - Зум (scroll wheel)
    - Настройка цветовой карты
    - Экспорт в PNG/SVG
    """
    
    def __init__(self, parent=None):
        """Инициализация виджета."""
        if not HAS_MATPLOTLIB_3D:
            raise ImportError(
                "matplotlib 3D не доступен. Установите: pip install matplotlib"
            )
        
        # Создаём Figure
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.fig.patch.set_facecolor('#1F2937')
        
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Создаём 3D оси
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#111827')
        
        # Данные
        self._freqs: Optional[np.ndarray] = None
        self._times: Optional[np.ndarray] = None
        self._spectrogram: Optional[np.ndarray] = None
        self._surface = None
        
        # Настройки
        self._colormap = 'viridis'
        self._view_elev = 30
        self._view_azim = 45
        
        # Настраиваем стиль
        self._setup_style()
    
    def _setup_style(self) -> None:
        """Настроить стиль графика."""
        # Стиль осей
        self.ax.tick_params(colors='#9CA3AF', labelsize=8)
        self.ax.xaxis.label.set_color('#E5E7EB')
        self.ax.yaxis.label.set_color('#E5E7EB')
        self.ax.zaxis.label.set_color('#E5E7EB')
        
        # Стиль панелей
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        
        self.ax.xaxis.pane.set_edgecolor('#374151')
        self.ax.yaxis.pane.set_edgecolor('#374151')
        self.ax.zaxis.pane.set_edgecolor('#374151')
        
        # Grid
        self.ax.grid(True, alpha=0.3, color='#4B5563')
        
        # Устанавливаем начальный угол обзора
        self.ax.view_init(elev=self._view_elev, azim=self._view_azim)
    
    def set_data(
        self,
        freqs: np.ndarray,
        times: np.ndarray,
        spectrogram: np.ndarray,
    ) -> None:
        """Установить данные спектрограммы.
        
        Parameters
        ----------
        freqs : np.ndarray
            Массив частот (shape: [n_freqs])
        times : np.ndarray
            Массив времён (shape: [n_times])
        spectrogram : np.ndarray
            Спектрограмма (shape: [n_freqs, n_times])
        """
        self._freqs = freqs
        self._times = times
        self._spectrogram = spectrogram
        
        self._update_plot()
    
    def set_data_from_audio(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_fft: int = 2048,
        hop_length: int = 512,
    ) -> None:
        """Вычислить и отобразить спектрограмму из аудиосигнала.
        
        Parameters
        ----------
        signal : np.ndarray
            Аудиосигнал
        sample_rate : int
            Частота дискретизации
        n_fft : int
            Размер FFT окна
        hop_length : int
            Шаг окна
        """
        # Вычисляем STFT
        n_frames = 1 + (len(signal) - n_fft) // hop_length
        spectrogram = np.zeros((n_fft // 2 + 1, n_frames))
        
        window = np.hanning(n_fft)
        
        for i in range(n_frames):
            start = i * hop_length
            frame = signal[start:start + n_fft]
            if len(frame) < n_fft:
                frame = np.pad(frame, (0, n_fft - len(frame)))
            
            fft_result = np.fft.rfft(frame * window)
            spectrogram[:, i] = np.abs(fft_result)
        
        # Частоты и времена
        freqs = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
        times = np.arange(n_frames) * hop_length / sample_rate
        
        # Конвертируем в dB
        spectrogram_db = 20 * np.log10(spectrogram + 1e-10)
        
        self.set_data(freqs, times, spectrogram_db)
    
    def _update_plot(self) -> None:
        """Обновить график."""
        if self._freqs is None or self._times is None or self._spectrogram is None:
            return
        
        # Очищаем оси
        self.ax.clear()
        self._setup_style()
        
        # Создаём сетку
        F, T = np.meshgrid(self._freqs, self._times)
        S = self._spectrogram.T  # Транспонируем для правильной формы
        
        # Ограничиваем частоты для лучшей визуализации
        max_freq_idx = min(len(self._freqs), 100)  # Максимум 100 частотных бинов
        freq_mask = np.arange(0, max_freq_idx)
        
        F_subset = F[:, freq_mask]
        S_subset = S[:, freq_mask]
        
        # Нормализация
        norm = Normalize(vmin=S_subset.min(), vmax=S_subset.max())
        
        # Создаём 3D поверхность
        self._surface = self.ax.plot_surface(
            F_subset,
            T,
            S_subset,
            cmap=self._colormap,
            norm=norm,
            edgecolor='none',
            alpha=0.9,
            antialiased=True,
        )
        
        # Метки осей
        self.ax.set_xlabel('Частота (Гц)', fontsize=10, labelpad=10)
        self.ax.set_ylabel('Время (с)', fontsize=10, labelpad=10)
        self.ax.set_zlabel('Амплитуда (дБ)', fontsize=10, labelpad=10)
        
        # Заголовок
        self.ax.set_title('3D Спектрограмма', color='#E5E7EB', fontsize=12, pad=20)
        
        # Восстанавливаем угол обзора
        self.ax.view_init(elev=self._view_elev, azim=self._view_azim)
        
        # Colorbar
        if hasattr(self, '_colorbar'):
            try:
                self._colorbar.remove()
            except Exception:
                pass
        
        self._colorbar = self.fig.colorbar(
            self._surface,
            ax=self.ax,
            shrink=0.5,
            aspect=10,
            pad=0.1
        )
        self._colorbar.ax.yaxis.set_tick_params(color='#9CA3AF')
        self._colorbar.ax.yaxis.label.set_color('#E5E7EB')
        
        # Обновляем
        self.draw()
    
    def set_colormap(self, name: str) -> None:
        """Установить цветовую карту.
        
        Parameters
        ----------
        name : str
            Имя цветовой карты matplotlib (viridis, plasma, magma, inferno, etc.)
        """
        self._colormap = name
        if self._spectrogram is not None:
            self._update_plot()
    
    def set_view_angle(self, elev: float, azim: float) -> None:
        """Установить угол обзора.
        
        Parameters
        ----------
        elev : float
            Угол возвышения (0-90 градусов)
        azim : float
            Азимутальный угол (0-360 градусов)
        """
        self._view_elev = elev
        self._view_azim = azim
        self.ax.view_init(elev=elev, azim=azim)
        self.draw()
    
    def reset_view(self) -> None:
        """Сбросить вид к начальному."""
        self.set_view_angle(30, 45)
    
    def save_figure(self, path: str, dpi: int = 150) -> bool:
        """Сохранить фигуру в файл.
        
        Parameters
        ----------
        path : str
            Путь к файлу (.png, .svg, .pdf)
        dpi : int
            Разрешение для растровых форматов
            
        Returns
        -------
        bool
            True при успехе
        """
        try:
            # Ensure directory exists
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            self.fig.savefig(
                path,
                dpi=dpi,
                facecolor=self.fig.get_facecolor(),
                edgecolor='none',
                bbox_inches='tight'
            )
            
            logger.info("3D spectrogram saved to %s", path)
            return True
            
        except Exception as e:
            logger.error("Failed to save 3D spectrogram: %s", e)
            return False
    
    def get_available_colormaps(self) -> List[str]:
        """Получить список доступных цветовых карт."""
        return [
            'viridis', 'plasma', 'inferno', 'magma', 'cividis',
            'coolwarm', 'RdBu', 'jet', 'turbo', 'rainbow',
            'Greys', 'Blues', 'Greens', 'Oranges', 'Reds',
        ]


class Spectrogram3DWidgetFallback(QWidget if 'QWidget' in dir() else object):
    """Fallback виджет когда matplotlib 3D недоступен."""
    
    def __init__(self, parent=None):
        """Инициализация fallback виджета."""
        # Импортируем QWidget если доступен
        try:
            from PySide6.QtWidgets import QWidget as QWidgetClass, QLabel, QVBoxLayout
            from PySide6.QtCore import Qt
            
            QWidgetClass.__init__(self, parent)
            
            layout = QVBoxLayout(self)
            
            label = QLabel(
                "3D Спектрограмма недоступна.\n\n"
                "Для использования установите matplotlib:\n"
                "pip install matplotlib"
            )
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #9CA3AF; font-size: 14px;")
            
            layout.addWidget(label)
            
            self.setMinimumSize(400, 300)
            
        except ImportError:
            # QWidget недоступен
            pass


def create_3d_spectrogram_widget(parent=None):
    """Фабричная функция для создания 3D спектрограммы.
    
    Автоматически выбирает между реальным виджетом и fallback.
    """
    if HAS_MATPLOTLIB_3D:
        try:
            return Spectrogram3DWidget(parent)
        except Exception as e:
            logger.warning("Failed to create Spectrogram3DWidget: %s", e)
            return Spectrogram3DWidgetFallback(parent)
    else:
        return Spectrogram3DWidgetFallback(parent)


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    "Spectrogram3DWidget",
    "Spectrogram3DWidgetFallback",
    "create_3d_spectrogram_widget",
    "HAS_MATPLOTLIB_3D",
]
