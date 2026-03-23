"""
UI компоненты Фазы 3: Улучшение UI/UX.

Содержит:
- Dashboard: панель мониторинга с ключевыми метриками
- ShortcutManager: система горячих клавиш
- ToastManager: toast-уведомления
- Wizards: мастера для сложных операций
- OnboardingManager: система онбординга
"""

from .dashboard import DashboardWidget
from .shortcuts import ShortcutManager, ShortcutAction
from .toast import ToastManager, ToastType
from .wizards import WizardDialog, CompareWizard, BatchProcessWizard
from .onboarding import OnboardingManager, OnboardingStep

__all__ = [
    # Dashboard
    "DashboardWidget",
    # Shortcuts
    "ShortcutManager",
    "ShortcutAction",
    # Toast
    "ToastManager",
    "ToastType",
    # Wizards
    "WizardDialog",
    "CompareWizard",
    "BatchProcessWizard",
    # Onboarding
    "OnboardingManager",
    "OnboardingStep",
]
