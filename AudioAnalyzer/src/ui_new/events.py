"""
Event Bus for loose coupling between application components.

Provides:
- Central event dispatcher for application-wide communication
- Type-safe event definitions
- Thread-safe event publishing (Qt signal-based)
- Subscription management with automatic cleanup

Usage:
------
>>> from ui_new.events import EventBus, Events
>>> 
>>> # Subscribe to events
>>> EventBus.subscribe(Events.FILE_LOADED, self.on_file_loaded)
>>> 
>>> # Publish events
>>> EventBus.publish(Events.FILE_LOADED, path="/path/to/file.wav")
>>> 
>>> # Unsubscribe
>>> EventBus.unsubscribe(Events.FILE_LOADED, self.on_file_loaded)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, fields
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("ui_new.events")


# =============================================================================
# EVENT DEFINITIONS
# =============================================================================

class EventType(Enum):
    """Base event types for the application."""
    
    # File events
    FILE_LOADED = auto()
    FILE_PROCESSED = auto()
    FILE_DELETED = auto()
    FILES_CLEARED = auto()
    
    # Processing events
    PROCESSING_STARTED = auto()
    PROCESSING_FINISHED = auto()
    PROCESSING_CANCELLED = auto()
    PROCESSING_ERROR = auto()
    PROCESSING_PROGRESS = auto()
    
    # Analysis events
    ANALYSIS_STARTED = auto()
    ANALYSIS_FINISHED = auto()
    ANALYSIS_ERROR = auto()
    ANALYSIS_PROGRESS = auto()
    
    # Profile events
    PROFILE_CHANGED = auto()
    PROFILE_SAVED = auto()
    PROFILE_LOADED = auto()
    
    # Settings events
    SETTINGS_CHANGED = auto()
    THEME_CHANGED = auto()
    
    # UI events
    TAB_CHANGED = auto()
    RESULTS_UPDATED = auto()
    SPECTRUM_UPDATED = auto()
    PLAYER_STATE_CHANGED = auto()
    
    # Application events
    APP_READY = auto()
    APP_CLOSING = auto()
    LOG_MESSAGE = auto()


@dataclass
class Event:
    """Base event data class.
    
    Все подклассы автоматически наследуют поля type, timestamp, source.
    Метод to_dict() сериализует все поля включая поля подклассов.
    """
    
    type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization.
        
        Включает все поля dataclass'а (базовые и подкласса).
        Автоматически обрабатывает:
        - EventType -> str (имя enum)
        - datetime -> ISO формат
        - dict/list -> как есть
        - None -> None
        """
        result = {}
        
        # Получаем все поля dataclass'а (включая наследуемые)
        for f in fields(self):
            value = getattr(self, f.name)
            
            # Обработка специальных типов
            if isinstance(value, EventType):
                result[f.name] = value.name
            elif isinstance(value, datetime):
                result[f.name] = value.isoformat()
            else:
                result[f.name] = value
        
        return result


@dataclass
class FileEvent(Event):
    """Event for file operations."""
    
    path: str = ""
    file_size: int = 0
    file_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingEvent(Event):
    """Event for processing operations."""
    
    file_path: str = ""
    method: str = ""
    progress: float = 0.0
    total_files: int = 0
    processed_files: int = 0
    eta_seconds: float = 0.0
    error_message: str = ""


@dataclass
class AnalysisEvent(Event):
    """Event for analysis operations."""
    
    source_file: str = ""
    results_count: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class ProfileEvent(Event):
    """Event for profile operations."""
    
    profile_name: str = ""
    profile_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SettingsEvent(Event):
    """Event for settings changes."""
    
    setting_key: str = ""
    old_value: Any = None
    new_value: Any = None


@dataclass
class PlayerEvent(Event):
    """Event for player state changes."""
    
    file_path: str = ""
    state: str = ""  # "playing", "paused", "stopped"
    position_ms: int = 0
    duration_ms: int = 0


@dataclass
class LogEvent(Event):
    """Event for log messages."""
    
    level: str = "INFO"
    message: str = ""


# =============================================================================
# EVENT BUS
# =============================================================================

class EventSignaler(QObject):
    """QObject for thread-safe signal emission."""
    
    # Signal carries the event as a dict for thread safety
    event_signal = Signal(dict)


class EventBus:
    """Central event dispatcher for application-wide communication.
    
    Features:
    - Thread-safe event publishing via Qt signals
    - Type-safe event definitions
    - Subscription management
    - Event history (optional)
    
    Usage:
    ------
    >>> # Subscribe to events
    >>> def on_file_loaded(event: dict):
    ...     print(f"File loaded: {event['path']}")
    >>> EventBus.subscribe(EventType.FILE_LOADED, on_file_loaded)
    >>> 
    >>> # Publish events
    >>> EventBus.publish(FileEvent(
    ...     type=EventType.FILE_LOADED,
    ...     path="/path/to/file.wav"
    ... ))
    >>> 
    >>> # Unsubscribe
    >>> EventBus.unsubscribe(EventType.FILE_LOADED, on_file_loaded)
    """
    
    _instance: Optional["EventBus"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "EventBus":
        """Singleton pattern for global event bus."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize event bus."""
        if self._initialized:
            return
        
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._signaler = EventSignaler()
        self._history: List[Dict] = []
        self._max_history: int = 100
        self._enabled: bool = True
        
        # Connect internal signal to dispatcher
        self._signaler.event_signal.connect(self._dispatch_event)
        
        self._initialized = True
        logger.debug("EventBus initialized")
    
    @classmethod
    def subscribe(cls, event_type: EventType, callback: Callable) -> None:
        """Subscribe to an event type.
        
        Parameters
        ----------
        event_type : EventType
            The event type to subscribe to
        callback : Callable
            Function to call when event is published
        """
        instance = cls()
        
        if event_type not in instance._subscribers:
            instance._subscribers[event_type] = []
        
        if callback not in instance._subscribers[event_type]:
            instance._subscribers[event_type].append(callback)
            logger.debug("Subscribed to %s: %s", event_type.name, callback.__name__)
    
    @classmethod
    def unsubscribe(cls, event_type: EventType, callback: Callable) -> None:
        """Unsubscribe from an event type.
        
        Parameters
        ----------
        event_type : EventType
            The event type to unsubscribe from
        callback : Callable
            The callback to remove
        """
        instance = cls()
        
        if event_type in instance._subscribers:
            try:
                instance._subscribers[event_type].remove(callback)
                logger.debug("Unsubscribed from %s: %s", event_type.name, callback.__name__)
            except ValueError:
                pass
    
    @classmethod
    def publish(cls, event: Event) -> None:
        """Publish an event to all subscribers.
        
        This method is thread-safe - it uses Qt signals for cross-thread
        communication.
        
        Parameters
        ----------
        event : Event
            The event to publish
        """
        instance = cls()
        
        if not instance._enabled:
            return
        
        event_dict = event.to_dict()
        
        # Add to history
        instance._history.append(event_dict)
        if len(instance._history) > instance._max_history:
            instance._history.pop(0)
        
        # Emit via Qt signal (thread-safe)
        instance._signaler.event_signal.emit(event_dict)
        logger.debug("Published event: %s", event.type.name)
    
    @classmethod
    def publish_sync(cls, event: Event) -> None:
        """Publish an event synchronously (direct call).
        
        Use this for events that need immediate processing in the same thread.
        
        Parameters
        ----------
        event : Event
            The event to publish
        """
        instance = cls()
        
        if not instance._enabled:
            return
        
        event_dict = event.to_dict()
        instance._dispatch_event(event_dict)
    
    def _dispatch_event(self, event_dict: Dict[str, Any]) -> None:
        """Dispatch event to subscribers (internal method)."""
        try:
            event_type_name = event_dict.get("type", "")
            event_type = EventType[event_type_name]
        except KeyError:
            logger.warning("Unknown event type: %s", event_dict.get("type"))
            return
        
        subscribers = self._subscribers.get(event_type, [])
        
        for callback in subscribers:
            try:
                callback(event_dict)
            except Exception as e:
                logger.error(
                    "Error in event handler %s for %s: %s",
                    callback.__name__,
                    event_type.name,
                    e
                )
    
    @classmethod
    def clear_subscribers(cls, event_type: Optional[EventType] = None) -> None:
        """Clear all subscribers for an event type or all events.
        
        Parameters
        ----------
        event_type : Optional[EventType]
            If provided, clear only this event type. Otherwise clear all.
        """
        instance = cls()
        
        if event_type is not None:
            instance._subscribers[event_type] = []
        else:
            instance._subscribers.clear()
        
        logger.debug("Cleared subscribers for %s", event_type.name if event_type else "all events")
    
    @classmethod
    def get_history(cls, limit: int = 50) -> List[Dict]:
        """Get recent event history.
        
        Parameters
        ----------
        limit : int
            Maximum number of events to return
        
        Returns
        -------
        List[Dict]
            Recent events as dictionaries
        """
        instance = cls()
        return instance._history[-limit:]
    
    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        """Enable or disable event publishing.
        
        Parameters
        ----------
        enabled : bool
            Whether to enable event publishing
        """
        instance = cls()
        instance._enabled = enabled
        logger.debug("EventBus enabled: %s", enabled)
    
    @classmethod
    def subscriber_count(cls, event_type: Optional[EventType] = None) -> int:
        """Get the number of subscribers.
        
        Parameters
        ----------
        event_type : Optional[EventType]
            If provided, count only this event type. Otherwise count all.
        
        Returns
        -------
        int
            Number of subscribers
        """
        instance = cls()
        
        if event_type is not None:
            return len(instance._subscribers.get(event_type, []))
        
        return sum(len(subs) for subs in instance._subscribers.values())


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def subscribe(event_type: EventType, callback: Callable) -> None:
    """Subscribe to an event type."""
    EventBus.subscribe(event_type, callback)


def unsubscribe(event_type: EventType, callback: Callable) -> None:
    """Unsubscribe from an event type."""
    EventBus.unsubscribe(event_type, callback)


def publish(event: Event) -> None:
    """Publish an event."""
    EventBus.publish(event)


def publish_sync(event: Event) -> None:
    """Publish an event synchronously."""
    EventBus.publish_sync(event)


# =============================================================================
# EVENT FACTORY FUNCTIONS
# =============================================================================

def emit_file_loaded(path: str, file_size: int = 0, **kwargs) -> None:
    """Emit a file loaded event."""
    publish(FileEvent(
        type=EventType.FILE_LOADED,
        path=path,
        file_size=file_size,
        **kwargs
    ))


def emit_file_processed(path: str, method: str, **kwargs) -> None:
    """Emit a file processed event."""
    publish(ProcessingEvent(
        type=EventType.FILE_PROCESSED,
        file_path=path,
        method=method,
        **kwargs
    ))


def emit_processing_started(file_count: int, **kwargs) -> None:
    """Emit a processing started event."""
    publish(ProcessingEvent(
        type=EventType.PROCESSING_STARTED,
        total_files=file_count,
        **kwargs
    ))


def emit_processing_finished(processed_count: int, **kwargs) -> None:
    """Emit a processing finished event."""
    publish(ProcessingEvent(
        type=EventType.PROCESSING_FINISHED,
        processed_files=processed_count,
        **kwargs
    ))


def emit_processing_progress(
    progress: float, 
    file_path: str = "", 
    method: str = "",
    eta_seconds: float = 0.0,
    **kwargs
) -> None:
    """Emit a processing progress event."""
    publish_sync(ProcessingEvent(
        type=EventType.PROCESSING_PROGRESS,
        progress=progress,
        file_path=file_path,
        method=method,
        eta_seconds=eta_seconds,
        **kwargs
    ))


def emit_processing_error(error_message: str, file_path: str = "", **kwargs) -> None:
    """Emit a processing error event."""
    publish(ProcessingEvent(
        type=EventType.PROCESSING_ERROR,
        error_message=error_message,
        file_path=file_path,
        **kwargs
    ))


def emit_settings_changed(key: str, old_value: Any, new_value: Any, **kwargs) -> None:
    """Emit a settings changed event."""
    publish(SettingsEvent(
        type=EventType.SETTINGS_CHANGED,
        setting_key=key,
        old_value=old_value,
        new_value=new_value,
        **kwargs
    ))


def emit_theme_changed(theme_name: str, **kwargs) -> None:
    """Emit a theme changed event."""
    publish(SettingsEvent(
        type=EventType.THEME_CHANGED,
        setting_key="theme",
        new_value=theme_name,
        **kwargs
    ))


def emit_profile_changed(profile_name: str, **kwargs) -> None:
    """Emit a profile changed event."""
    publish(ProfileEvent(
        type=EventType.PROFILE_CHANGED,
        profile_name=profile_name,
        **kwargs
    ))


def emit_log_message(level: str, message: str, **kwargs) -> None:
    """Emit a log message event."""
    publish_sync(LogEvent(
        type=EventType.LOG_MESSAGE,
        level=level,
        message=message,
        **kwargs
    ))


def emit_results_updated(count: int, **kwargs) -> None:
    """Emit a results updated event."""
    publish(AnalysisEvent(
        type=EventType.RESULTS_UPDATED,
        results_count=count,
        **kwargs
    ))


def emit_player_state_changed(
    state: str, 
    file_path: str = "",
    position_ms: int = 0,
    duration_ms: int = 0,
    **kwargs
) -> None:
    """Emit a player state changed event."""
    publish_sync(PlayerEvent(
        type=EventType.PLAYER_STATE_CHANGED,
        state=state,
        file_path=file_path,
        position_ms=position_ms,
        duration_ms=duration_ms,
        **kwargs
    ))


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Core classes
    "EventBus",
    "EventType",
    "Event",
    "EventSignaler",
    # Event data classes
    "FileEvent",
    "ProcessingEvent",
    "AnalysisEvent",
    "ProfileEvent",
    "SettingsEvent",
    "PlayerEvent",
    "LogEvent",
    # Convenience functions
    "subscribe",
    "unsubscribe",
    "publish",
    "publish_sync",
    # Event emitters
    "emit_file_loaded",
    "emit_file_processed",
    "emit_processing_started",
    "emit_processing_finished",
    "emit_processing_progress",
    "emit_processing_error",
    "emit_settings_changed",
    "emit_theme_changed",
    "emit_profile_changed",
    "emit_log_message",
    "emit_results_updated",
    "emit_player_state_changed",
]
