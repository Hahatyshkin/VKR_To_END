# Архитектура AudioAnalyzer v2.0

## Обзор

AudioAnalyzer — настольное приложение для сравнительного анализа методов аудио-обработки. Версия 2.0 включает масштабные архитектурные улучшения, разделённые на 4 фазы.

---

## Архитектурные паттерны

### 1. Event Bus (Шина событий)

**Файл:** `src/ui_new/events.py`

Центральный диспетчер событий для слабосвязанной коммуникации между компонентами.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          EVENT BUS                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    EventSignaler (QObject)                   │    │
│  │                       event_signal                           │    │
│  └──────────────────────────────┬──────────────────────────────┘    │
│                                 │                                    │
│  ┌──────────────────────────────▼──────────────────────────────┐    │
│  │                     _dispatch_event()                        │    │
│  │                 (thread-safe via Qt signals)                 │    │
│  └──────────────────────────────┬──────────────────────────────┘    │
│                                 │                                    │
│  ┌──────────┬──────────┬────────┴────────┬──────────┬──────────┐   │
│  ▼          ▼          ▼                 ▼          ▼          ▼   │
│ Sub#1     Sub#2     Sub#3            Sub#4     Sub#5     Sub#N    │
└─────────────────────────────────────────────────────────────────────┘
```

**Типы событий:**
- `FILE_LOADED`, `FILE_PROCESSED`, `FILE_DELETED`
- `PROCESSING_STARTED`, `PROCESSING_FINISHED`, `PROCESSING_ERROR`
- `PROFILE_CHANGED`, `SETTINGS_CHANGED`
- `RESULTS_UPDATED`, `PLAYER_STATE_CHANGED`

**Использование:**
```python
from ui_new.events import EventBus, EventType, emit_file_loaded

# Подписка
EventBus.subscribe(EventType.FILE_LOADED, self.on_file_loaded)

# Публикация
emit_file_loaded(path="/path/to/file.wav", file_size=1024000)
```

---

### 2. Repository Pattern (Репозиторий)

**Файл:** `src/ui_new/repositories.py`

Абстракция доступа к данным с поддержкой JSON-хранилищ.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BaseRepository[T, ID]                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ + get(id: ID) -> Optional[T]                                 │    │
│  │ + get_all() -> Dict[ID, T]                                   │    │
│  │ + save(id: ID, entity: T) -> None                            │    │
│  │ + delete(id: ID) -> bool                                     │    │
│  │ + exists(id: ID) -> bool                                     │    │
│  └──────────────────────────────┬──────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
           ▼                       ▼                       ▼
┌─────────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│   JsonRepository    │  │ ProfileRepo     │  │  SettingsRepo       │
│   (base JSON)       │  │ (built-ins)     │  │  (key-value)        │
└─────────────────────┘  └─────────────────┘  └─────────────────────┘
           │
           ├─────────────────────┐
           ▼                     ▼
┌─────────────────────┐  ┌─────────────────────┐
│   HistoryRepo       │  │   SessionRepo       │
│   (operations)      │  │   (state)           │
└─────────────────────┘  └─────────────────────┘
```

**Использование:**
```python
from ui_new.repositories import RepositoryFactory

profile_repo = RepositoryFactory.get_profile_repository()
settings_repo = RepositoryFactory.get_settings_repository()
history_repo = RepositoryFactory.get_history_repository()
```

---

### 3. Pipeline Pattern (Пайплайн)

**Файл:** `src/ui_new/pipeline.py`

Цепочка обработки аудио с прогрессом и отменой.

```
┌─────────────────────────────────────────────────────────────────────┐
│                       AudioPipeline                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ steps: List[PipelineStep]                                    │    │
│  │ _cancelled: bool                                             │    │
│  │ + add_step(step) -> AudioPipeline                            │    │
│  │ + execute_sync(context) -> PipelineContext                   │    │
│  │ + cancel() -> None                                           │    │
│  └──────────────────────────────┬──────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ execute_sync()
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PipelineContext                                 │
│  source_path, output_dir, audio_data, sample_rate, settings,       │
│  progress, status, metrics, error_message                          │
└─────────────────────────────────────────────────────────────────────┘
                                   │
         ┌─────────────┬───────────┼───────────┬─────────────┐
         ▼             ▼           ▼           ▼             ▼
┌─────────────┐ ┌───────────┐ ┌─────────┐ ┌──────────┐ ┌───────────┐
│  LoadStep   │ │Transform  │ │Metrics  │ │ Encode   │ │  Custom   │
│  (10%)      │ │Step (50%) │ │Step(30%)│ │ Step(10%)│ │  Steps    │
└─────────────┘ └───────────┘ └─────────┘ └──────────┘ └───────────┘
```

**Использование:**
```python
from ui_new.pipeline import AudioPipeline, LoadStep, TransformStep, MetricsStep

pipeline = AudioPipeline("analysis")
pipeline.add_step(LoadStep())
pipeline.add_step(TransformStep(method="fwht"))
pipeline.add_step(MetricsStep())

result = pipeline.execute_sync(context)
```

---

### 4. DI Container (Внедрение зависимостей)

**Файл:** `src/ui_new/services/container.py`

Ленивая инициализация сервисов с глобальным доступом.

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ServiceContainer                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ _config: AppConfig                                           │    │
│  │ _services: Dict[str, Any]                                    │    │
│  │                                                              │    │
│  │ @property audio_processing -> AudioProcessingService         │    │
│  │ @property spectrum -> SpectrumService                        │    │
│  │ @property file -> FileService                                │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘

Глобальные функции:
- init_container(config) -> ServiceContainer
- get_container() -> ServiceContainer
- reset_container() -> None
```

---

## Структура MainWindow

MainWindow использует миксины для разделения ответственности:

```python
class MainWindow(
    SettingsMixin,      # Панель настроек, матрица влияния
    ComparisonMixin,    # Графики сравнения, heatmap
    PlayerMixin,        # Аудиоплеер + Event Bus
    FilesMixin,         # Работа с файлами + Event Bus
    SpectrumMixin,      # Спектральный анализ
    WorkerMixin,        # Управление Worker + Event Bus
    QMainWindow
):
    pass
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MainWindow                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     Dashboard (Phase 3)                      │    │
│  │  [Files Card] [SNR Card] [Methods Card] [Time Card]         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                        QTabWidget                            │    │
│  │  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │    │
│  │  │ Таблица  │ Сравнение│ Настройки│  Плеер   │  Спектр  │  │    │
│  │  └──────────┴──────────┴──────────┴──────────┴──────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Log Panel (QPlainTextEdit)               │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## UI Компоненты (Фаза 3)

### Dashboard
- KPI карточки с метриками
- Quick Actions — кнопки быстрого доступа
- Recent Activity — история операций

### ShortcutManager
- 16 горячих клавиш
- Категории: Файл, Анализ, Вид, Справка
- Настраиваемые комбинации

### Toast Notifications
- 4 типа: INFO, SUCCESS, WARNING, ERROR
- Анимации и автоскрытие

### OnboardingManager
- Тур для новых пользователей
- Сохранение прогресса

---

## Виджеты (Фаза 4)

### ResultsTable
- Контекстное меню (анализ файла)
- Сортировка и фильтрация
- Экспорт в Excel

### Spectrogram3D
- Интерактивный 3D график (Plotly)
- Ось X — время, Y — частота, Z — амплитуда

### SpectrumWidget
- Интерактивный график спектра
- Сравнение нескольких методов

---

## ML Интеграция

**Файл:** `src/ui_new/ml_integration.py`

```python
class MLMethodRecommender:
    """Рекомендации методов на основе характеристик аудио."""
    
    def recommend(self, features: Dict) -> List[MethodRecommendation]:
        # Анализ характеристик:
        # - duration_sec
        # - dynamic_range_db
        # - spectral_centroid_hz
        # - is_speech
        pass
```

---

## Тестирование

### Структура тестов

```
tests/
├── conftest.py              # Фикстуры
├── test_events_core.py      # Event Bus (20 тестов)
├── test_repositories.py     # Repository Pattern (38 тестов)
├── test_pipeline.py         # Pipeline Pattern (27 тестов)
├── test_protocols.py        # Protocol Interfaces (23 тестов)
├── test_metrics.py          # Метрики качества (19 тестов)
├── test_processing.py       # Обработка аудио
├── test_transforms.py       # Трансформации
├── test_codecs.py           # Кодеки
├── test_architecture.py     # Архитектура
├── test_phase3_components.py # UI компоненты
├── test_new_features.py     # Новый функционал
└── test_integration.py      # Интеграция
```

### Запуск тестов

```bash
pytest tests/ -v --cov=src --cov-report=html
```

---

## Диаграммы

Все диаграммы в формате draw.io в `docs/diagrams/`:

| Диаграмма | Описание |
|-----------|----------|
| `architecture_diagram.drawio` | Общая архитектура |
| `ui_mixin_diagram.drawio` | Структура миксинов |
| `audio_pipeline.drawio` | Пайплайн обработки |
| `sequence_diagram.drawio` | Взаимодействие компонентов |
| `method_*.drawio` | Диаграммы методов |

---

## Метрики качества

### Временная область
- **SNR (дБ)** — Signal-to-Noise Ratio (↑ лучше)
- **RMSE** — Root Mean Square Error (↓ лучше)
- **SI-SDR (дБ)** — Scale-Invariant SDR (↑ лучше)

### Спектральная область
- **LSD (дБ)** — Log-Spectral Distance (↓ лучше)
- **Spectral Convergence** — ошибка амплитуд (↓ лучше)
- **Centroid Δ (Гц)** — разница центроидов (↓ лучше)
- **Cosine Similarity** — схожесть спектров (↑ лучше)

---

## Версионирование

- v2.0.0 — 4 фазы улучшений (текущая)
- v1.1.0 — Рефакторинг transforms
- v1.0.0 — Базовый функционал
