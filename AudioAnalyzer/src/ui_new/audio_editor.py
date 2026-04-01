"""
Audio Editor - базовое редактирование аудио.

Функционал:
- Обрезка аудиофайлов (trim)
- Нормализация громкости
- Fade In/Fade Out эффекты
- Экспорт в различные форматы

Использование:
--------------
>>> from ui_new.audio_editor import AudioEditor, EditOperation
>>> 
>>> editor = AudioEditor()
>>> edited = editor.apply(signal, sample_rate, EditOperation.NORMALIZE)
"""
from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger("ui_new.audio_editor")


# =============================================================================
# ENUMS
# =============================================================================

class EditOperation(Enum):
    """Операции редактирования."""
    
    TRIM = "trim"
    NORMALIZE = "normalize"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    REVERSE = "reverse"
    AMPLIFY = "amplify"
    RESAMPLE = "resample"
    CONVERT_TO_MONO = "to_mono"
    SILENCE_REMOVE = "silence_remove"


class ExportFormat(Enum):
    """Форматы экспорта."""
    
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EditResult:
    """Результат операции редактирования."""
    
    signal: np.ndarray
    sample_rate: int
    operation: EditOperation
    success: bool = True
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь."""
        return {
            "operation": self.operation.value,
            "success": self.success,
            "message": self.message,
            "duration": len(self.signal) / self.sample_rate,
        }


@dataclass
class TrimParams:
    """Параметры обрезки."""
    
    start_time: float = 0.0  # секунды
    end_time: Optional[float] = None  # секунды (None = до конца)
    
    def validate(self, total_duration: float) -> Tuple[float, float]:
        """Валидировать и вернуть начальную и конечную позиции.
        
        Parameters
        ----------
        total_duration : float
            Общая длительность аудио в секундах
            
        Returns
        -------
        Tuple[float, float]
            (start, end) в секундах
        """
        start = max(0.0, self.start_time)
        end = min(total_duration, self.end_time or total_duration)
        
        if start >= end:
            raise ValueError(f"Invalid trim range: {start} >= {end}")
        
        return start, end


@dataclass
class FadeParams:
    """Параметры fade эффекта."""
    
    duration: float = 1.0  # секунды
    curve: str = "linear"  # linear, exponential, logarithmic
    
    def get_curve(self) -> np.ndarray:
        """Получить кривую fade."""
        n = 100
        t = np.linspace(0, 1, n)
        
        if self.curve == "exponential":
            return t ** 2
        elif self.curve == "logarithmic":
            return np.log(1 + 9 * t) / np.log(10)
        else:  # linear
            return t


# =============================================================================
# AUDIO EDITOR
# =============================================================================

class AudioEditor:
    """Редактор аудио с базовыми операциями.
    
    Поддерживаемые операции:
    - trim: обрезка по времени
    - normalize: нормализация до целевого уровня dB
    - fade_in: плавное нарастание
    - fade_out: плавное затухание
    - reverse: реверс аудио
    - amplify: усиление/ослабление
    - resample: изменение частоты дискретизации
    - to_mono: преобразование в моно
    - silence_remove: удаление тишины
    """
    
    def __init__(self):
        """Инициализация редактора."""
        self._operations: Dict[EditOperation, Callable] = {
            EditOperation.TRIM: self._trim,
            EditOperation.NORMALIZE: self._normalize,
            EditOperation.FADE_IN: self._fade_in,
            EditOperation.FADE_OUT: self._fade_out,
            EditOperation.REVERSE: self._reverse,
            EditOperation.AMPLIFY: self._amplify,
            EditOperation.RESAMPLE: self._resample,
            EditOperation.CONVERT_TO_MONO: self._to_mono,
            EditOperation.SILENCE_REMOVE: self._silence_remove,
        }
    
    # =========================================================================
    # MAIN API
    # =========================================================================
    
    def apply(
        self,
        signal: np.ndarray,
        sample_rate: int,
        operation: EditOperation,
        **params
    ) -> EditResult:
        """Применить операцию к аудиосигналу.
        
        Parameters
        ----------
        signal : np.ndarray
            Аудиосигнал
        sample_rate : int
            Частота дискретизации
        operation : EditOperation
            Операция редактирования
        **params : Dict
            Параметры операции
            
        Returns
        -------
        EditResult
            Результат операции
        """
        handler = self._operations.get(operation)
        
        if handler is None:
            return EditResult(
                signal=signal,
                sample_rate=sample_rate,
                operation=operation,
                success=False,
                message=f"Unknown operation: {operation}",
            )
        
        try:
            result_signal = handler(signal, sample_rate, **params)
            
            return EditResult(
                signal=result_signal,
                sample_rate=sample_rate,
                operation=operation,
                success=True,
                message=f"Operation {operation.value} applied successfully",
            )
            
        except Exception as e:
            logger.error("Edit operation failed: %s", e)
            return EditResult(
                signal=signal,
                sample_rate=sample_rate,
                operation=operation,
                success=False,
                message=f"Error: {str(e)}",
            )
    
    def apply_chain(
        self,
        signal: np.ndarray,
        sample_rate: int,
        operations: List[Tuple[EditOperation, Dict]],
    ) -> EditResult:
        """Применить цепочку операций.
        
        Parameters
        ----------
        signal : np.ndarray
            Аудиосигнал
        sample_rate : int
            Частота дискретизации
        operations : List[Tuple[EditOperation, Dict]]
            Список (операция, параметры)
            
        Returns
        -------
        EditResult
            Результат последней операции
        """
        current_signal = signal.copy()
        result = None
        
        for operation, params in operations:
            result = self.apply(
                current_signal, sample_rate, operation, **params
            )
            
            if not result.success:
                return result
            
            current_signal = result.signal
        
        return result or EditResult(
            signal=signal,
            sample_rate=sample_rate,
            operation=EditOperation.TRIM,
            success=True,
        )
    
    # =========================================================================
    # OPERATIONS
    # =========================================================================
    
    def _trim(
        self,
        signal: np.ndarray,
        sample_rate: int,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
        **kwargs
    ) -> np.ndarray:
        """Обрезать аудио."""
        params = TrimParams(start_time=start_time, end_time=end_time)
        total_duration = len(signal) / sample_rate
        start, end = params.validate(total_duration)
        
        start_sample = int(start * sample_rate)
        end_sample = int(end * sample_rate)
        
        return signal[start_sample:end_sample].copy()
    
    def _normalize(
        self,
        signal: np.ndarray,
        sample_rate: int,
        target_db: float = -3.0,
        **kwargs
    ) -> np.ndarray:
        """Нормализовать громкость.
        
        Parameters
        ----------
        signal : np.ndarray
            Аудиосигнал
        sample_rate : int
            Частота дискретизации
        target_db : float
            Целевой пиковый уровень в dB (отрицательное значение)
        """
        # Находим текущий пик
        peak = np.max(np.abs(signal))
        
        if peak < 1e-10:
            logger.warning("Signal is silent, cannot normalize")
            return signal.copy()
        
        # Целевой пик
        target_peak = 10 ** (target_db / 20)
        
        # Коэффициент нормализации
        gain = target_peak / peak
        
        return (signal * gain).astype(signal.dtype)
    
    def _fade_in(
        self,
        signal: np.ndarray,
        sample_rate: int,
        duration: float = 1.0,
        curve: str = "linear",
        **kwargs
    ) -> np.ndarray:
        """Применить fade in."""
        params = FadeParams(duration=duration, curve=curve)
        curve_values = params.get_curve()
        
        n_samples = int(duration * sample_rate)
        
        if n_samples >= len(signal):
            n_samples = len(signal)
            curve_values = np.linspace(0, 1, n_samples)
        else:
            curve_values = np.interp(
                np.linspace(0, 1, n_samples),
                np.linspace(0, 1, len(curve_values)),
                curve_values
            )
        
        result = signal.copy()
        
        # Применяем fade
        fade_region = result[:n_samples].astype(np.float64)
        fade_region *= curve_values
        result[:n_samples] = fade_region.astype(signal.dtype)
        
        return result
    
    def _fade_out(
        self,
        signal: np.ndarray,
        sample_rate: int,
        duration: float = 1.0,
        curve: str = "linear",
        **kwargs
    ) -> np.ndarray:
        """Применить fade out."""
        params = FadeParams(duration=duration, curve=curve)
        curve_values = params.get_curve()
        
        n_samples = int(duration * sample_rate)
        
        if n_samples >= len(signal):
            n_samples = len(signal)
            curve_values = np.linspace(1, 0, n_samples)
        else:
            curve_values = np.interp(
                np.linspace(0, 1, n_samples),
                np.linspace(0, 1, len(curve_values)),
                curve_values
            )
        
        result = signal.copy()
        
        # Применяем fade
        fade_region = result[-n_samples:].astype(np.float64)
        fade_region *= curve_values[::-1]
        result[-n_samples:] = fade_region.astype(signal.dtype)
        
        return result
    
    def _reverse(
        self,
        signal: np.ndarray,
        sample_rate: int,
        **kwargs
    ) -> np.ndarray:
        """Реверс аудио."""
        return signal[::-1].copy()
    
    def _amplify(
        self,
        signal: np.ndarray,
        sample_rate: int,
        gain_db: float = 0.0,
        **kwargs
    ) -> np.ndarray:
        """Усилить или ослабить сигнал.
        
        Parameters
        ----------
        gain_db : float
            Усиление в dB (положительное = громче, отрицательное = тише)
        """
        gain = 10 ** (gain_db / 20)
        return (signal * gain).astype(np.float32)
    
    def _resample(
        self,
        signal: np.ndarray,
        sample_rate: int,
        target_rate: int = 44100,
        **kwargs
    ) -> Tuple[np.ndarray, int]:
        """Изменить частоту дискретизации.
        
        Note: Возвращает tuple (signal, new_sample_rate)
        """
        if target_rate == sample_rate:
            return signal
        
        # Простой метод передискретизации
        ratio = target_rate / sample_rate
        n_samples = int(len(signal) * ratio)
        
        # Линейная интерполяция
        old_indices = np.arange(len(signal))
        new_indices = np.linspace(0, len(signal) - 1, n_samples)
        
        resampled = np.interp(new_indices, old_indices, signal.astype(np.float64))
        
        return resampled.astype(np.float32)
    
    def _to_mono(
        self,
        signal: np.ndarray,
        sample_rate: int,
        **kwargs
    ) -> np.ndarray:
        """Преобразовать в моно."""
        if signal.ndim == 1:
            return signal
        
        # Усредняем каналы
        return np.mean(signal, axis=1).astype(np.float32)
    
    def _silence_remove(
        self,
        signal: np.ndarray,
        sample_rate: int,
        threshold_db: float = -40.0,
        min_silence_duration: float = 0.1,
        **kwargs
    ) -> np.ndarray:
        """Удалить тишину.
        
        Parameters
        ----------
        threshold_db : float
            Порог тишины в dB
        min_silence_duration : float
            Минимальная длительность тишины для удаления в секундах
        """
        # Порог в линейной шкале
        threshold = 10 ** (threshold_db / 20)
        
        # Находим негilent области
        abs_signal = np.abs(signal)
        is_loud = abs_signal > threshold
        
        # Морфологическая операция для устранения коротких пауз
        from scipy import ndimage
        
        min_samples = int(min_silence_duration * sample_rate)
        
        try:
            # Расширяем громкие области
            structure = np.ones(min_samples)
            is_loud_dilated = ndimage.binary_dilation(is_loud, structure=structure)
            
            # Выбираем негilent области
            result = signal[is_loud_dilated]
            
            return result
            
        except ImportError:
            # Fallback без scipy
            logger.warning("scipy not available, using simple silence removal")
            
            # Простой метод: находим границы негilent областей
            non_silent_indices = np.where(is_loud)[0]
            
            if len(non_silent_indices) == 0:
                return np.array([], dtype=signal.dtype)
            
            start = non_silent_indices[0]
            end = non_silent_indices[-1] + 1
            
            return signal[start:end].copy()
    
    # =========================================================================
    # EXPORT
    # =========================================================================
    
    def export(
        self,
        signal: np.ndarray,
        sample_rate: int,
        output_path: str,
        format: Optional[ExportFormat] = None,
        bitrate: str = "192k",
    ) -> bool:
        """Экспортировать аудио в файл.
        
        Parameters
        ----------
        signal : np.ndarray
            Аудиосигнал
        sample_rate : int
            Частота дискретизации
        output_path : str
            Путь к выходному файлу
        format : Optional[ExportFormat]
            Формат (определяется по расширению если не указан)
        bitrate : str
            Битрейт для MP3
            
        Returns
        -------
        bool
            True при успехе
        """
        # Определяем формат
        if format is None:
            ext = Path(output_path).suffix.lower()
            format_map = {
                '.wav': ExportFormat.WAV,
                '.mp3': ExportFormat.MP3,
                '.flac': ExportFormat.FLAC,
                '.ogg': ExportFormat.OGG,
            }
            format = format_map.get(ext, ExportFormat.WAV)
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if format == ExportFormat.WAV:
                return self._export_wav(signal, sample_rate, output_path)
            elif format == ExportFormat.MP3:
                return self._export_mp3(signal, sample_rate, output_path, bitrate)
            elif format == ExportFormat.FLAC:
                return self._export_flac(signal, sample_rate, output_path)
            else:
                logger.warning("Format %s not supported, using WAV", format)
                return self._export_wav(signal, sample_rate, output_path)
                
        except Exception as e:
            logger.error("Export failed: %s", e)
            return False
    
    def _export_wav(
        self,
        signal: np.ndarray,
        sample_rate: int,
        output_path: str,
    ) -> bool:
        """Экспорт в WAV."""
        import wave
        import struct
        
        # Конвертируем в int16
        signal_int = (signal * 32767).astype(np.int16)
        
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(signal_int.tobytes())
        
        logger.info("Exported WAV to %s", output_path)
        return True
    
    def _export_mp3(
        self,
        signal: np.ndarray,
        sample_rate: int,
        output_path: str,
        bitrate: str,
    ) -> bool:
        """Экспорт в MP3."""
        try:
            from processing.codecs import encode_pcm_to_mp3
            
            # Сначала сохраняем как временный WAV
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name
            
            self._export_wav(signal, sample_rate, tmp_path)
            
            # Кодируем в MP3
            from processing.codecs import load_wav_mono
            audio, sr = load_wav_mono(tmp_path)
            
            encode_pcm_to_mp3(audio, sample_rate, output_path, bitrate)
            
            # Удаляем временный файл
            os.unlink(tmp_path)
            
            logger.info("Exported MP3 to %s", output_path)
            return True
            
        except Exception as e:
            logger.error("MP3 export failed: %s", e)
            return False
    
    def _export_flac(
        self,
        signal: np.ndarray,
        sample_rate: int,
        output_path: str,
    ) -> bool:
        """Экспорт в FLAC."""
        try:
            import soundfile as sf
            sf.write(output_path, signal, sample_rate, format='FLAC')
            logger.info("Exported FLAC to %s", output_path)
            return True
        except ImportError:
            logger.warning("soundfile not available for FLAC export")
            # Fallback to WAV
            return self._export_wav(signal, sample_rate, output_path.replace('.flac', '.wav'))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def trim_audio(
    signal: np.ndarray,
    sample_rate: int,
    start_time: float = 0.0,
    end_time: Optional[float] = None,
) -> np.ndarray:
    """Обрезать аудио.
    
    Parameters
    ----------
    signal : np.ndarray
        Аудиосигнал
    sample_rate : int
        Частота дискретизации
    start_time : float
        Начальное время в секундах
    end_time : Optional[float]
        Конечное время в секундах
        
    Returns
    -------
    np.ndarray
        Обрезанный сигнал
    """
    editor = AudioEditor()
    result = editor.apply(
        signal, sample_rate, EditOperation.TRIM,
        start_time=start_time, end_time=end_time
    )
    return result.signal


def normalize_audio(
    signal: np.ndarray,
    sample_rate: int,
    target_db: float = -3.0,
) -> np.ndarray:
    """Нормализовать аудио.
    
    Parameters
    ----------
    signal : np.ndarray
        Аудиосигнал
    sample_rate : int
        Частота дискретизации
    target_db : float
        Целевой пиковый уровень в dB
        
    Returns
    -------
    np.ndarray
        Нормализованный сигнал
    """
    editor = AudioEditor()
    result = editor.apply(
        signal, sample_rate, EditOperation.NORMALIZE,
        target_db=target_db
    )
    return result.signal


def apply_fade(
    signal: np.ndarray,
    sample_rate: int,
    fade_in_duration: float = 0.0,
    fade_out_duration: float = 0.0,
) -> np.ndarray:
    """Применить fade in/out.
    
    Parameters
    ----------
    signal : np.ndarray
        Аудиосигнал
    sample_rate : int
        Частота дискретизации
    fade_in_duration : float
        Длительность fade in в секундах
    fade_out_duration : float
        Длительность fade out в секундах
        
    Returns
    -------
    np.ndarray
        Сигнал с применёнными fade эффектами
    """
    editor = AudioEditor()
    
    result = signal.copy()
    
    if fade_in_duration > 0:
        result = editor.apply(
            result, sample_rate, EditOperation.FADE_IN,
            duration=fade_in_duration
        ).signal
    
    if fade_out_duration > 0:
        result = editor.apply(
            result, sample_rate, EditOperation.FADE_OUT,
            duration=fade_out_duration
        ).signal
    
    return result


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Enums
    "EditOperation",
    "ExportFormat",
    # Data classes
    "EditResult",
    "TrimParams",
    "FadeParams",
    # Classes
    "AudioEditor",
    # Functions
    "trim_audio",
    "normalize_audio",
    "apply_fade",
]
