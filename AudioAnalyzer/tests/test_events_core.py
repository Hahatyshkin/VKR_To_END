"""
Tests for Event Bus functionality (without Qt dependency).

Tests:
- Event data classes
- Event types enum
- EventBus core logic (without Qt signal testing)
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import sys

# Check if PySide6 is available
try:
    import PySide6
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

# Skip all tests if PySide6 is not available
pytestmark = pytest.mark.skipif(
    not HAS_PYSIDE6,
    reason="PySide6 not available"
)


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
        
    def test_event_type_auto_values(self):
        """Test that EventType values are auto-assigned."""
        from src.ui_new.events import EventType
        
        # Each event type should have a unique value
        values = [e.value for e in EventType]
        assert len(values) == len(set(values))  # All unique


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
        assert event.type == EventType.FILE_LOADED
        
    def test_file_event_to_dict(self):
        """Test FileEvent to_dict includes file fields."""
        from src.ui_new.events import FileEvent, EventType
        
        event = FileEvent(
            type=EventType.FILE_LOADED,
            path="/path/to/file.wav",
            file_size=1024000,
            file_type=".wav",
            metadata={"sample_rate": 44100}
        )
        
        d = event.to_dict()
        
        assert d["path"] == "/path/to/file.wav"
        assert d["file_size"] == 1024000
        assert d["file_type"] == ".wav"
        
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
        
    def test_processing_event_error(self):
        """Test creating a ProcessingEvent with error."""
        from src.ui_new.events import ProcessingEvent, EventType
        
        event = ProcessingEvent(
            type=EventType.PROCESSING_ERROR,
            error_message="Failed to process file",
            file_path="/path/to/file.wav"
        )
        
        assert event.error_message == "Failed to process file"
        assert event.type == EventType.PROCESSING_ERROR
        
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
        
    def test_profile_event_creation(self):
        """Test creating a ProfileEvent."""
        from src.ui_new.events import ProfileEvent, EventType
        
        event = ProfileEvent(
            type=EventType.PROFILE_CHANGED,
            profile_name="HighQuality",
            profile_data={"bitrate": "320k"}
        )
        
        assert event.profile_name == "HighQuality"
        assert event.profile_data == {"bitrate": "320k"}
        
    def test_log_event_creation(self):
        """Test creating a LogEvent."""
        from src.ui_new.events import LogEvent, EventType
        
        event = LogEvent(
            type=EventType.LOG_MESSAGE,
            level="INFO",
            message="Processing started"
        )
        
        assert event.level == "INFO"
        assert event.message == "Processing started"


class TestEventBusWithoutQt:
    """Tests for EventBus core logic without Qt signal mechanism."""
    
    def test_event_bus_singleton_pattern(self):
        """Test that EventBus uses singleton pattern."""
        from src.ui_new.events import EventBus
        
        # Check that EventBus has singleton attributes
        assert hasattr(EventBus, '_instance')
        assert hasattr(EventBus, '_initialized')
        
    def test_event_bus_class_methods_exist(self):
        """Test that EventBus has required class methods."""
        from src.ui_new.events import EventBus
        
        assert hasattr(EventBus, 'subscribe')
        assert hasattr(EventBus, 'unsubscribe')
        assert hasattr(EventBus, 'publish')
        assert hasattr(EventBus, 'publish_sync')
        assert hasattr(EventBus, 'clear_subscribers')
        assert hasattr(EventBus, 'get_history')
        assert hasattr(EventBus, 'set_enabled')
        assert hasattr(EventBus, 'subscriber_count')
        
    def test_event_bus_instance_methods_exist(self):
        """Test that EventBus instance has required methods."""
        from src.ui_new.events import EventBus
        
        # These are instance methods
        bus_methods = [
            '__init__',
            '_dispatch_event',
        ]
        
        for method in bus_methods:
            assert hasattr(EventBus, method)


class TestConvenienceFunctions:
    """Tests for convenience event emitter functions."""
    
    def test_emit_functions_exist(self):
        """Test that all emit functions are defined."""
        from src.ui_new.events import (
            emit_file_loaded,
            emit_file_processed,
            emit_processing_started,
            emit_processing_finished,
            emit_processing_progress,
            emit_processing_error,
            emit_settings_changed,
            emit_theme_changed,
            emit_profile_changed,
            emit_log_message,
            emit_results_updated,
            emit_player_state_changed,
        )
        
        # All functions should be callable
        assert callable(emit_file_loaded)
        assert callable(emit_file_processed)
        assert callable(emit_processing_started)
        assert callable(emit_processing_finished)
        assert callable(emit_processing_progress)
        assert callable(emit_processing_error)
        assert callable(emit_settings_changed)
        assert callable(emit_theme_changed)
        assert callable(emit_profile_changed)
        assert callable(emit_log_message)
        assert callable(emit_results_updated)
        assert callable(emit_player_state_changed)
        
    def test_module_level_functions(self):
        """Test module level subscribe/publish functions."""
        from src.ui_new.events import subscribe, unsubscribe, publish, publish_sync
        
        assert callable(subscribe)
        assert callable(unsubscribe)
        assert callable(publish)
        assert callable(publish_sync)


class TestExports:
    """Tests for module exports."""
    
    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        from src.ui_new.events import __all__
        
        expected_exports = [
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
        
        for export in expected_exports:
            assert export in __all__, f"Missing export: {export}"


class TestEventIntegration:
    """Integration tests for Event system."""
    
    def test_event_flow_simulation(self):
        """Simulate a typical event flow without Qt."""
        from src.ui_new.events import (
            EventType,
            FileEvent,
            ProcessingEvent,
            PlayerEvent,
            SettingsEvent,
        )
        
        # 1. File loaded event
        file_event = FileEvent(
            type=EventType.FILE_LOADED,
            path="/music/track.wav",
            file_size=5000000,
            file_type=".wav"
        )
        assert file_event.to_dict()["type"] == "FILE_LOADED"
        
        # 2. Processing started event
        proc_event = ProcessingEvent(
            type=EventType.PROCESSING_STARTED,
            total_files=1,
            file_path="/music/track.wav"
        )
        assert proc_event.to_dict()["type"] == "PROCESSING_STARTED"
        
        # 3. Processing progress
        progress_event = ProcessingEvent(
            type=EventType.PROCESSING_PROGRESS,
            progress=50.0,
            file_path="/music/track.wav",
            method="fwht"
        )
        assert progress_event.progress == 50.0
        
        # 4. Settings changed
        settings_event = SettingsEvent(
            type=EventType.SETTINGS_CHANGED,
            setting_key="bitrate",
            old_value="128k",
            new_value="192k"
        )
        assert settings_event.new_value == "192k"
        
        # 5. Player state changed
        player_event = PlayerEvent(
            type=EventType.PLAYER_STATE_CHANGED,
            state="playing",
            file_path="/music/track_fwht.mp3"
        )
        assert player_event.state == "playing"
        
    def test_event_serialization(self):
        """Test that events can be serialized to dict."""
        from src.ui_new.events import (
            EventType,
            FileEvent,
            ProcessingEvent,
            AnalysisEvent,
            ProfileEvent,
            SettingsEvent,
            PlayerEvent,
            LogEvent,
        )
        
        events = [
            FileEvent(type=EventType.FILE_LOADED, path="/test.wav"),
            ProcessingEvent(type=EventType.PROCESSING_STARTED, total_files=5),
            AnalysisEvent(type=EventType.ANALYSIS_FINISHED, results_count=7),
            ProfileEvent(type=EventType.PROFILE_CHANGED, profile_name="Test"),
            SettingsEvent(type=EventType.SETTINGS_CHANGED, setting_key="test"),
            PlayerEvent(type=EventType.PLAYER_STATE_CHANGED, state="playing"),
            LogEvent(type=EventType.LOG_MESSAGE, message="test"),
        ]
        
        for event in events:
            d = event.to_dict()
            assert "type" in d
            assert "timestamp" in d
            assert isinstance(d["timestamp"], str)  # ISO format


# =============================================================================
# FIXTURES
# =============================================================================

# Check if PySide6 is available
try:
    import PySide6
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

# Skip all tests if PySide6 is not available
pytestmark = pytest.mark.skipif(
    not HAS_PYSIDE6,
    reason="PySide6 not available"
)


@pytest.fixture(autouse=True)
def reset_event_bus():
    """Reset EventBus singleton state before each test."""
    from src.ui_new.events import EventBus
    
    # Reset for test
    EventBus._instance = None
    EventBus._initialized = False
    
    yield
    
    # Reset after test
    EventBus._instance = None
    EventBus._initialized = False
