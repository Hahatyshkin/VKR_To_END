"""
Фоновый обработчик для вычисления спектров.

Предотвращает зависание UI при анализе больших файлов.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from PySide6.QtCore import QObject, Signal, QThread

logger = logging.getLogger("ui_new.widgets.spectrum_worker")


class SpectrumWorker(QObject):
    """Фоновое вычисление спектров.

    Сигналы:
    - progress(str): сообщение о прогрессе
    - spectrum_ready(str, np.ndarray, np.ndarray): имя, частоты, амплитуды
    - error(str): сообщение об ошибке
    - finished(): завершение обработки
    """

    progress = Signal(str)
    spectrum_ready = Signal(str, np.ndarray, np.ndarray)  # name, freqs, spectrum_db
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        source_path: str,
        selected_files: List[Tuple[str, str]],
        n_fft: int = 4096,
    ):
        """Инициализация.

        Параметры:
        ----------
        source_path : str
            Путь к исходному файлу
        selected_files : List[Tuple[str, str]]
            Список (метод, путь) для сравнения
        n_fft : int
            Размер FFT для вычисления спектра
        """
        super().__init__()
        self.source_path = source_path
        self.selected_files = selected_files
        self.n_fft = n_fft
        self._cancelled = False

    def cancel(self) -> None:
        """Отменить обработку."""
        self._cancelled = True

    def _compute_spectrum(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Вычислить спектр сигнала.

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

        # Даунсамплинг для производительности (максимум 2000 точек)
        max_points = 2000
        if len(frequencies) > max_points:
            step = len(frequencies) // max_points
            frequencies = frequencies[::step]
            spectrum_db = spectrum_db[::step]

        return frequencies, spectrum_db

    def run(self) -> None:
        """Выполнить вычисление спектров."""
        try:
            # Загружаем исходный файл
            self.progress.emit(f"Загрузка: {self.source_path}")

            try:
                from processing.codecs import load_wav_mono, decode_audio_to_mono
            except ImportError:
                from src.processing.codecs import load_wav_mono, decode_audio_to_mono

            try:
                signal, sr = load_wav_mono(self.source_path)
            except Exception:
                signal, sr = decode_audio_to_mono(self.source_path)

            if self._cancelled:
                return

            self.progress.emit(f"Загружено: {len(signal)} сэмплов, {sr} Гц")

            # Вычисляем спектр исходного файла
            self.progress.emit("Вычисление спектра: Исходный...")
            freqs, spectrum_db = self._compute_spectrum(signal, sr)
            self.spectrum_ready.emit("Исходный", freqs, spectrum_db)

            if self._cancelled:
                return

            # Вычисляем спектры для каждого выбранного файла
            for idx, (method, path) in enumerate(self.selected_files):
                if self._cancelled:
                    break

                self.progress.emit(f"Вычисление спектра: {method.upper()}... ({idx + 1}/{len(self.selected_files)})")

                try:
                    try:
                        signal2, sr2 = decode_audio_to_mono(path)
                    except Exception:
                        signal2, sr2 = load_wav_mono(path)

                    freqs2, spectrum_db2 = self._compute_spectrum(signal2, sr2)
                    self.spectrum_ready.emit(method.upper(), freqs2, spectrum_db2)

                except Exception as e:
                    self.error.emit(f"Ошибка {method}: {e}")
                    logger.error(f"Error computing spectrum for {method}: {e}")

            self.progress.emit("Спектр построен успешно")

        except Exception as e:
            self.error.emit(f"Ошибка: {e}")
            logger.error(f"Error in SpectrumWorker: {e}")

        finally:
            self.finished.emit()


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "SpectrumWorker",
]
