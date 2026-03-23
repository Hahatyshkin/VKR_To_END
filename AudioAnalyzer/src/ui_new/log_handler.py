"""
Логирование в UI: Qt-совместимый обработчик логов.

Назначение:
- Перенаправление Python logging в Qt-виджеты через сигналы.
- Форматирование лог-сообщений для отображения в панели UI.

Внешние зависимости: PySide6 (QObject, Signal), logging, datetime.

ВАЖНО: Этот обработчик должен использоваться ТОЛЬКО из главного потока!
Для логирования из Worker потока используйте отдельный механизм (stdout/file).
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, Signal, QCoreApplication, QMetaObject, Qt


class UiLogEmitter(QObject):
    """Qt-эмиттер для передачи лог-сообщений в UI.

    Используется как мост между Python logging и Qt-виджетами.
    Подключите сигнал log_line к слоту текстового виджета.
    """
    log_line = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = True
    
    def disable(self) -> None:
        """Отключить эмиттер для безопасного shutdown."""
        self._enabled = False
        self.blockSignals(True)


class QtLogHandler(logging.Handler):
    """Обработчик логов для вывода в Qt UI.

    Форматирует записи лога в читаемые строки и отправляет их
    через UiLogEmitter в текстовую панель интерфейса.
    
    ВАЖНО: Этот обработчик безопасен для использования из любого потока.
    При вызове из не-GUI потока он использует QMetaObject.invokeMethod
    для безопасной отправки сигнала в GUI поток.

    Пример использования:
        emitter = UiLogEmitter()
        emitter.log_line.connect(text_edit.appendPlainText)
        handler = QtLogHandler(emitter)
        logging.getLogger().addHandler(handler)
    """

    def __init__(self, emitter: UiLogEmitter, *, show_timestamp: bool = True):
        """Инициализация обработчика.

        Параметры:
        - emitter: UiLogEmitter для отправки сообщений в UI
        - show_timestamp: показывать ли временную метку в логах
        """
        super().__init__()
        self.emitter = emitter
        self._show_timestamp = show_timestamp
        self._formatter: Optional[logging.Formatter] = None
        # Флаг для безопасного отключения во время shutdown
        self._enabled = True
        # Главный поток для проверки
        self._main_thread_id = threading.main_thread().ident

    def emit(self, record: logging.LogRecord) -> None:
        """Обработать запись лога и отправить в UI.

        Формат: "HH:MM:SS [LEVEL] logger: message"
        При наличии исключения добавляется трассировка.
        """
        # Проверяем, что обработчик включён (безопасный shutdown)
        if not self._enabled or self.emitter is None:
            return
        
        # Проверяем, что emitter ещё существует
        try:
            if not self.emitter._enabled:
                return
        except (AttributeError, RuntimeError):
            self._enabled = False
            return
            
        try:
            # Формируем временную метку
            if self._show_timestamp:
                ts = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
                line = f"{ts} [{record.levelname}] {record.name}: {record.getMessage()}"
            else:
                line = f"[{record.levelname}] {record.name}: {record.getMessage()}"

            # Добавляем трассировку исключения, если есть
            if record.exc_info:
                try:
                    if self._formatter is None:
                        self._formatter = logging.Formatter()
                    exc_text = self._formatter.formatException(record.exc_info)
                    line += "\n" + exc_text
                except Exception:
                    pass

            # Проверяем поток - безопасно отправлять сигнал только из GUI потока
            current_thread_id = threading.current_thread().ident
            if current_thread_id != self._main_thread_id:
                # Мы в Worker потоке - НЕ отправляем сигнал напрямую!
                # Это может вызывать "setParent from different thread" ошибки
                # Просто игнорируем лог из Worker потока
                return
            
            # Отправляем в UI через сигнал (мы в GUI потоке)
            try:
                self.emitter.log_line.emit(line)
            except RuntimeError:
                # Qt объект уже уничтожен или в процессе уничтожения
                self._enabled = False

        except RuntimeError:
            # Qt объект уничтожен
            self._enabled = False
        except Exception:
            # При любой другой ошибке пытаемся отправить хотя бы базовое сообщение
            try:
                current_thread_id = threading.current_thread().ident
                if current_thread_id == self._main_thread_id:
                    self.emitter.log_line.emit(record.getMessage())
            except (RuntimeError, Exception):
                self._enabled = False

    def setTimestampVisible(self, visible: bool) -> None:
        """Установить видимость временной метки."""
        self._show_timestamp = visible

    def disable(self) -> None:
        """Отключить обработчик для безопасного shutdown.
        
        После вызова этого метода emit() не будет отправлять сигналы.
        Это предотвращает краш при попытке отправить сигнал из Worker
        потока во время уничтожения Qt объектов.
        """
        self._enabled = False
