"""
Тесты для компонентов Фазы 3: UI/UX улучшения.

Содержит тесты для:
- DashboardWidget
- ShortcutManager
- ToastManager
- Wizards
- OnboardingManager
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Пропускаем тесты если PySide6 недоступен
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow

from src.ui_new.components.dashboard import (
    DashboardWidget,
    KPICard,
    QuickActionButton,
    RecentActivityItem,
    MiniSpectrogram,
)
from src.ui_new.components.shortcuts import (
    ShortcutManager,
    ShortcutAction,
    ShortcutCategory,
    get_shortcut_manager,
)
from src.ui_new.components.toast import (
    ToastType,
    ToastPosition,
    ToastWidget,
    ToastManager,
)
from src.ui_new.components.wizards import (
    WizardPage,
    WizardDialog,
    CompareWizard,
    BatchProcessWizard,
)
from src.ui_new.components.onboarding import (
    OnboardingStep,
    OnboardingStepType,
    OnboardingManager,
    DEFAULT_ONBOARDING_STEPS,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def main_window(qtbot):
    """Создать главное окно для тестов."""
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


# =============================================================================
# ТЕСТЫ DASHBOARD
# =============================================================================

class TestDashboardWidget:
    """Тесты для DashboardWidget."""

    def test_dashboard_creation(self, qtbot, main_window):
        """Тест создания Dashboard."""
        dashboard = DashboardWidget()
        qtbot.addWidget(dashboard)

        assert dashboard is not None
        # Проверяем наличие KPI карточек
        assert hasattr(dashboard, 'files_card')
        assert hasattr(dashboard, 'snr_card')
        assert hasattr(dashboard, 'methods_card')
        assert hasattr(dashboard, 'time_card')

    def test_kpi_card_creation(self, qtbot):
        """Тест создания KPI карточки."""
        card = KPICard(
            title="Тестовая метрика",
            value="42",
            subtitle="единиц",
            icon="📊",
            color="#3B82F6"
        )
        qtbot.addWidget(card)

        assert card._title == "Тестовая метрика"
        assert card._value == "42"

    def test_kpi_card_update(self, qtbot):
        """Тест обновления значения KPI карточки."""
        card = KPICard(title="Test", value="0")
        qtbot.addWidget(card)

        card.set_value("100", "новое значение")

        assert card._value == "100"

    def test_kpi_card_click(self, qtbot):
        """Тест клика по KPI карточке."""
        card = KPICard(title="Test", value="0")
        qtbot.addWidget(card)

        clicked = Mock()
        card.clicked.connect(clicked)

        qtbot.mouseClick(card, Qt.LeftButton)
        clicked.assert_called_once()

    def test_dashboard_update_results(self, qtbot):
        """Тест обновления результатов на Dashboard."""
        dashboard = DashboardWidget()
        qtbot.addWidget(dashboard)

        # Создаём мок результаты (используем правильные поля ResultRow)
        results = []
        for i in range(5):
            result = Mock()
            result.source = f"test_{i}.wav"
            result.genre = "test_genre" if i % 2 == 0 else None
            result.variant = "FWHT" if i % 2 == 0 else "FFT"
            result.snr_db = 30.0 + i
            result.time_sec = 1.5 + i * 0.1
            results.append(result)

        dashboard.update_results(results)

        # Проверяем обновление карточки файлов
        assert dashboard.files_card._value == "5"

    def test_dashboard_update_processing_time(self, qtbot):
        """Тест обновления времени обработки."""
        dashboard = DashboardWidget()
        qtbot.addWidget(dashboard)

        dashboard.update_processing_time(45.5)
        assert "45.5" in dashboard.time_card._value

        dashboard.update_processing_time(125.0)
        assert "2m" in dashboard.time_card._value


class TestQuickActionButton:
    """Тесты для QuickActionButton."""

    def test_button_creation(self, qtbot):
        """Тест создания кнопки быстрого действия."""
        btn = QuickActionButton(
            text="Тест",
            icon="▶️",
            description="Тестовое действие"
        )
        qtbot.addWidget(btn)

        assert "Тест" in btn.text()
        assert btn.toolTip() == "Тестовое действие"


class TestMiniSpectrogram:
    """Тесты для MiniSpectrogram."""

    def test_mini_spectrogram_creation(self, qtbot):
        """Тест создания мини-спектрограммы."""
        mini = MiniSpectrogram("test.wav")
        qtbot.addWidget(mini)

        assert mini._filename == "test.wav"

    def test_mini_spectrogram_click(self, qtbot):
        """Тест клика по мини-спектрограмме."""
        mini = MiniSpectrogram("test.wav")
        qtbot.addWidget(mini)

        clicked = Mock()
        mini.clicked.connect(clicked)

        qtbot.mouseClick(mini, Qt.LeftButton)
        clicked.assert_called_with("test.wav")


# =============================================================================
# ТЕСТЫ SHORTCUT MANAGER
# =============================================================================

class TestShortcutManager:
    """Тесты для ShortcutManager."""

    def test_manager_creation(self):
        """Тест создания менеджера горячих клавиш."""
        manager = ShortcutManager()
        assert manager is not None
        assert len(manager.get_all_actions()) > 0

    def test_default_actions(self):
        """Тест наличия стандартных действий."""
        manager = ShortcutManager()
        actions = manager.get_all_actions()

        # Проверяем наличие основных действий
        action_ids = [a.id for a in actions]
        assert "file.open" in action_ids
        assert "file.save" in action_ids
        assert "analysis.run" in action_ids
        assert "help.about" in action_ids

    def test_get_action(self):
        """Тест получения действия по ID."""
        manager = ShortcutManager()

        action = manager.get_action("file.open")
        assert action is not None
        assert action.name == "Открыть файл"

    def test_get_actions_by_category(self):
        """Тест получения действий по категории."""
        manager = ShortcutManager()

        file_actions = manager.get_actions_by_category(ShortcutCategory.FILE)
        assert len(file_actions) > 0

        for action in file_actions:
            assert action.category == ShortcutCategory.FILE

    def test_set_key(self):
        """Тест установки новой комбинации клавиш."""
        manager = ShortcutManager()

        # Устанавливаем новую комбинацию
        result = manager.set_key("file.open", "Ctrl+Shift+O")
        assert result is True

        action = manager.get_action("file.open")
        assert action.current_key == "Ctrl+Shift+O"

    def test_set_conflicting_key(self):
        """Тест установки конфликтующей комбинации."""
        manager = ShortcutManager()

        # Получаем текущую комбинацию другого действия
        other_key = manager.get_action("file.save").current_key

        # Пытаемся установить её для file.open
        result = manager.set_key("file.open", other_key)
        assert result is False

    def test_reset_all(self):
        """Тест сброса всех горячих клавиш."""
        manager = ShortcutManager()

        # Изменяем комбинацию
        manager.set_key("file.open", "Ctrl+Shift+O")

        # Сбрасываем
        manager.reset_all()

        action = manager.get_action("file.open")
        assert action.current_key == action.default_key

    def test_register(self, main_window):
        """Тест регистрации обработчика."""
        manager = ShortcutManager()

        callback = Mock()
        shortcut = manager.register(main_window, "file.open", callback)

        assert shortcut is not None

    def test_singleton(self):
        """Тест глобального экземпляра."""
        manager1 = get_shortcut_manager()
        manager2 = get_shortcut_manager()

        assert manager1 is manager2


class TestShortcutAction:
    """Тесты для ShortcutAction."""

    def test_action_creation(self):
        """Тест создания действия."""
        action = ShortcutAction(
            id="test.action",
            name="Тестовое действие",
            default_key="Ctrl+T",
            description="Описание",
            category=ShortcutCategory.EDIT
        )

        assert action.id == "test.action"
        assert action.current_key == "Ctrl+T"

    def test_action_reset(self):
        """Тест сброса действия к значению по умолчанию."""
        action = ShortcutAction(
            id="test",
            name="Test",
            default_key="Ctrl+T"
        )
        action.current_key = "Ctrl+Shift+T"

        action.reset_to_default()

        assert action.current_key == "Ctrl+T"


# =============================================================================
# ТЕСТЫ TOAST
# =============================================================================

class TestToastWidget:
    """Тесты для ToastWidget."""

    def test_toast_creation(self, qtbot, main_window):
        """Тест создания toast-уведомления."""
        toast = ToastWidget(
            message="Тестовое сообщение",
            toast_type=ToastType.INFO,
            duration=1000,
            parent=main_window
        )
        qtbot.addWidget(toast)

        assert toast._message == "Тестовое сообщение"
        assert toast._toast_type == ToastType.INFO

    def test_toast_show_hide(self, qtbot, main_window):
        """Тест показа и скрытия toast."""
        toast = ToastWidget(
            message="Test",
            toast_type=ToastType.SUCCESS,
            duration=500,
            parent=main_window
        )
        qtbot.addWidget(toast)

        toast.show_toast()
        assert toast.isVisible()

        # Ждём автоматического скрытия
        qtbot.wait(800)
        assert not toast.isVisible()

    def test_toast_types(self, qtbot, main_window):
        """Тест разных типов toast."""
        for toast_type in [ToastType.INFO, ToastType.SUCCESS, ToastType.WARNING, ToastType.ERROR]:
            toast = ToastWidget(
                message=f"Test {toast_type.value}",
                toast_type=toast_type,
                duration=0,  # Без автоскрытия
                parent=main_window
            )
            qtbot.addWidget(toast)
            toast.show_toast()
            assert toast.isVisible()


class TestToastManager:
    """Тесты для ToastManager."""

    def test_manager_creation(self, main_window):
        """Тест создания менеджера."""
        manager = ToastManager(main_window)
        assert manager is not None

    def test_show_info(self, main_window):
        """Тест показа информационного уведомления."""
        manager = ToastManager(main_window)
        manager.show_info("Информационное сообщение")

        assert len(manager._active_toasts) == 1

    def test_show_success(self, main_window):
        """Тест показа уведомления об успехе."""
        manager = ToastManager(main_window)
        manager.show_success("Операция успешна")

        assert len(manager._active_toasts) == 1

    def test_show_error(self, main_window):
        """Тест показа уведомления об ошибке."""
        manager = ToastManager(main_window)
        manager.show_error("Произошла ошибка")

        assert len(manager._active_toasts) == 1

    def test_queue(self, main_window):
        """Тест очереди уведомлений."""
        manager = ToastManager(main_window, max_visible=1)

        # Добавляем несколько уведомлений
        manager.show_info("Первое")
        manager.show_info("Второе")
        manager.show_info("Третье")

        # Одно активно, два в очереди
        assert len(manager._active_toasts) == 1
        assert len(manager._queue) == 2

    def test_clear_all(self, main_window):
        """Тест очистки всех уведомлений."""
        manager = ToastManager(main_window)
        manager.show_info("Test 1")
        manager.show_info("Test 2")

        manager.clear_all()

        assert len(manager._queue) == 0


# =============================================================================
# ТЕСТЫ WIZARDS
# =============================================================================

class TestCompareWizard:
    """Тесты для CompareWizard."""

    def test_wizard_creation(self, qtbot, main_window):
        """Тест создания мастера сравнения."""
        wizard = CompareWizard(main_window)
        qtbot.addWidget(wizard)

        assert wizard is not None
        assert len(wizard._pages) == 4

    def test_wizard_navigation(self, qtbot, main_window):
        """Тест навигации по мастеру."""
        wizard = CompareWizard(main_window)
        qtbot.addWidget(wizard)

        # Начинаем с первой страницы
        assert wizard._current_index == 0

        # Кнопка "Назад" отключена
        assert not wizard.btn_back.isEnabled()

        # Кнопка "Далее" включена
        assert wizard.btn_next.isEnabled()


class TestBatchProcessWizard:
    """Тесты для BatchProcessWizard."""

    def test_wizard_creation(self, qtbot, main_window):
        """Тест создания мастера пакетной обработки."""
        wizard = BatchProcessWizard(main_window)
        qtbot.addWidget(wizard)

        assert wizard is not None
        assert len(wizard._pages) == 3


# =============================================================================
# ТЕСТЫ ONBOARDING
# =============================================================================

class TestOnboardingStep:
    """Тесты для OnboardingStep."""

    def test_step_creation(self):
        """Тест создания шага онбординга."""
        step = OnboardingStep(
            id="test.step",
            title="Тестовый шаг",
            description="Описание тестового шага",
            step_type=OnboardingStepType.HIGHLIGHT
        )

        assert step.id == "test.step"
        assert step.title == "Тестовый шаг"
        assert not step.is_completed


class TestOnboardingManager:
    """Тесты для OnboardingManager."""

    def test_default_steps(self):
        """Тест наличия стандартных шагов."""
        assert len(DEFAULT_ONBOARDING_STEPS) > 0

        # Проверяем наличие шагов приветствия и завершения
        step_ids = [s.id for s in DEFAULT_ONBOARDING_STEPS]
        assert "welcome" in step_ids
        assert "complete" in step_ids

    def test_manager_creation(self, main_window, tmp_path):
        """Тест создания менеджера онбординга."""
        config_path = tmp_path / "test_config.json"
        manager = OnboardingManager(main_window, config_path)

        assert manager is not None
        assert len(manager._steps) > 0

    def test_is_completed(self, main_window, tmp_path):
        """Тест проверки завершённости онбординга."""
        config_path = tmp_path / "test_config.json"
        manager = OnboardingManager(main_window, config_path)

        # По умолчанию не завершён
        assert not manager.is_completed()

    def test_reset(self, main_window, tmp_path):
        """Тест сброса состояния онбординга."""
        config_path = tmp_path / "test_config.json"
        manager = OnboardingManager(main_window, config_path)

        manager.reset()

        assert not manager.is_completed()


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================

class TestPhase3Integration:
    """Интеграционные тесты для Фазы 3."""

    def test_shortcut_toast_integration(self, qtbot, main_window):
        """Тест интеграции горячих клавиш и toast."""
        manager = ShortcutManager()

        # Регистрируем действие показа toast
        toast_manager = ToastManager(main_window)
        manager.register(
            main_window,
            "file.open",
            lambda: toast_manager.show_info("Тест")
        )

        # Проверяем что регистрация прошла успешно
        assert "file.open" in manager._shortcuts

    def test_dashboard_shortcuts(self, qtbot, main_window):
        """Тест горячих клавиш на Dashboard."""
        dashboard = DashboardWidget()
        qtbot.addWidget(dashboard)

        manager = ShortcutManager()

        # Регистрируем навигацию
        manager.register(
            dashboard,
            "view.dashboard",
            lambda: None
        )

        assert "view.dashboard" in manager._shortcuts


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
