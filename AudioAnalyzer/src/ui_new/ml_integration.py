"""
ML Integration - интеграция с ML моделями для анализа аудио.

Функционал:
- Абстракция MLModel для поддержки различных моделей
- Предобученные модели для классификации аудио
- Автоматическое определение типа аудио (речь, музыка, шум)
- Предсказание качества аудио на основе ML
- Возможность загрузки пользовательских моделей через плагины

Использование:
--------------
>>> from ui_new.ml_integration import MLModelRegistry, AudioClassifier
>>> 
>>> classifier = AudioClassifier()
>>> result = classifier.classify(audio_signal, sample_rate)
"""
from __future__ import annotations

import logging
import os
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Protocol, runtime_checkable

import numpy as np

logger = logging.getLogger("ui_new.ml_integration")


# =============================================================================
# PROTOCOLS
# =============================================================================

@runtime_checkable
class MLModelProtocol(Protocol):
    """Protocol для ML моделей."""
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Выполнить предсказание."""
        ...
    
    def get_model_info(self) -> Dict[str, Any]:
        """Получить информацию о модели."""
        ...


# =============================================================================
# DATA CLASSES
# =============================================================================

class AudioType(Enum):
    """Типы аудио."""
    
    SPEECH = "speech"
    MUSIC = "music"
    NOISE = "noise"
    MIXED = "mixed"
    SILENCE = "silence"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Результат классификации аудио."""
    
    audio_type: AudioType
    confidence: float
    probabilities: Dict[str, float] = field(default_factory=dict)
    features: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь."""
        return {
            "audio_type": self.audio_type.value,
            "confidence": self.confidence,
            "probabilities": self.probabilities,
            "features": self.features,
        }


@dataclass
class QualityPrediction:
    """Предсказание качества аудио."""
    
    predicted_snr: float
    predicted_lsd: float
    quality_score: float  # 0-100
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь."""
        return {
            "predicted_snr": self.predicted_snr,
            "predicted_lsd": self.predicted_lsd,
            "quality_score": self.quality_score,
            "recommendations": self.recommendations,
        }


@dataclass
class ModelInfo:
    """Информация о модели."""
    
    name: str
    version: str
    description: str
    supported_types: List[str]
    input_shape: Tuple[int, ...]
    output_classes: List[str]
    model_path: Optional[str] = None


# =============================================================================
# BASE MODEL CLASS
# =============================================================================

class MLModelBase(ABC):
    """Базовый класс для ML моделей."""
    
    def __init__(self, model_path: Optional[str] = None):
        """Инициализация модели.
        
        Parameters
        ----------
        model_path : Optional[str]
            Путь к файлу модели (для пользовательских моделей)
        """
        self._model_path = model_path
        self._model = None
        self._is_loaded = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Имя модели."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Версия модели."""
        pass
    
    @abstractmethod
    def load(self) -> bool:
        """Загрузить модель.
        
        Returns
        -------
        bool
            True при успехе
        """
        pass
    
    @abstractmethod
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Выполнить предсказание.
        
        Parameters
        ----------
        features : np.ndarray
            Признаки аудио
            
        Returns
        -------
        np.ndarray
            Результат предсказания
        """
        pass
    
    def is_loaded(self) -> bool:
        """Проверить, загружена ли модель."""
        return self._is_loaded
    
    def get_info(self) -> ModelInfo:
        """Получить информацию о модели."""
        return ModelInfo(
            name=self.name,
            version=self.version,
            description=self.__doc__ or "",
            supported_types=["audio"],
            input_shape=(0,),
            output_classes=[],
            model_path=self._model_path,
        )


# =============================================================================
# FEATURE EXTRACTOR
# =============================================================================

class AudioFeatureExtractor:
    """Извлечение признаков из аудио для ML моделей."""
    
    @staticmethod
    def extract_features(
        signal: np.ndarray,
        sample_rate: int,
        n_mfcc: int = 13,
    ) -> Dict[str, np.ndarray]:
        """Извлечь признаки из аудиосигнала.
        
        Parameters
        ----------
        signal : np.ndarray
            Аудиосигнал
        sample_rate : int
            Частота дискретизации
        n_mfcc : int
            Количество MFCC коэффициентов
            
        Returns
        -------
        Dict[str, np.ndarray]
            Словарь признаков
        """
        features = {}
        
        # Статистики сигнала
        features['rms'] = np.sqrt(np.mean(signal ** 2))
        features['zero_crossing_rate'] = np.mean(np.abs(np.diff(np.sign(signal))))
        features['duration'] = len(signal) / sample_rate
        
        # Спектральные признаки
        fft = np.fft.rfft(signal)
        spectrum = np.abs(fft)
        freqs = np.fft.rfftfreq(len(signal), 1.0 / sample_rate)
        
        # Спектральный центроид
        features['spectral_centroid'] = np.sum(freqs * spectrum) / (np.sum(spectrum) + 1e-10)
        
        # Спектральный спад (rolloff)
        cumsum = np.cumsum(spectrum)
        rolloff_threshold = 0.85 * cumsum[-1]
        rolloff_idx = np.searchsorted(cumsum, rolloff_threshold)
        features['spectral_rolloff'] = freqs[min(rolloff_idx, len(freqs) - 1)]
        
        # Спектральная плоскость
        features['spectral_flatness'] = np.exp(np.mean(np.log(spectrum + 1e-10))) / (np.mean(spectrum) + 1e-10)
        
        # Спектральная полоса пропускания
        centroid = features['spectral_centroid']
        features['spectral_bandwidth'] = np.sqrt(
            np.sum(((freqs - centroid) ** 2) * spectrum) / (np.sum(spectrum) + 1e-10)
        )
        
        # MFCC (упрощённая реализация)
        features['mfcc_mean'] = AudioFeatureExtractor._compute_mfcc_mean(
            signal, sample_rate, n_mfcc
        )
        
        # Энергия в частотных полосах
        n_bands = 8
        band_energies = AudioFeatureExtractor._compute_band_energies(
            spectrum, freqs, n_bands
        )
        features['band_energies'] = band_energies
        
        return features
    
    @staticmethod
    def _compute_mfcc_mean(
        signal: np.ndarray,
        sample_rate: int,
        n_mfcc: int
    ) -> np.ndarray:
        """Вычислить средние MFCC."""
        try:
            # Простой расчёт MFCC без librosa
            n_fft = min(2048, len(signal))
            fft = np.fft.rfft(signal[:n_fft])
            spectrum = np.abs(fft) ** 2
            
            # Mel фильтры
            n_mels = 40
            mel_spectrum = np.zeros(n_mels)
            
            freqs = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
            
            for i in range(n_mels):
                mel_start = 1500 * i / n_mels
                mel_end = 1500 * (i + 1) / n_mels
                
                mask = (freqs >= mel_start) & (freqs < mel_end)
                if np.any(mask):
                    mel_spectrum[i] = np.mean(spectrum[mask])
            
            # DCT для MFCC
            log_mel = np.log(mel_spectrum + 1e-10)
            mfcc = np.fft.dct(log_mel, type=2, norm='ortho')[:n_mfcc]
            
            return mfcc
            
        except Exception:
            return np.zeros(n_mfcc)
    
    @staticmethod
    def _compute_band_energies(
        spectrum: np.ndarray,
        freqs: np.ndarray,
        n_bands: int
    ) -> np.ndarray:
        """Вычислить энергию в частотных полосах."""
        max_freq = min(8000, freqs[-1])
        band_edges = np.linspace(0, max_freq, n_bands + 1)
        
        energies = np.zeros(n_bands)
        
        for i in range(n_bands):
            mask = (freqs >= band_edges[i]) & (freqs < band_edges[i + 1])
            if np.any(mask):
                energies[i] = np.sum(spectrum[mask] ** 2)
        
        # Нормализация
        total = np.sum(energies) + 1e-10
        return energies / total
    
    @staticmethod
    def extract_feature_vector(
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """Извлечь вектор признаков для ML модели.
        
        Returns
        -------
        np.ndarray
            1D массив признаков фиксированной длины
        """
        features = AudioFeatureExtractor.extract_features(signal, sample_rate)
        
        # Формируем вектор
        vector = []
        
        # Скалярные признаки
        vector.append(features['rms'])
        vector.append(features['zero_crossing_rate'])
        vector.append(features['spectral_centroid'] / 10000)  # Нормализация
        vector.append(features['spectral_rolloff'] / 10000)
        vector.append(features['spectral_flatness'])
        vector.append(features['spectral_bandwidth'] / 10000)
        
        # MFCC (первые 13)
        mfcc = features['mfcc_mean']
        vector.extend(mfcc[:13] if len(mfcc) >= 13 else list(mfcc) + [0] * (13 - len(mfcc)))
        
        # Энергии полос
        band_energies = features['band_energies']
        vector.extend(band_energies)
        
        return np.array(vector, dtype=np.float32)


# =============================================================================
# AUDIO CLASSIFIER
# =============================================================================

class AudioClassifier(MLModelBase):
    """Классификатор типа аудио (речь/музыка/шум).
    
    Использует правило-базированную классификацию без внешних зависимостей.
    Для продакшена рекомендуется заменить на реальную ML модель.
    """
    
    def __init__(self):
        super().__init__()
        self._is_loaded = True  # Встроенная модель
    
    @property
    def name(self) -> str:
        return "AudioClassifier"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def load(self) -> bool:
        """Загрузка не требуется для встроенной модели."""
        return True
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Предсказать тип аудио."""
        # Для встроенной модели не используется
        return np.array([0])
    
    def classify(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> ClassificationResult:
        """Классифицировать тип аудио.
        
        Parameters
        ----------
        signal : np.ndarray
            Аудиосигнал
        sample_rate : int
            Частота дискретизации
            
        Returns
        -------
        ClassificationResult
            Результат классификации
        """
        features = AudioFeatureExtractor.extract_features(signal, sample_rate)
        
        # Правило-базированная классификация
        probabilities = {}
        
        # Вычисляем признаки для классификации
        zcr = features['zero_crossing_rate']
        flatness = features['spectral_flatness']
        centroid = features['spectral_centroid']
        rms = features['rms']
        
        # Тишина
        if rms < 0.001:
            audio_type = AudioType.SILENCE
            probabilities['silence'] = 0.95
            probabilities['speech'] = 0.03
            probabilities['music'] = 0.01
            probabilities['noise'] = 0.01
        
        # Речь: высокий ZCR, средний центроид, низкая плоскость
        elif zcr > 0.05 and 1000 < centroid < 4000 and flatness < 0.3:
            audio_type = AudioType.SPEECH
            probabilities['speech'] = 0.70
            probabilities['music'] = 0.15
            probabilities['noise'] = 0.10
            probabilities['mixed'] = 0.05
        
        # Музыка: высокий центроид, низкая плоскость
        elif centroid > 3000 and flatness < 0.2:
            audio_type = AudioType.MUSIC
            probabilities['music'] = 0.75
            probabilities['speech'] = 0.10
            probabilities['noise'] = 0.10
            probabilities['mixed'] = 0.05
        
        # Шум: высокая плоскость
        elif flatness > 0.5:
            audio_type = AudioType.NOISE
            probabilities['noise'] = 0.80
            probabilities['speech'] = 0.10
            probabilities['music'] = 0.05
            probabilities['silence'] = 0.05
        
        # Смешанный тип
        else:
            audio_type = AudioType.MIXED
            probabilities['mixed'] = 0.50
            probabilities['speech'] = 0.25
            probabilities['music'] = 0.20
            probabilities['noise'] = 0.05
        
        # Вычисляем уверенность
        confidence = max(probabilities.values())
        
        return ClassificationResult(
            audio_type=audio_type,
            confidence=confidence,
            probabilities=probabilities,
            features={
                'zcr': zcr,
                'flatness': flatness,
                'centroid': centroid,
                'rms': rms,
            }
        )


# =============================================================================
# QUALITY PREDICTOR
# =============================================================================

class QualityPredictor(MLModelBase):
    """Предсказатель качества аудио.
    
    Предсказывает примерные значения SNR и LSD на основе признаков.
    """
    
    def __init__(self):
        super().__init__()
        self._is_loaded = True
    
    @property
    def name(self) -> str:
        return "QualityPredictor"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def load(self) -> bool:
        return True
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        return np.array([0, 0])
    
    def predict_quality(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> QualityPrediction:
        """Предсказать качество аудио.
        
        Parameters
        ----------
        signal : np.ndarray
            Аудиосигнал
        sample_rate : int
            Частота дискретизации
            
        Returns
        -------
        QualityPrediction
            Предсказание качества
        """
        features = AudioFeatureExtractor.extract_features(signal, sample_rate)
        
        # Эвристическое предсказание на основе признаков
        
        # SNR: связан с динамическим диапазоном
        rms = features['rms']
        peak = np.max(np.abs(signal)) + 1e-10
        dynamic_range_db = 20 * np.log10(peak / (rms + 1e-10))
        
        # Примерный SNR (эвристика)
        predicted_snr = min(50, max(0, dynamic_range_db * 0.7))
        
        # LSD: связан со спектральной плоскостью
        flatness = features['spectral_flatness']
        predicted_lsd = flatness * 5  # Эвристика
        
        # Общий балл качества (0-100)
        quality_score = min(100, max(0,
            100 - flatness * 50 - predicted_lsd * 10
        ))
        
        # Рекомендации
        recommendations = []
        
        if rms < 0.01:
            recommendations.append("Низкий уровень громкости - нормализуйте аудио")
        
        if flatness > 0.4:
            recommendations.append("Высокий уровень шума - примените шумоподавление")
        
        if dynamic_range_db < 20:
            recommendations.append("Низкий динамический диапазон - проверьте компрессию")
        
        if features['spectral_centroid'] < 500:
            recommendations.append("Низкочастотный контент доминирует")
        
        if not recommendations:
            recommendations.append("Качество аудио в норме")
        
        return QualityPrediction(
            predicted_snr=predicted_snr,
            predicted_lsd=predicted_lsd,
            quality_score=quality_score,
            recommendations=recommendations,
        )


# =============================================================================
# MODEL REGISTRY
# =============================================================================

class MLModelRegistry:
    """Реестр ML моделей.
    
    Управляет регистрацией и доступом к моделям.
    """
    
    _models: Dict[str, MLModelBase] = {}
    _initialized = False
    
    @classmethod
    def initialize(cls) -> None:
        """Инициализировать реестр с встроенными моделями."""
        if cls._initialized:
            return
        
        # Регистрируем встроенные модели
        cls.register('audio_classifier', AudioClassifier())
        cls.register('quality_predictor', QualityPredictor())
        
        cls._initialized = True
        logger.info("MLModelRegistry initialized")
    
    @classmethod
    def register(cls, name: str, model: MLModelBase) -> None:
        """Зарегистрировать модель.
        
        Parameters
        ----------
        name : str
            Имя модели
        model : MLModelBase
            Экземпляр модели
        """
        cls._models[name] = model
        logger.debug("Model registered: %s", name)
    
    @classmethod
    def get(cls, name: str) -> Optional[MLModelBase]:
        """Получить модель по имени.
        
        Parameters
        ----------
        name : str
            Имя модели
            
        Returns
        -------
        Optional[MLModelBase]
            Модель или None если не найдена
        """
        if not cls._initialized:
            cls.initialize()
        
        return cls._models.get(name)
    
    @classmethod
    def get_all(cls) -> Dict[str, MLModelBase]:
        """Получить все модели."""
        if not cls._initialized:
            cls.initialize()
        
        return cls._models.copy()
    
    @classmethod
    def get_available_models(cls) -> List[str]:
        """Получить список доступных моделей."""
        if not cls._initialized:
            cls.initialize()
        
        return list(cls._models.keys())


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def classify_audio(signal: np.ndarray, sample_rate: int) -> ClassificationResult:
    """Классифицировать тип аудио.
    
    Parameters
    ----------
    signal : np.ndarray
        Аудиосигнал
    sample_rate : int
        Частота дискретизации
        
    Returns
    -------
    ClassificationResult
        Результат классификации
    """
    classifier = MLModelRegistry.get('audio_classifier')
    if classifier:
        return classifier.classify(signal, sample_rate)
    
    # Fallback
    return ClassificationResult(
        audio_type=AudioType.UNKNOWN,
        confidence=0.0,
    )


def predict_audio_quality(signal: np.ndarray, sample_rate: int) -> QualityPrediction:
    """Предсказать качество аудио.
    
    Parameters
    ----------
    signal : np.ndarray
        Аудиосигнал
    sample_rate : int
        Частота дискретизации
        
    Returns
    -------
    QualityPrediction
        Предсказание качества
    """
    predictor = MLModelRegistry.get('quality_predictor')
    if predictor:
        return predictor.predict_quality(signal, sample_rate)
    
    # Fallback
    return QualityPrediction(
        predicted_snr=0.0,
        predicted_lsd=0.0,
        quality_score=0.0,
        recommendations=["ML модели недоступны"],
    )


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Protocols
    "MLModelProtocol",
    # Data classes
    "AudioType",
    "ClassificationResult",
    "QualityPrediction",
    "ModelInfo",
    # Classes
    "MLModelBase",
    "AudioFeatureExtractor",
    "AudioClassifier",
    "QualityPredictor",
    "MLModelRegistry",
    # Functions
    "classify_audio",
    "predict_audio_quality",
]
