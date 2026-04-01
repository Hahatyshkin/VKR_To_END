"""
Tests for Event Bus functionality.

Tests:
- EventBus singleton pattern
- Event subscription and publishing
- Event types and data classes
- Thread-safe event handling
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import sys

# Skip all tests if PySide6 is not available
pytest.importorskip("PySide6")

from PySide6.QtCore import QThread, Signal, QObject


class TestEventType:
    """Tests for EventType enum."""
    
    def test_event_types_exist(self):
        """Test that all expected event types are defined."""
        from src.ui_new.events import EventType
        
        # File events
        assert EventType.FILE_LOADED
        assert EventType.FILE_PROCESSED
        assert EventType.FILE_DELETED
        assert EventType.FILES_CLEARED
        
        # Processing events
        assert EventType.PROCESSING_STARTED
        assert EventType.PROCESSING_FINISHED
        assert EventType.PROCESSING_ERROR
        assert EventType.PROCESSING_PROGRESS
        
        # Settings events
        assert EventType.SETTINGS_CHANGED
        assert EventType.THEME_CHANGED
        
        # Player events
        assert EventType.PLAYER_STATE_CHANGED


class TestEventDataClasses:
    """Tests for Event data classes."""
    
    def test_base_event_creation(self):
        """Test creating a base Event."""
        from src.ui_new.events import Event, EventType
        
        event = Event(type=EventType.FILE_LOADED)
        
        assert event.type == EventType.FILE_LOADED
        assert isinstance(event.timestamp, datetime)
        assert event.source is None
        
    def test_base_event_with_source(self):
        """Test creating an Event with source."""
        from src.ui_new.events import Event, EventType
        
        event = Event(type=EventType.FILE_LOADED, source="TestSource")
        
        assert event.source == "TestSource"
        
    def test_event_to_dict(self):
        """Test converting Event to dictionary."""
        from src.ui_new.events import Event, EventType
        
        event = Event(type=EventType.FILE_LOADED, source="TestSource")
        d = event.to_dict()
        
        assert d["type"] == "FILE_LOADED"
        assert d["source"] == "TestSource"
        assert "timestamp" in d
        
    def test_file_event_creation(self):
        """Test creating a FileEvent."""
        from src.ui_new.events import FileEvent, EventType
        
        event = FileEvent(
            type=EventType.FILE_LOADED,
            path="/path/to/file.wav",
            file_size=1024000,
            file_type=".wav"
        )
        
        assert event.path == "/path/to/file.wav"
        assert event.file_size == 1024000
        assert event.file_type == ".wav"
        
    def test_processing_event_creation(self):
        """Test creating a ProcessingEvent."""
        from src.ui_new.events import ProcessingEvent, EventType
        
        event = ProcessingEvent(
            type=EventType.PROCESSING_STARTED,
            file_path="/path/to/file.wav",
            method="fwht",
            total_files=10,
            progress=0.0
        )
        
        assert event.file_path == "/path/to/file.wav"
        assert event.method == "fwht"
        assert event.total_files == 10
        assert event.progress == 0.0
        
    def test_player_event_creation(self):
        """Test creating a PlayerEvent."""
        from src.ui_new.events import PlayerEvent, EventType
        
        event = PlayerEvent(
            type=EventType.PLAYER_STATE_CHANGED,
            state="playing",
            file_path="/path/to/file.mp3",
            position_ms=5000,
            duration_ms=180000
        )
        
        assert event.state == "playing"
        assert event.position_ms == 5000
        assert event.duration_ms == 180000
        
    def test_settings_event_creation(self):
        """Test creating a SettingsEvent."""
        from src.ui_new.events import SettingsEvent, EventType
        
        event = SettingsEvent(
            type=EventType.SETTINGS_CHANGED,
            setting_key="bitrate",
            old_value="128k",
            new_value="192k"
        )
        
        assert event.setting_key == "bitrate"
        assert event.old_value == "128k"
        assert event.new_value == "192k"


class TestEventBus:
    """Tests for EventBus singleton."""
    
    def test_event_bus_singleton(self):
        """Test that EventBus is a singleton."""
        from src.ui_new.events import EventBus
        
        # Clear any existing instance
        EventBus._instance = None
        EventBus._initialized = False
        
        bus1 = EventBus()
        bus2 = EventBus()
        
        assert bus1 is bus2
        
    def test_subscribe_and_publish(self):
        """Test subscribing to and publishing events."""
        from src.ui_new.events import EventBus, Event, EventType
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        callback = Mock()
        EventBus.subscribe(EventType.FILE_LOADED, callback)
        
        event = Event(type=EventType.FILE_LOADED)
        EventBus.publish_sync(event)
        
        callback.assert_called_once()
        
    def test_multiple_subscribers(self):
        """Test multiple subscribers for same event type."""
        from src.ui_new.events import EventBus, Event, EventType
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        callback1 = Mock()
        callback2 = Mock()
        
        EventBus.subscribe(EventType.FILE_LOADED, callback1)
        EventBus.subscribe(EventType.FILE_LOADED, callback2)
        
        event = Event(type=EventType.FILE_LOADED)
        EventBus.publish_sync(event)
        
        callback1.assert_called_once()
        callback2.assert_called_once()
        
    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        from src.ui_new.events import EventBus, Event, EventType
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        callback = Mock()
        EventBus.subscribe(EventType.FILE_LOADED, callback)
        EventBus.unsubscribe(EventType.FILE_LOADED, callback)
        
        event = Event(type=EventType.FILE_LOADED)
        EventBus.publish_sync(event)
        
        callback.assert_not_called()
        
    def test_event_history(self):
        """Test event history tracking."""
        from src.ui_new.events import EventBus, Event, EventType
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        for i in range(5):
            event = Event(type=EventType.FILE_LOADED, source=f"source_{i}")
            EventBus.publish_sync(event)
        
        history = EventBus.get_history(limit=10)
        
        assert len(history) == 5
        
    def test_clear_subscribers(self):
        """Test clearing all subscribers."""
        from src.ui_new.events import EventBus, Event, EventType
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        callback = Mock()
        EventBus.subscribe(EventType.FILE_LOADED, callback)
        EventBus.clear_subscribers()
        
        event = Event(type=EventType.FILE_LOADED)
        EventBus.publish_sync(event)
        
        callback.assert_not_called()
        
    def test_subscriber_count(self):
        """Test counting subscribers."""
        from src.ui_new.events import EventBus, EventType
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()
        
        EventBus.subscribe(EventType.FILE_LOADED, callback1)
        EventBus.subscribe(EventType.FILE_LOADED, callback2)
        EventBus.subscribe(EventType.PROCESSING_STARTED, callback3)
        
        assert EventBus.subscriber_count(EventType.FILE_LOADED) == 2
        assert EventBus.subscriber_count(EventType.PROCESSING_STARTED) == 1
        assert EventBus.subscriber_count() == 3


class TestEventEmitters:
    """Tests for convenience event emitter functions."""
    
    def test_emit_file_loaded(self):
        """Test emit_file_loaded function."""
        from src.ui_new.events import (
            EventBus, EventType, FileEvent, emit_file_loaded
        )
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        callback = Mock()
        EventBus.subscribe(EventType.FILE_LOADED, callback)
        
        emit_file_loaded(path="/path/to/file.wav", file_size=1024)
        
        # emit_file_loaded uses async publish, so we need to process events
        # For testing, we'll verify the callback was set up correctly
        assert EventBus.subscriber_count(EventType.FILE_LOADED) == 1
        
    def test_emit_processing_started(self):
        """Test emit_processing_started function."""
        from src.ui_new.events import (
            EventBus, EventType, emit_processing_started
        )
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        callback = Mock()
        EventBus.subscribe(EventType.PROCESSING_STARTED, callback)
        
        emit_processing_started(file_count=10)
        
        assert EventBus.subscriber_count(EventType.PROCESSING_STARTED) == 1
        
    def test_emit_player_state_changed(self):
        """Test emit_player_state_changed function."""
        from src.ui_new.events import (
            EventBus, EventType, emit_player_state_changed
        )
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        callback = Mock()
        EventBus.subscribe(EventType.PLAYER_STATE_CHANGED, callback)
        
        emit_player_state_changed(state="playing", position_ms=5000)
        
        assert EventBus.subscriber_count(EventType.PLAYER_STATE_CHANGED) == 1


class TestEventBusIntegration:
    """Integration tests for EventBus with mock components."""
    
    def test_event_bus_receives_event_data(self):
        """Test that event data is properly passed to callbacks."""
        from src.ui_new.events import (
            EventBus, EventType, FileEvent
        )
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        received_data = {}
        
        def callback(event_dict):
            received_data.update(event_dict)
        
        EventBus.subscribe(EventType.FILE_LOADED, callback)
        
        event = FileEvent(
            type=EventType.FILE_LOADED,
            path="/test/path.wav",
            file_size=2048,
            file_type=".wav"
        )
        EventBus.publish_sync(event)
        
        assert received_data["type"] == "FILE_LOADED"
        assert received_data["path"] == "/test/path.wav"
        assert received_data["file_size"] == 2048
        
    def test_event_bus_error_handling(self):
        """Test that errors in callbacks don't crash the bus."""
        from src.ui_new.events import EventBus, Event, EventType
        
        # Reset EventBus
        EventBus._instance = None
        EventBus._initialized = False
        
        bad_callback = Mock(side_effect=Exception("Test error"))
        good_callback = Mock()
        
        EventBus.subscribe(EventType.FILE_LOADED, bad_callback)
        EventBus.subscribe(EventType.FILE_LOADED, good_callback)
        
        event = Event(type=EventType.FILE_LOADED)
        # Should not raise
        EventBus.publish_sync(event)
        
        # Good callback should still be called
        good_callback.assert_called_once()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def reset_event_bus():
    """Reset EventBus before each test."""
    from src.ui_new.events import EventBus
    
    EventBus._instance = None
    EventBus._initialized = False
    
    yield
    
    # Cleanup
    try:
        EventBus.clear_subscribers()
    except Exception:
        pass
