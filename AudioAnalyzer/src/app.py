"""
Точка входа настольного приложения Audio Transformer.

Назначение:
- Инициализировать структурированное логирование (JSON) и каталоги логов.
- Загрузить и запустить класс главного окна Qt (ui_new).
- Показать понятные сообщения об ошибках при проблемах.
- Глобальный обработчик исключений для логирования крашей.

Внешние библиотеки:
- PySide6: графический интерфейс (QApplication, QMessageBox).
- logging: корневое логирование.

Переменные окружения:
- APP_LOG_DIR, APP_LOG_PATH — выставляются в utils.logging_setup.
"""
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import qInstallMessageHandler, QtMsgType
import logging
import os
import sys
import traceback
from datetime import datetime
from importlib import import_module


# =============================================================================
# ГЛОБАЛЬНЫЙ ФАЙЛ ДЛЯ КРАШЕЙ
# =============================================================================

CRASH_LOG_FILE = None


def _get_crash_log_path() -> str:
    """Получить путь к файлу краш-логов."""
    global CRASH_LOG_FILE
    if CRASH_LOG_FILE is None:
        # Определяем директорию для краш-логов
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.getcwd()
        
        crash_dir = os.path.join(base_dir, 'crash_logs')
        try:
            os.makedirs(crash_dir, exist_ok=True)
        except Exception:
            crash_dir = base_dir
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        CRASH_LOG_FILE = os.path.join(crash_dir, f'crash_{timestamp}.log')
    
    return CRASH_LOG_FILE


def _write_crash(message: str) -> None:
    """Записать сообщение о краше в файл."""
    try:
        crash_file = _get_crash_log_path()
        with open(crash_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"TIME: {datetime.now().isoformat()}\n")
            f.write(f"{message}\n")
            f.write(f"{'='*60}\n")
            f.flush()
    except Exception:
        pass


def _exception_hook(exc_type, exc_value, exc_tb) -> None:
    """Глобальный обработчик необработанных исключений."""
    # Формируем полный трейсбек
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    tb_text = ''.join(tb_lines)
    
    # Пишем в файл краша
    _write_crash(f"UNHANDLED EXCEPTION:\n{tb_text}")
    
    # Пытаемся записать в лог
    try:
        log = logging.getLogger("app.crash")
        log.critical(f"UNHANDLED EXCEPTION: {exc_type.__name__}: {exc_value}")
        log.critical(tb_text)
    except Exception:
        pass
    
    # Пытаемся показать диалог (может не сработать если Qt уже разрушен)
    try:
        QMessageBox.critical(
            None,
            "Критическая ошибка",
            f"Произошла ошибка:\n{exc_type.__name__}: {exc_value}\n\n"
            f"Детали записаны в файл:\n{_get_crash_log_path()}"
        )
    except Exception:
        pass
    
    # Вызываем оригинальный обработчик
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def _qt_message_handler(msg_type, context, msg):
    """Обработчик Qt сообщений для логирования."""
    try:
        log = logging.getLogger("qt")
        
        # Записываем в файл краша если это ошибка или критическая ошибка
        if msg_type in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg, QtMsgType.QtWarningMsg):
            location = ""
            if context.file:
                location = f" [{context.file}:{context.line}]"
            _write_crash(f"QT {msg_type.name}{location}: {msg}")
        
        if msg_type == QtMsgType.QtDebugMsg:
            log.debug(msg)
        elif msg_type == QtMsgType.QtInfoMsg:
            log.info(msg)
        elif msg_type == QtMsgType.QtWarningMsg:
            log.warning(msg)
        elif msg_type == QtMsgType.QtCriticalMsg:
            log.critical(msg)
        elif msg_type == QtMsgType.QtFatalMsg:
            log.critical(f"FATAL: {msg}")
            _write_crash(f"QT FATAL: {msg}")
    except Exception:
        pass


# Устанавливаем глобальные обработчики
sys.excepthook = _exception_hook


# =============================================================================
# ИМПОРТ MAINWINDOW
# =============================================================================

# Прямой импорт из нового модуля ui_new
try:
    from ui_new.main_window import MainWindow  # type: ignore
except ImportError:
    try:
        from src.ui_new.main_window import MainWindow  # type: ignore
    except ImportError as e:
        MainWindow = None  # Будет обработано в main()


# =============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================================================================

def _setup_logging() -> None:
    """Подготовить каталог логов и сконфигурировать корневой логгер.

    Пробует несколько вариантов расположения логов:
    1. ./logs (рядом с приложением)
    2. LocalAppData/AudioTransformer/logs (Windows)
    3. TEMP/AudioTransformer/logs
    """
    # Импорт модуля конфигурации логов
    _logging_setup = None
    for module_path in ['utils.logging_setup', 'src.utils.logging_setup']:
        try:
            _logging_setup = import_module(module_path)
            break
        except ImportError:
            continue

    if _logging_setup is None:
        return  # Продолжаем без файлового логирования

    # Определение базовой директории
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.getcwd()

    # Кандидаты для логов
    candidates = [
        os.path.join(base_dir, 'logs'),
        os.path.join(
            os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
            'AudioTransformer', 'logs'
        ),
        os.path.join(
            os.environ.get('TMP', os.environ.get('TEMP', os.getcwd())),
            'AudioTransformer', 'logs'
        ),
    ]

    # Пробуем создать директорию и настроить логирование
    for log_dir in candidates:
        try:
            os.makedirs(log_dir, exist_ok=True)
            # Проверка записи
            probe_file = os.path.join(log_dir, 'probe.txt')
            with open(probe_file, 'a', encoding='utf-8') as f:
                f.write('')
            # Настройка логирования
            _logging_setup.setup_logging(log_dir, json_logs=True)
            os.environ['APP_LOG_DIR'] = log_dir
            return
        except Exception:
            continue


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

def main() -> int:
    """Запуск QApplication и отображение MainWindow.

    Возвращает код выхода приложения (int).
    """
    _setup_logging()
    log = logging.getLogger("app")
    log.info("app_start")
    
    # Устанавливаем Qt обработчик сообщений
    qInstallMessageHandler(_qt_message_handler)

    app = QApplication(sys.argv)

    # Проверяем, что MainWindow загружен
    if MainWindow is None:
        log.error("main_window_import_failed")
        QMessageBox.critical(
            None,
            "Ошибка импорта",
            "Не удалось загрузить модуль UI. Проверьте установку PySide6."
        )
        return 1

    # Создаём и отображаем окно
    try:
        win = MainWindow()
        win.show()
        win.raise_()
        win.activateWindow()
    except Exception as e:
        log.exception("main_window_creation_error")
        _write_crash(f"main_window_creation_error: {e}\n{traceback.format_exc()}")
        QMessageBox.critical(
            None,
            "Ошибка создания окна",
            f"Не удалось создать главное окно:\n{e}"
        )
        return 1

    # Запуск цикла событий
    try:
        rc = app.exec()
        log.info("app_exit", extra={"exit_code": rc})
        return rc
    except Exception as e:
        log.exception("app_exec_error")
        _write_crash(f"app_exec_error: {e}\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
