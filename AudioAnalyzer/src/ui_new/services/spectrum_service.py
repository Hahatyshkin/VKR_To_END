"""
Сервис спектрального анализа.

Назначение:
- Вычисление спектра аудиосигнала
- Сравнение спектров разных методов
- Подготовка данных для визуализации

Использование:
--------------
>>> from ui_new.services import get_container
>>> container = get_container()
>>> spectrum_service = container.spectrum
>>> 
>>> # Вычислить спектр
>>> freqs, spectrum_db = spectrum_service.compute_spectrum(signal, sample_rate)
>>> 
>>> # Сравнить спектры
>>> comparison = spectrum_service.compare_spectra(source_path, processed_paths)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from .config import AppConfig

logger = logging.getLogger("ui_new.services.spectrum_service")


# =============================================================================
# СТРУКТУРЫ ДАННЫХ
# =============================================================================

@dataclass
class SpectrumData:
    """Данные спектра для визуализации."""
    name: str
    freqs: np.ndarray
    spectrum_db: np.ndarray
    color: Tuple[int, int, int] = (0, 0, 0)
    
    @property
    def point_count(self) -> int:
        """Количество точек в спектре."""
        return len(self.freqs)


@dataclass
class SpectrumComparison:
    """Результат сравнения спектров."""
    source: SpectrumData
    processed: List[SpectrumData]
    max_freq: float = 20000.0
    min_db: float = -100.0
    max_db: float = 0.0


# =============================================================================
# СЕРВИС СПЕКТРАЛЬНОГО АНАЛИЗА
# =============================================================================

class SpectrumService:
    """Сервис спектрального анализа.
    
    Предоставляет:
    - Вычисление спектра сигнала (FFT)
    - Downsampling для визуализации
    - Сравнение спектров разных файлов
    - Метрики схожести спектров
    
    Атрибуты:
    ----------
    config : AppConfig
        Конфигурация приложения
    """
    
    # Цвета для кривых спектра
    DEFAULT_COLORS: List[Tuple[int, int, int]] = [
        (0, 0, 0),        # Исходный - черный
        (255, 0, 0),      # Красный
        (0, 128, 0),      # Зелёный
        (0, 0, 255),      # Синий
        (255, 165, 0),    # Оранжевый
        (128, 0, 128),    # Фиолетовый
        (0, 128, 128),    # Бирюзовый
        (255, 192, 203),  # Розовый
    ]
    
    def __init__(self, config: AppConfig):
        """Инициализация сервиса.
        
        Параметры:
        ----------
        config : AppConfig
            Конфигурация приложения
        """
        self._config = config
        self._max_points = config.max_spectrum_points
        logger.debug(f"SpectrumService initialized (max_points={self._max_points})")
    
    # =========================================================================
    # ВЫЧИСЛЕНИЕ СПЕКТРА
    # =========================================================================
    
    def compute_spectrum(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_fft: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Вычислить спектр сигнала.
        
        Использует FFT для вычисления спектра мощности.
        Результат возвращается в децибелах.
        
        Параметры:
        ----------
        signal : np.ndarray
            Аудиосигнал (моно)
        sample_rate : int
            Частота дискретизации
        n_fft : Optional[int]
            Размер FFT. Если None, используется длина сигнала.
            
        Возвращает:
        -----------
        Tuple[np.ndarray, np.ndarray]
            (частоты, спектр в дБ)
        """
        # Валидация
        if signal is None or len(signal) == 0:
            return np.array([]), np.array([])
        
        # Нормализация
        signal = np.asarray(signal, dtype=np.float32)
        
        # Удаление NaN и Inf
        signal = np.nan_to_num(signal, nan=0.0, posinf=0.0, neginf=0.0)
        
        # FFT
        if n_fft is None:
            n_fft = len(signal)
        
        # Используем длину, являющуюся степенью двойки для эффективности
        n_fft = max(1, int(2 ** np.ceil(np.log2(min(n_fft, len(signal))))))
        
        # FFT с zero-padding если нужно
        fft_result = np.fft.rfft(signal, n=n_fft)
        spectrum = np.abs(fft_result)
        
        # Нормализация
        spectrum = spectrum / n_fft * 2
        
        # Частоты
        freqs = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
        
        # Конвертация в дБ (с защитой от log(0))
        epsilon = 1e-10
        spectrum_db = 20 * np.log10(np.maximum(spectrum, epsilon))
        
        # Ограничение диапазона
        spectrum_db = np.clip(spectrum_db, -100, 0)
        
        # Downsampling для визуализации
        freqs, spectrum_db = self._downsample(freqs, spectrum_db)
        
        return freqs, spectrum_db
    
    def _downsample(
        self,
        freqs: np.ndarray,
        spectrum: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Уменьшить количество точек для визуализации.
        
        Параметры:
        ----------
        freqs : np.ndarray
            Массив частот
        spectrum : np.ndarray
            Массив значений спектра
            
        Возвращает:
        -----------
        Tuple[np.ndarray, np.ndarray]
            (freqs, spectrum) с уменьшенным количеством точек
        """
        n = len(freqs)
        if n <= self._max_points:
            return freqs, spectrum
        
        # Равномерное прореживание
        step = n // self._max_points
        indices = np.arange(0, n, step)[:self._max_points]
        
        return freqs[indices], spectrum[indices]
    
    # =========================================================================
    # СРАВНЕНИЕ СПЕКТРОВ
    # =========================================================================
    
    def compute_spectrum_for_file(
        self,
        file_path: str,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Вычислить спектр для аудиофайла.
        
        Загружает файл и вычисляет его спектр.
        
        Параметры:
        ----------
        file_path : str
            Путь к аудиофайлу
            
        Возвращает:
        -----------
        Tuple[np.ndarray, np.ndarray]
            (частоты, спектр в дБ)
        """
        try:
            # Пытаемся загрузить через разные методы
            signal, sr = self._load_audio(file_path)
            return self.compute_spectrum(signal, sr)
        except Exception as e:
            logger.error(f"Error computing spectrum for {file_path}: {e}")
            return np.array([]), np.array([])
    
    def _load_audio(self, path: str) -> Tuple[np.ndarray, int]:
        """Загрузить аудиофайл.
        
        Параметры:
        ----------
        path : str
            Путь к файлу
            
        Возвращает:
        -----------
        Tuple[np.ndarray, int]
            (сигнал, частота дискретизации)
        """
        # Пробуем разные методы загрузки
        errors = []
        
        # Метод 1: processing.codecs
        try:
            from processing.codecs import decode_audio_to_mono
            return decode_audio_to_mono(path)
        except Exception as e:
            errors.append(f"decode_audio_to_mono: {e}")
        
        # Метод 2: load_wav_mono
        try:
            from processing.codecs import load_wav_mono
            return load_wav_mono(path)
        except Exception as e:
            errors.append(f"load_wav_mono: {e}")
        
        # Метод 3: soundfile
        try:
            import soundfile as sf
            signal, sr = sf.read(path)
            if len(signal.shape) > 1:
                signal = signal.mean(axis=1)  # Моно
            return signal, sr
        except Exception as e:
            errors.append(f"soundfile: {e}")
        
        # Метод 4: scipy
        try:
            from scipy.io import wavfile
            sr, signal = wavfile.read(path)
            if signal.dtype != np.float32:
                signal = signal.astype(np.float32) / 32768.0
            if len(signal.shape) > 1:
                signal = signal.mean(axis=1)
            return signal, sr
        except Exception as e:
            errors.append(f"scipy: {e}")
        
        raise RuntimeError(f"Could not load audio file {path}. Errors: {errors}")
    
    def compare_spectra(
        self,
        source_path: str,
        processed_paths: List[Tuple[str, str]],  # [(method_name, path), ...]
    ) -> SpectrumComparison:
        """Сравнить спектры исходного и обработанных файлов.
        
        Параметры:
        ----------
        source_path : str
            Путь к исходному файлу
        processed_paths : List[Tuple[str, str]]
            Список (имя_метода, путь_к_файлу)
            
        Возвращает:
        -----------
        SpectrumComparison
            Результат сравнения со всеми спектрами
        """
        # Вычисляем спектр источника
        source_freqs, source_spectrum = self.compute_spectrum_for_file(source_path)
        
        source_data = SpectrumData(
            name="Исходный",
            freqs=source_freqs,
            spectrum_db=source_spectrum,
            color=self.DEFAULT_COLORS[0],
        )
        
        processed_data = []
        min_db = np.min(source_spectrum) if len(source_spectrum) > 0 else -100
        max_db = np.max(source_spectrum) if len(source_spectrum) > 0 else 0
        
        for idx, (method_name, path) in enumerate(processed_paths):
            try:
                freqs, spectrum = self.compute_spectrum_for_file(path)
                
                if len(freqs) > 0:
                    color = self.DEFAULT_COLORS[(idx + 1) % len(self.DEFAULT_COLORS)]
                    
                    processed_data.append(SpectrumData(
                        name=method_name.upper(),
                        freqs=freqs,
                        spectrum_db=spectrum,
                        color=color,
                    ))
                    
                    # Обновляем диапазон дБ
                    min_db = min(min_db, np.min(spectrum))
                    max_db = max(max_db, np.max(spectrum))
                    
            except Exception as e:
                logger.error(f"Error computing spectrum for {path}: {e}")
        
        return SpectrumComparison(
            source=source_data,
            processed=processed_data,
            min_db=float(min_db),
            max_db=float(max_db),
        )
    
    # =========================================================================
    # МЕТРИКИ СПЕКТРА
    # =========================================================================
    
    def compute_spectral_similarity(
        self,
        spectrum1: np.ndarray,
        spectrum2: np.ndarray,
    ) -> float:
        """Вычислить сходство спектров (косинусная схожесть).
        
        Параметры:
        ----------
        spectrum1 : np.ndarray
            Первый спектр
        spectrum2 : np.ndarray
            Второй спектр
            
        Возвращает:
        -----------
        float
            Косинусная схожесть от -1 до 1
        """
        # Интерполяция если разная длина
        if len(spectrum1) != len(spectrum2):
            min_len = min(len(spectrum1), len(spectrum2))
            spectrum1 = spectrum1[:min_len]
            spectrum2 = spectrum2[:min_len]
        
        if len(spectrum1) == 0:
            return 0.0
        
        # Косинусная схожесть
        dot = np.dot(spectrum1, spectrum2)
        norm1 = np.linalg.norm(spectrum1)
        norm2 = np.linalg.norm(spectrum2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot / (norm1 * norm2))
    
    def compute_spectral_distance(
        self,
        spectrum1_db: np.ndarray,
        spectrum2_db: np.ndarray,
    ) -> float:
        """Вычислить расстояние между спектрами (LSD).
        
        Параметры:
        ----------
        spectrum1_db : np.ndarray
            Первый спектр в дБ
        spectrum2_db : np.ndarray
            Второй спектр в дБ
            
        Возвращает:
        -----------
        float
            Log-Spectral Distance в дБ
        """
        # Интерполяция если разная длина
        if len(spectrum1_db) != len(spectrum2_db):
            min_len = min(len(spectrum1_db), len(spectrum2_db))
            spectrum1_db = spectrum1_db[:min_len]
            spectrum2_db = spectrum2_db[:min_len]
        
        if len(spectrum1_db) == 0:
            return float('inf')
        
        # LSD = mean((S1 - S2)^2)^0.5
        diff = spectrum1_db - spectrum2_db
        lsd = np.sqrt(np.mean(diff ** 2))
        
        return float(lsd)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "SpectrumService",
    "SpectrumData",
    "SpectrumComparison",
]
