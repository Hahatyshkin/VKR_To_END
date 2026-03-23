# UI Components (Фаза 3)

Модуль содержит компоненты улучшения UI/UX для AudioAnalyzer.

## Структура

```
components/
├── __init__.py           # Экспорты всех компонентов
├── dashboard.py          # Dashboard - панель мониторинга
├── shortcuts.py          # ShortcutManager - горячие клавиши
├── toast.py              # ToastManager - всплывающие уведомления
├── wizards.py            # Wizards - мастера для сложных операций
└── onboarding.py         # OnboardingManager - онбординг для новых пользователей
```

## Компоненты

### Dashboard (dashboard.py)

Главная панель мониторинга с ключевыми метриками.

**Классы:**
- `DashboardWidget` - главный виджет Dashboard
- `KPICard` - карточка с ключевым показателем
- `QuickActionButton` - кнопка быстрого действия
- `RecentActivityItem` - элемент истории последних операций
- `MiniSpectrogram` - миниатюра спектрограммы

**Использование:**
```python
from ui_new.components import DashboardWidget

dashboard = DashboardWidget()
dashboard.update_results(results)
dashboard.update_processing_time(45.5)

# Сигналы
dashboard.open_file_requested.connect(...)
dashboard.batch_process_requested.connect(...)
dashboard.compare_requested.connect(...)
```

### ShortcutManager (shortcuts.py)

Централизованное управление горячими клавишами.

**Классы:**
- `ShortcutManager` - менеджер горячих клавиш
- `ShortcutAction` - действие с горячей клавишей
- `ShortcutCategory` - категория действий

**Стандартные комбинации:**
| Действие | Комбинация |
|----------|------------|
| Открыть файл | Ctrl+O |
| Сохранить результаты | Ctrl+S |
| Экспорт в Excel | Ctrl+E |
| Пакетная обработка | Ctrl+B |
| Запустить анализ | F5 |
| Dashboard | Ctrl+D |
| Таблица | Ctrl+T |
| Сравнение | Ctrl+G |
| Настройки | Ctrl+, |
| Логи | Ctrl+L |
| Справка | F1 |

**Использование:**
```python
from ui_new.components import ShortcutManager

manager = ShortcutManager(parent)
manager.register(parent, "file.open", callback)
manager.set_key("file.open", "Ctrl+Shift+O")
```

### ToastManager (toast.py)

Всплывающие уведомления с анимацией.

**Классы:**
- `ToastManager` - менеджер уведомлений
- `ToastWidget` - виджет уведомления
- `ToastType` - типы (INFO, SUCCESS, WARNING, ERROR)
- `ToastPosition` - позиция на экране

**Использование:**
```python
from ui_new.components import ToastManager, ToastType

manager = ToastManager(parent)
manager.show_info("Информация")
manager.show_success("Успешно!")
manager.show_warning("Предупреждение")
manager.show_error("Ошибка")
```

### Wizards (wizards.py)

Мастера для пошаговых операций.

**Классы:**
- `WizardDialog` - базовый класс мастера
- `CompareWizard` - мастер сравнения файлов
- `BatchProcessWizard` - мастер пакетной обработки

**Использование:**
```python
from ui_new.components import CompareWizard

wizard = CompareWizard(parent)
wizard.files_selected.connect(on_files_selected)
if wizard.exec() == QDialog.Accepted:
    # Получить данные
    data = wizard._data
```

### OnboardingManager (onboarding.py)

Система онбординга для новых пользователей.

**Классы:**
- `OnboardingManager` - менеджер онбординга
- `OnboardingStep` - шаг онбординга
- `OnboardingOverlay` - оверлей с подсказками

**Использование:**
```python
from ui_new.components import OnboardingManager

manager = OnboardingManager(main_window, config_path)
if not manager.is_completed():
    manager.start()
```

## Интеграция в MainWindow

Все компоненты автоматически интегрируются при инициализации MainWindow:

```python
class MainWindow(...):
    def __init__(self):
        # Инициализация компонентов Фазы 3
        self._init_phase3_components()
        self._build_ui()

    def _init_phase3_components(self):
        self._shortcut_manager = ShortcutManager(self)
        self._setup_shortcuts()
        self._toast_manager = None
        self._onboarding_manager = OnboardingManager(self, config_path)
```

## Тестирование

Тесты находятся в `tests/test_phase3_components.py`:
- TestDashboardWidget - тесты Dashboard
- TestShortcutManager - тесты горячих клавиш
- TestToastWidget/Manager - тесты уведомлений
- TestWizards - тесты мастеров
- TestOnboardingManager - тесты онбординга

**Примечание:** Тесты требуют PySide6 для выполнения.
