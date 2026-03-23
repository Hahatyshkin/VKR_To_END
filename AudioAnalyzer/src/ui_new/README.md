# ui_new

Модуль пользовательского интерфейса (PySide6).

## Архитектура

Модуль реализует современную архитектуру с применением следующих паттернов:

- **Event Bus** — слабосвязанная коммуникация между компонентами
- **Repository Pattern** — абстракция доступа к данным
- **Pipeline Pattern** — обработка аудио в виде цепочки шагов
- **Protocol Interfaces** — структурная типизация
- **DI Container** — внедрение зависимостей
- **Mixin Architecture** — разделение функциональности MainWindow

## Структура модуля

```
ui_new/
├── __init__.py          # Публичный API модуля
├── main_window.py       # Главное окно (~1000 строк)
├── worker.py            # Фоновый обработчик (~500 строк)
├── constants.py         # Константы UI (~125 строк)
├── presets.py           # Пресеты настроек (~320 строк)
├── log_handler.py       # Обработчик логов (~90 строк)
├── export_xlsx.py       # Экспорт в Excel (~240 строк)
│
├── events.py            # 🆕 Event Bus (Фаза 2.1)
├── repositories.py      # 🆕 Repository Pattern (Фаза 2.2)
├── pipeline.py          # 🆕 Pipeline Pattern (Фаза 2.3)
├── protocols.py         # 🆕 Protocol Interfaces (Фаза 2.4)
│
├── services/            # 🆕 DI контейнер и сервисы
│   ├── __init__.py
│   ├── container.py     # Service Container (lazy init)
│   ├── config.py        # AppConfig + progress ranges
│   ├── audio_service.py # Сервис координации обработки
│   ├── spectrum_service.py # Сервис спектрального анализа
│   └── file_service.py  # Сервис работы с файлами
│
├── components/          # 🆕 UI компоненты (Фаза 3)
│   ├── __init__.py
│   ├── dashboard.py     # Dashboard с KPI карточками
│   ├── shortcuts.py     # ShortcutManager (горячие клавиши)
│   ├── toast.py         # Toast уведомления
│   ├── onboarding.py    # Onboarding для новых пользователей
│   └── wizards.py       # CompareWizard, BatchProcessWizard
│
├── widgets/             # 🆕 Виджеты (Фаза 4)
│   ├── __init__.py
│   ├── results_table.py # Таблица с контекстным меню
│   ├── spectrogram_3d.py # 3D спектрограмма (Plotly)
│   ├── spectrum_widget.py # Интерактивный график спектра
│   └── spectrum_worker.py # Фоновый расчёт спектра
│
├── ml_integration.py    # 🆕 ML интеграция (Фаза 4.4)
├── reports.py           # 🆕 Генерация отчётов (Фаза 4.3)
├── audio_editor.py      # 🆕 Простой аудиоредактор
├── themes.py            # 🆕 Темы оформления (light/dark)
├── profiles_new.py      # 🆕 Профили настроек
└── cli.py               # 🆕 CLI интерфейс
│
└── mixins/              # Миксины MainWindow (~2000 строк)
    ├── __init__.py
    ├── settings_mixin.py    # Настройки и матрица влияния
    ├── comparison_mixin.py  # Графики сравнения
    ├── player_mixin.py      # Аудиоплеер + Event Bus
    ├── files_mixin.py       # Работа с файлами + Event Bus
    ├── spectrum_mixin.py    # Спектральный анализ
    └── worker_mixin.py      # Управление Worker + Event Bus
```

## Архитектура MainWindow

MainWindow использует **миксины** для разделения функциональности:

```python
class MainWindow(
    SettingsMixin,      # Панель настроек, матрица влияния
    ComparisonMixin,    # Графики сравнения, heatmap
    PlayerMixin,        # Аудиоплеер
    FilesMixin,         # Исходные/обработанные файлы
    SpectrumMixin,      # Спектральный анализ
    WorkerMixin,        # Управление Worker
    QMainWindow         # Базовый класс Qt
):
    pass
```

### Преимущества архитектуры:

1. **Разделение ответственности**: каждый миксин отвечает за свою область
2. **Читаемость**: ~500 строк вместо ~2400 в одном файле
3. **Тестируемость**: можно тестировать миксины отдельно
4. **Расширяемость**: легко добавить новый функционал

## Использование

```python
from ui_new import MainWindow

# Создание окна
window = MainWindow()
window.show()
```

## Миксины

### SettingsMixin

- Построение панели настроек
- Матрица влияния параметров на метрики
- Расчёт impact score

### ComparisonMixin

- График сравнения методов (Bar Chart)
- Тепловая карта (Heatmap)
- Таблица подсказок по метрикам

### PlayerMixin

- Аудиоплеер (QMediaPlayer)
- Управление воспроизведением
- Громкость и позиция

### FilesMixin

- Список исходных файлов
- Список обработанных файлов
- Очистка папки output

### SpectrumMixin

- Спектральный анализ
- Сравнение спектров методов
- График спектра

### WorkerMixin

- Запуск фоновой обработки
- Обработка результатов
- Прогресс

## Ключевые архитектурные улучшения

### Event Bus (events.py)

Центральный диспетчер событий для слабосвязанной коммуникации:

```python
from ui_new.events import EventBus, EventType, emit_file_loaded

# Подписка на события
EventBus.subscribe(EventType.FILE_LOADED, self.on_file_loaded)

# Публикация событий
emit_file_loaded(path="/path/to/file.wav", file_size=1024000)
```

### Repository Pattern (repositories.py)

Абстракция доступа к данным с поддержкой JSON-хранилищ:

```python
from ui_new.repositories import RepositoryFactory

# Получение репозиториев
profile_repo = RepositoryFactory.get_profile_repository()
settings_repo = RepositoryFactory.get_settings_repository()
history_repo = RepositoryFactory.get_history_repository()
```

### Pipeline Pattern (pipeline.py)

Цепочка обработки аудио с прогрессом:

```python
from ui_new.pipeline import AudioPipeline, LoadStep, TransformStep, MetricsStep

pipeline = AudioPipeline("analysis")
pipeline.add_step(LoadStep())
pipeline.add_step(TransformStep(method="fwht"))
pipeline.add_step(MetricsStep())

result = pipeline.execute_sync(context)
```

### DI Container (services/container.py)

Внедрение зависимостей с ленивой инициализацией:

```python
from ui_new.services import init_container, get_container

container = init_container()
audio_service = container.audio_processing
spectrum_service = container.spectrum
```

## История изменений

### Версия 2.0 (4 фазы улучшений)

**Фаза 1: Качество кода и тестирование**
- 278+ unit тестов (pytest)
- Фикстуры для временных файлов
- Проверка типизации (mypy)
- Автоматическое логирование

**Фаза 2: Архитектурные улучшения**
- Event Bus для слабосвязанной коммуникации
- Repository Pattern для доступа к данным
- Pipeline Pattern для обработки аудио
- Protocol Interfaces для типизации

**Фаза 3: UI/UX улучшения**
- Dashboard с KPI карточками
- Система горячих клавиш (ShortcutManager)
- Toast-уведомления
- Onboarding для новых пользователей
- Мастеры (CompareWizard, BatchProcessWizard)

**Фаза 4: Новый функционал**
- 3D спектрограмма (Plotly)
- История и сессии
- Генерация отчётов
- ML интеграция для рекомендаций

### Версия 1.2 (рефакторинг UI)
- Создан модуль mixins/ для разделения функциональности
- MainWindow сокращён с ~2400 до ~500 строк
- Каждый миксин в отдельном файле с документацией
- Полностью сохранена функциональность
