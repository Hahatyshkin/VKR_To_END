"""
Виджеты UI для AudioAnalyzer.

Модули:
- spectrum_widget: Интерактивный виджет спектра (pyqtgraph)
- spectrum_worker: Фоновое вычисление спектра
- results_table: Таблица результатов с контекстным меню
- spectrogram_3d: 3D визуализация спектрограммы
"""

# Ленивый импорт для избежания ImportError при отсутствии pyqtgraph

def __getattr__(name):
    """Ленивый импорт модулей."""
    if name == "InteractiveSpectrumWidget":
        from .spectrum_widget import InteractiveSpectrumWidget
        return InteractiveSpectrumWidget
    elif name == "SpectrumCalculator":
        from .spectrum_widget import SpectrumCalculator
        return SpectrumCalculator
    elif name == "SpectrumWorker":
        from .spectrum_worker import SpectrumWorker
        return SpectrumWorker
    elif name == "ResultsTable":
        from .results_table import ResultsTable
        return ResultsTable
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "InteractiveSpectrumWidget",
    "SpectrumCalculator",
    "SpectrumWorker",
    "ResultsTable",
]
