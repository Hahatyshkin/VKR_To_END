# processing

Модуль вычислительной части и кодеков.

## Структура модуля

```
processing/
├── __init__.py          # Публичный API модуля
├── audio_ops.py         # Standard MP3 + переэкспорт трансформаций
├── codecs.py            # Взаимодействие с FFmpeg/pydub/soundfile
├── metrics.py           # Метрики качества аудио
├── utils.py             # Вспомогательные функции
├── api.py               # Устаревший фасад совместимости
└── transforms/          # Реализации трансформаций
    ├── __init__.py      # Экспорт всех трансформаций
    ├── base.py          # Базовый класс и утилиты OLA
    ├── fft.py           # Быстрое преобразование Фурье
    ├── dct.py           # Дискретное косинусное преобразование
    ├── dwt.py           # Дискретное вейвлет-преобразование (Хаар)
    ├── fwht.py          # Быстрое преобразование Уолша-Адамара
    ├── huffman.py       # Huffman-like (μ-law компандирование)
    └── rosenbrock.py    # Rosenbrock-like (нелинейное сглаживание)
```

## Доступные методы обработки

1. **Standard MP3** — прямое кодирование WAV→MP3 через FFmpeg
2. **FFT** — Быстрое преобразование Фурье
3. **DCT** — Дискретное косинусное преобразование
4. **DWT** — Вейвлет Хаара (многоуровневое разложение)
5. **FWHT** — Преобразование Уолша-Адамара
6. **Huffman-like** — μ-law компандирование с квантованием
7. **Rosenbrock-like** — Нелинейное сглаживающее преобразование

## Архитектура transforms/

### Диаграмма наследования

```
                    BaseTransform (abstract)
                           │
           ┌───────┬───────┼───────┬───────┬───────┐
           │       │       │       │       │       │
           ▼       ▼       ▼       ▼       ▼       ▼
         FFT     FWHT    DCT     DWT   Huffman  Rosenbrock
```

### BaseTransform API

Абстрактный базовый класс определяет единый интерфейс для всех методов:

```python
from abc import ABC, abstractmethod

class BaseTransform(ABC):
    # Атрибуты класса (переопределяются в подклассах)
    NAME: str           # Имя метода для логирования
    DESCRIPTION: str    # Краткое описание
    FILE_SUFFIX: str    # Суффикс выходного файла

    # Общие параметры
    block_size: int     # Размер блока OLA (степень двойки)
    bitrate: str        # Битрейт MP3
    select_mode: str    # Режим отбора: 'none', 'energy', 'lowpass'

    @abstractmethod
    def transform_block(self, block: np.ndarray, **params) -> np.ndarray:
        """Применить преобразование к одному блоку."""
        pass

    @abstractmethod
    def process(self, wav_path: str, out_dir: str,
                progress_cb: Callable[[float, str], None] = None
                ) -> Tuple[str, float]:
        """Полный пайплайн обработки файла."""
        pass
```

### Утилиты OLA в base.py

```python
from processing.transforms.base import (
    # Константы
    SELECT_MODE_NONE,      # "none" — без отбора
    SELECT_MODE_ENERGY,    # "energy" — по энергии
    SELECT_MODE_LOWPASS,   # "lowpass" — по частоте

    # Функции OLA
    load_audio_safe,       # Безопасная загрузка аудио
    create_ola_window,     # sqrt-Hann окно
    prepare_ola_buffers,   # Подготовка буферов
    finalize_ola,          # Нормировка и обрезка

    # Отбор коэффициентов
    select_coefficients_energy,   # По энергии
    select_coefficients_lowpass,  # По частоте
)
```

## Использование

### Через функции-обёртки

```python
from processing import (
    standard_convert_to_mp3,
    fft_transform_and_mp3,
    fwht_transform_and_mp3,
)

# Стандартное MP3
out_path, time_sec = standard_convert_to_mp3("audio.wav", "output/")

# FFT с отбором по энергии
out_path, time_sec = fft_transform_and_mp3(
    "audio.wav", "output/",
    select_mode="energy",
    keep_energy_ratio=0.8
)
```

### Через классы трансформаций

```python
from processing.transforms import FFTTransform, FWHTTransform

# Создание экземпляра
fft = FFTTransform(
    block_size=2048,
    select_mode="energy",
    keep_energy_ratio=0.8
)

# Обработка
out_path, time_sec = fft.process("audio.wav", "output/")
```

### С прогресс-колбэком

```python
def on_progress(fraction: float, message: str):
    print(f"[{fraction*100:.0f}%] {message}")

fft = FFTTransform(select_mode="energy")
out_path, time_sec = fft.process(
    "audio.wav", "output/",
    progress_cb=on_progress
)
```

### Динамический выбор метода

```python
from processing import get_transform

# Получить класс по имени
TransformClass = get_transform("fwht")
transform = TransformClass(block_size=2048)
out_path, time_sec = transform.process("audio.wav", "output/")
```

## Режимы отбора коэффициентов

| Режим | Описание | Параметр |
|-------|----------|----------|
| `'none'` | Без отбора (идеальная реконструкция) | — |
| `'energy'` | Сохранение доли энергии | `keep_energy_ratio` (0.0-1.0) |
| `'lowpass'` | Сохранение низких частот | `sequency_keep_ratio` (0.0-1.0) |

## Метрики качества

```python
from processing import compute_metrics_batch

results = compute_metrics_batch("original.wav", [
    ("MP3", "output.mp3", 1.5),
    ("FWHT", "output_fwht.mp3", 2.3),
])

for r in results:
    print(f"{r['variant']}: SNR={r['snr_db']:.1f}dB, LSD={r['lsd_db']:.2f}dB")
```

## Зависимости

- `numpy` — численные операции
- `soundfile` — чтение WAV файлов
- `pydub` / `ffmpeg` — кодирование в MP3
- стандартные библиотеки Python

## История изменений

### Версия 1.1 (рефакторинг)
- Создан подмодуль `transforms/` с единообразной структурой
- Каждый метод вынесен в отдельный файл с подробной документацией
- Добавлен базовый класс `BaseTransform` для консистентного API
- Добавлены утилиты `get_transform()` и `get_transform_function()`
- Полностью сохранена обратная совместимость через переэкспорт
