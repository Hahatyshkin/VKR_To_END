# transforms

Модуль реализаций методов трансформации аудиосигналов.

## Назначение

Предоставляет единообразную архитектуру для всех методов обработки аудиосигналов перед кодированием в MP3. Каждый метод реализован в отдельном файле и наследует от абстрактного базового класса `BaseTransform`.

## Структура модуля

```
transforms/
├── __init__.py      # Экспорт всех трансформаций и утилит
├── base.py          # BaseTransform + OLA утилиты
├── fft.py           # FFTTransform — Быстрое преобразование Фурье
├── dct.py           # DCTTransform — Дискретное косинусное преобразование
├── dwt.py           # DWTTransform — Вейвлет-преобразование Хаара
├── fwht.py          # FWHTTransform — Преобразование Уолша-Адамара
├── huffman.py       # HuffmanTransform — μ-law компандирование
└── rosenbrock.py    # RosenbrockTransform — Нелинейное сглаживание
```

## Доступные трансформации

| Класс | Имя | Описание | Особенности |
|-------|-----|----------|-------------|
| `FFTTransform` | FFT | Быстрое преобразование Фурье | Комплексные коэффициенты, частотный анализ |
| `DCTTransform` | DCT | Дискретное косинусное преобразование | Действительные коэффициенты, стандарт MP3/JPEG |
| `DWTTransform` | DWT | Вейвлет Хаара | Многоуровневая декомпозиция, 5 частотных полос |
| `FWHTTransform` | FWHT | Преобразование Уолша-Адамара | Только сложение/вычитание, высокая скорость |
| `HuffmanTransform` | Huffman | μ-law компандирование | Логарифмическая компрессия, телефония |
| `RosenbrockTransform` | Rosenbrock | Нелинейное сглаживание | Экспериментальный метод |

## BaseTransform API

### Атрибуты класса

```python
class BaseTransform(ABC):
    # Переопределяются в подклассах
    NAME: str           # Имя метода для логирования
    DESCRIPTION: str    # Краткое описание
    FILE_SUFFIX: str    # Суффикс выходного файла (напр. 'fft', 'dct')
```

### Параметры инициализации

```python
def __init__(
    self,
    block_size: int = 2048,        # Размер блока OLA (степень двойки)
    bitrate: str = "192k",         # Битрейт MP3
    select_mode: str = "none",     # Режим отбора: 'none'|'energy'|'lowpass'
    keep_energy_ratio: float = 1.0,# Доля энергии (режим 'energy')
    sequency_keep_ratio: float = 1.0, # Доля частот (режим 'lowpass')
):
    ...
```

### Абстрактные методы

```python
@abstractmethod
def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
    """Применить преобразование к одному блоку.
    
    Параметры:
        block: Входной блок сигнала (умноженный на окно)
        
    Возвращает:
        Восстановленный блок той же длины
    """
    pass

@abstractmethod
def process(
    self,
    wav_path: str,
    out_dir: str,
    progress_cb: Callable[[float, str], None] = None,
) -> Tuple[str, float]:
    """Полный пайплайн обработки файла.
    
    Параметры:
        wav_path: Путь к исходному аудиофайлу
        out_dir: Директория для сохранения MP3
        progress_cb: Колбэк прогресса (fraction, message)
        
    Возвращает:
        (путь к MP3, время обработки в секундах)
    """
    pass
```

### Вспомогательные методы

```python
def get_output_path(self, wav_path: str, out_dir: str) -> str:
    """Сформировать путь к выходному файлу с суффиксом метода."""

def log_start(self, wav_path: str, **extra_params) -> None:
    """Залогировать начало обработки."""

def log_done(self, out_path: str, time_sec: float) -> None:
    """Залогировать завершение обработки."""
```

## Использование

### Импорт трансформаций

```python
# Импорт конкретных классов
from processing.transforms import FFTTransform, FWHTTransform, DCTTransform

# Импорт базового класса и утилит
from processing.transforms import BaseTransform, create_ola_window, finalize_ola

# Динамический выбор метода
from processing.transforms import TRANSFORM_REGISTRY
TransformClass = TRANSFORM_REGISTRY.get("fwht")
```

### Создание экземпляра

```python
# Базовое использование
fft = FFTTransform()

# С параметрами
fft = FFTTransform(
    block_size=4096,           # Увеличенный блок
    bitrate="256k",            # Высокий битрейт
    select_mode="energy",      # Отбор по энергии
    keep_energy_ratio=0.9,     # Сохранить 90% энергии
)

# FWHT без OLA (поточечная обработка)
fwht = FWHTTransform(select_mode="none")
```

### Обработка файла

```python
# Без прогресс-колбэка
out_path, time_sec = fft.process("audio.wav", "output/")
print(f"Сохранено: {out_path}, время: {time_sec:.2f} сек")

# С прогресс-колбэком
def on_progress(fraction: float, message: str):
    print(f"[{fraction*100:5.1f}%] {message}")

out_path, time_sec = fft.process(
    "audio.wav", 
    "output/",
    progress_cb=on_progress
)
```

### Использование transform_block напрямую

```python
# Создание окна
win = create_ola_window(2048)

# Обработка одного блока
block = audio_signal[:2048] * win
reconstructed = fft.transform_block(block)
```

## Создание новой трансформации

### Шаг 1: Создание файла

Создайте файл `processing/transforms/my_transform.py`:

```python
"""MyTransform: Краткое описание метода.

Теоретические основы:
=====================
Описание математической базы метода...

Параметры:
----------
param1 : type
    Описание параметра 1
    
Примеры использования:
----------------------
>>> transform = MyTransform(param1=value)
>>> out_path, time_sec = transform.process("audio.wav", "output/")
"""
from __future__ import annotations
import time
import numpy as np
from typing import Callable, Optional, Tuple

from .base import (
    BaseTransform,
    load_audio_safe,
    create_ola_window,
    finalize_ola,
    prepare_ola_buffers,
    get_output_path,
)
from ..codecs import encode_pcm_to_mp3


class MyTransform(BaseTransform):
    """Описание новой трансформации."""
    
    # Обязательные атрибуты класса
    NAME = "MyTransform"
    DESCRIPTION = "Мой метод обработки аудио"
    FILE_SUFFIX = "my"
    
    def __init__(
        self,
        block_size: int = 2048,
        bitrate: str = "192k",
        select_mode: str = "none",
        keep_energy_ratio: float = 1.0,
        sequency_keep_ratio: float = 1.0,
        # Добавьте специфичные параметры
        my_param: float = 1.0,
    ):
        """Инициализация трансформации."""
        super().__init__(
            block_size=block_size,
            bitrate=bitrate,
            select_mode=select_mode,
            keep_energy_ratio=keep_energy_ratio,
            sequency_keep_ratio=sequency_keep_ratio,
        )
        self.my_param = my_param
    
    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """Применить преобразование к одному блоку.
        
        Реализуйте здесь:
        1. Прямое преобразование
        2. Отбор коэффициентов (если применимо)
        3. Обратное преобразование
        """
        # Пример: простое сглаживание
        smoothed = block * self.my_param
        return smoothed.astype(np.float32)
    
    def process(
        self,
        wav_path: str,
        out_dir: str,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[str, float]:
        """Полный пайплайн обработки файла."""
        t0 = time.perf_counter()
        self.log_start(wav_path, my_param=self.my_param)
        
        # Загрузка аудио
        if progress_cb:
            progress_cb(0.0, "MyTransform: загрузка")
        x, sr = load_audio_safe(wav_path)
        n = len(x)
        
        # Подготовка OLA (если используется)
        win = create_ola_window(self.block_size)
        frames, hop, total_len, y_accum, w_accum = prepare_ola_buffers(n, self.block_size)
        x_padded = np.pad(x, (0, total_len - n), mode="constant")
        
        # Обработка блоков
        for fi in range(frames):
            i0 = fi * hop
            blk = x_padded[i0 : i0 + self.block_size] * win
            rec = self.transform_block(blk) * win
            y_accum[i0 : i0 + self.block_size] += rec
            w_accum[i0 : i0 + self.block_size] += win * win
            
            if progress_cb:
                progress_cb(
                    0.1 + 0.8 * (fi + 1) / frames,
                    f"MyTransform: блок {fi+1}/{frames}"
                )
        
        # Финализация OLA
        y = finalize_ola(y_accum, w_accum, n)
        
        # Кодирование в MP3
        out_mp3 = self.get_output_path(wav_path, out_dir)
        if progress_cb:
            progress_cb(0.95, "MyTransform: кодирование MP3")
        encode_pcm_to_mp3(y, sr, out_mp3, self.bitrate)
        
        total_dt = time.perf_counter() - t0
        if progress_cb:
            progress_cb(1.0, "MyTransform: готово")
        
        self.log_done(out_mp3, total_dt)
        return out_mp3, total_dt


# Функция-обёртка для обратной совместимости
def my_transform_and_mp3(
    wav_path: str,
    out_dir: str,
    *,
    block_size: int = 2048,
    bitrate: str = "192k",
    my_param: float = 1.0,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> Tuple[str, float]:
    """Функция-обёртка для MyTransform."""
    transform = MyTransform(
        block_size=block_size,
        bitrate=bitrate,
        my_param=my_param,
    )
    return transform.process(wav_path, out_dir, progress_cb)


__all__ = [
    "MyTransform",
    "my_transform_and_mp3",
]
```

### Шаг 2: Регистрация

Добавьте в `processing/transforms/__init__.py`:

```python
from .my_transform import MyTransform, my_transform_and_mp3

TRANSFORM_REGISTRY["my"] = MyTransform

__all__.extend([
    "MyTransform",
    "my_transform_and_mp3",
])
```

### Шаг 3: Экспорт на уровень выше

Добавьте в `processing/__init__.py`:

```python
from .transforms.my_transform import my_transform_and_mp3

__all__.append("my_transform_and_mp3")
```

## Утилиты OLA в base.py

### Константы

```python
SELECT_MODE_NONE = "none"       # Без отбора (идеальная реконструкция)
SELECT_MODE_ENERGY = "energy"   # Отбор по энергии
SELECT_MODE_LOWPASS = "lowpass" # Отбор по частоте
VALID_SELECT_MODES = (SELECT_MODE_NONE, SELECT_MODE_ENERGY, SELECT_MODE_LOWPASS)
```

### Функции загрузки

```python
def load_audio_safe(wav_path: str) -> Tuple[np.ndarray, int]:
    """Безопасная загрузка аудио с fallback на soundfile."""
    ...

def get_output_path(wav_path: str, out_dir: str, suffix: str) -> str:
    """Сформировать путь к выходному MP3 файлу."""
    ...
```

### Функции OLA

```python
def create_ola_window(block_size: int) -> np.ndarray:
    """Создать sqrt-Hann окно для OLA с 50% перекрытием.
    
    h^2[n] + h^2[n+N/2] = 1 для идеальной реконструкции.
    """
    return np.sqrt(np.hanning(block_size) + 1e-12).astype(np.float32)

def prepare_ola_buffers(
    signal_length: int,
    block_size: int
) -> Tuple[int, int, int, np.ndarray, np.ndarray]:
    """Подготовить буферы для OLA обработки.
    
    Возвращает:
        (frames, hop, total_len, y_accum, w_accum)
    """
    ...

def finalize_ola(
    y_accum: np.ndarray,
    w_accum: np.ndarray,
    original_len: int
) -> np.ndarray:
    """Завершить OLA: нормировка окна и обрезка до исходной длины."""
    ...
```

### Функции отбора коэффициентов

```python
def select_coefficients_energy(
    coeffs: np.ndarray,
    keep_ratio: float
) -> np.ndarray:
    """Отбор коэффициентов по энергии.
    
    Сохраняет минимальное число наибольших по модулю коэффициентов,
    которые содержат заданную долю энергии сигнала.
    """
    ...

def select_coefficients_lowpass(
    coeffs: np.ndarray,
    keep_ratio: float
) -> np.ndarray:
    """Отбор коэффициентов по частоте (lowpass).
    
    Сохраняет первые коэффициенты в порядке частоты.
    """
    ...
```

## Диаграмма потока данных

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                  TYPICAL TRANSFORM FLOW                      │
                    └─────────────────────────────────────────────────────────────┘
                    
    Входной файл
    (WAV/MP3/OGG)
         │
         ▼
    ┌─────────────────┐
    │ load_audio_safe │ ──── Декодирование в PCM float32 моно
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ prepare_ola_    │ ──── Вычисление параметров OLA
    │ buffers         │      Создание окон и буферов
    └────────┬────────┘
             │
    ┌────────┴────────────────────────────────────────────┐
    │                    ЦИКЛ OLA                         │
    │  ┌──────────────────────────────────────────────┐   │
    │  │ for each frame:                              │   │
    │  │   1. Извлечь блок × окно                     │   │
    │  │   2. transform_block(block)                  │   │
    │  │   3. Накопить результат × окно               │   │
    │  │   4. Накопить веса (window²)                 │   │
    │  └──────────────────────────────────────────────┘   │
    └────────┬────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │ finalize_ola    │ ──── Нормировка по весам
    └────────┬────────┘      Обрезка до исходной длины
             │               Защита от клиппинга
             ▼
    ┌─────────────────┐
    │ encode_pcm_to_  │ ──── Кодирование в MP3 через FFmpeg
    │ mp3             │
    └────────┬────────┘
             │
             ▼
    Выходной MP3
    {basename}_{suffix}.mp3
```

## Обратная совместимость

Для каждого класса трансформации предусмотрена функция-обёртка:

```python
# Старый API (функции)
from processing import fft_transform_and_mp3, fwht_transform_and_mp3
out, time = fft_transform_and_mp3("audio.wav", "output/", select_mode="energy")

# Новый API (классы) — рекомендуется
from processing.transforms import FFTTransform
fft = FFTTransform(select_mode="energy")
out, time = fft.process("audio.wav", "output/")
```

Оба подхода дают одинаковый результат. Классовый API предпочтителен для:
- Повторного использования с разными параметрами
- Расширения через наследование
- Более явного управления жизненным циклом

## Тестирование

```python
import pytest
from processing.transforms import FFTTransform

def test_fft_transform_basic():
    """Тест базовой функциональности FFT трансформации."""
    fft = FFTTransform(block_size=2048)
    assert fft.NAME == "FFT"
    assert fft.FILE_SUFFIX == "fft"

def test_fft_transform_block():
    """Тест обработки блока."""
    fft = FFTTransform()
    block = np.random.randn(2048).astype(np.float32)
    result = fft.transform_block(block)
    assert result.shape == block.shape
    assert result.dtype == np.float32

def test_fft_ola_reconstruction():
    """Тест реконструкции через OLA."""
    # Создаём тестовый сигнал
    sr = 44100
    t = np.linspace(0, 1, sr, dtype=np.float32)
    x = np.sin(2 * np.pi * 440 * t)  # 440 Гц синусоида
    
    # Обрабатываем через FFT без модификации
    fft = FFTTransform(select_mode="none")
    win = create_ola_window(2048)
    
    # ... тест OLA обработки ...
```

## Зависимости

| Библиотека | Назначение |
|------------|------------|
| `numpy` | Численные операции, FFT |
| `scipy.fft` | Альтернативные реализации FFT |
| `logging` | Диагностические сообщения |
| `abc` | Абстрактные базовые классы |

---

*Документация обновлена для версии 1.1 (рефакторинг transforms).*
