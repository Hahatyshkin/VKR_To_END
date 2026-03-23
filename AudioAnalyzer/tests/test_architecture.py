"""
Tests for architectural improvements - Event Bus, Repositories, Pipeline.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# =============================================================================
# EVENT BUS TESTS
# =============================================================================

class TestEventBus:
    """Tests for Event Bus."""
    
    @classmethod
    def setup_class(cls):
        """Check if PySide6 is available."""
        try:
            import PySide6
            cls.has_pyside = True
        except ImportError:
            cls.has_pyside = False
    
    def test_import_event_bus(self):
        """Test that event bus can be imported."""
        try:
            from ui_new.events import EventBus, EventType
            assert EventBus is not None
            assert EventType is not None
        except ImportError:
            pytest.skip("PySide6 not available")
    
    def test_event_types_exist(self):
        """Test that event types are defined."""
        try:
            from ui_new.events import EventType
            
            # Check key event types
            assert hasattr(EventType, "FILE_LOADED")
            assert hasattr(EventType, "PROCESSING_STARTED")
            assert hasattr(EventType, "PROCESSING_FINISHED")
            assert hasattr(EventType, "SETTINGS_CHANGED")
            assert hasattr(EventType, "THEME_CHANGED")
        except ImportError:
            pytest.skip("PySide6 not available")
    
    def test_event_dataclass(self):
        """Test Event dataclass."""
        try:
            from ui_new.events import Event, EventType
            from datetime import datetime
            
            event = Event(type=EventType.FILE_LOADED, source="test")
            
            assert event.type == EventType.FILE_LOADED
            assert event.source == "test"
            assert isinstance(event.timestamp, datetime)
        except ImportError:
            pytest.skip("PySide6 not available")
    
    def test_file_event(self):
        """Test FileEvent dataclass."""
        try:
            from ui_new.events import FileEvent, EventType
            
            event = FileEvent(
                type=EventType.FILE_LOADED,
                path="/path/to/file.wav",
                file_size=1024000,
                file_type="wav",
            )
            
            assert event.path == "/path/to/file.wav"
            assert event.file_size == 1024000
            
            # Test serialization
            d = event.to_dict()
            assert d["path"] == "/path/to/file.wav"
        except ImportError:
            pytest.skip("PySide6 not available")
    
    def test_processing_event(self):
        """Test ProcessingEvent dataclass."""
        try:
            from ui_new.events import ProcessingEvent, EventType
            
            event = ProcessingEvent(
                type=EventType.PROCESSING_PROGRESS,
                file_path="/path/to/file.wav",
                method="fwht",
                progress=0.5,
                total_files=10,
                processed_files=5,
            )
            
            assert event.progress == 0.5
            assert event.total_files == 10
        except ImportError:
            pytest.skip("PySide6 not available")
    
    def test_event_bus_subscribe_unsubscribe(self):
        """Test EventBus subscribe/unsubscribe."""
        try:
            from ui_new.events import EventBus, EventType
            
            callback_called = []
            
            def callback(event_dict):
                callback_called.append(event_dict)
            
            # Subscribe
            EventBus.subscribe(EventType.FILE_LOADED, callback)
            
            # Check subscriber count
            count = EventBus.subscriber_count(EventType.FILE_LOADED)
            assert count >= 1
            
            # Unsubscribe
            EventBus.unsubscribe(EventType.FILE_LOADED, callback)
            
            count = EventBus.subscriber_count(EventType.FILE_LOADED)
            assert count == 0
        except ImportError:
            pytest.skip("PySide6 not available")
    
    def test_event_bus_publish_sync(self):
        """Test EventBus synchronous publishing."""
        try:
            from ui_new.events import EventBus, EventType, FileEvent
            
            received_events = []
            
            def callback(event_dict):
                received_events.append(event_dict)
            
            EventBus.subscribe(EventType.FILE_LOADED, callback)
            
            # Publish event
            event = FileEvent(
                type=EventType.FILE_LOADED,
                path="/test/file.wav",
            )
            EventBus.publish_sync(event)
            
            # Check event was received
            assert len(received_events) == 1
            assert received_events[0]["path"] == "/test/file.wav"
            
            # Cleanup
            EventBus.unsubscribe(EventType.FILE_LOADED, callback)
        except ImportError:
            pytest.skip("PySide6 not available")
    
    def test_event_bus_clear_subscribers(self):
        """Test clearing all subscribers."""
        try:
            from ui_new.events import EventBus, EventType
            
            def dummy_callback(event_dict):
                pass
            
            EventBus.subscribe(EventType.FILE_LOADED, dummy_callback)
            EventBus.subscribe(EventType.PROCESSING_STARTED, dummy_callback)
            
            # Clear all
            EventBus.clear_subscribers()
            
            assert EventBus.subscriber_count() == 0
        except ImportError:
            pytest.skip("PySide6 not available")


# =============================================================================
# REPOSITORY TESTS
# =============================================================================

class TestRepositories:
    """Tests for Repository Pattern."""
    
    def test_import_repositories(self):
        """Test that repositories can be imported."""
        from ui_new.repositories import (
            BaseRepository,
            JsonRepository,
            ProfileRepository,
            SettingsRepository,
            HistoryRepository,
            SessionRepository,
            RepositoryFactory,
        )
        
        assert BaseRepository is not None
        assert JsonRepository is not None
        assert ProfileRepository is not None
    
    def test_json_repository_basic(self, temp_dir):
        """Test basic JsonRepository operations."""
        from ui_new.repositories import JsonRepository
        
        repo = JsonRepository(temp_dir / "test_repo")
        
        # Save
        repo.save("test1", {"name": "Test", "value": 42})
        
        # Get
        data = repo.get("test1")
        assert data is not None
        assert data["name"] == "Test"
        assert data["value"] == 42
        
        # Exists
        assert repo.exists("test1")
        assert not repo.exists("nonexistent")
        
        # Delete
        assert repo.delete("test1")
        assert not repo.exists("test1")
    
    def test_json_repository_get_all(self, temp_dir):
        """Test JsonRepository get_all."""
        from ui_new.repositories import JsonRepository
        
        repo = JsonRepository(temp_dir / "test_repo2")
        
        repo.save("item1", {"id": 1})
        repo.save("item2", {"id": 2})
        repo.save("item3", {"id": 3})
        
        all_items = repo.get_all()
        
        assert len(all_items) == 3
        assert "item1" in all_items
        assert "item2" in all_items
        assert "item3" in all_items
    
    def test_profile_repository_builtin(self, temp_dir):
        """Test ProfileRepository with built-in profiles."""
        from ui_new.repositories import ProfileRepository
        
        repo = ProfileRepository(temp_dir / "profiles")
        
        # Check built-in profiles
        standard = repo.get("standard")
        assert standard is not None
        assert standard["name"] == "standard"
        
        # Get all should include built-in
        all_profiles = repo.get_all()
        assert "standard" in all_profiles
        assert "fast" in all_profiles
        assert "quality" in all_profiles
    
    def test_profile_repository_cannot_delete_builtin(self, temp_dir):
        """Test that built-in profiles cannot be deleted."""
        try:
            from ui_new.repositories import ProfileRepository
            
            repo = ProfileRepository(temp_dir / "profiles2")
            
            # Try to delete built-in
            result = repo.delete("standard")
            assert result is False
            
            # Profile should still exist
            assert repo.exists("standard")
        except ImportError:
            pytest.skip("Required dependencies not available")
    
    def test_settings_repository(self, temp_dir):
        """Test SettingsRepository."""
        from ui_new.repositories import SettingsRepository
        
        repo = SettingsRepository(temp_dir / "settings")
        
        # Get setting with default
        theme = repo.get_setting("theme")
        assert theme is not None
        
        # Set setting
        repo.set_setting("theme", "dark")
        
        # Get updated setting
        theme = repo.get_setting("theme")
        assert theme == "dark"
    
    def test_history_repository(self, temp_dir):
        """Test HistoryRepository."""
        from ui_new.repositories import HistoryRepository
        
        repo = HistoryRepository(temp_dir / "history", max_entries=10)
        
        # Add entry
        entry_id = repo.add_entry(
            source_file="/test/source.wav",
            output_file="/test/output.mp3",
            method="fwht",
            metrics={"snr": 30.0},
            settings={"block_size": 2048},
        )
        
        assert entry_id is not None
        
        # Get entry
        entry = repo.get(entry_id)
        assert entry is not None
        assert entry["method"] == "fwht"
    
    def test_session_repository(self, temp_dir):
        """Test SessionRepository."""
        from ui_new.repositories import SessionRepository
        
        repo = SessionRepository(temp_dir / "sessions")
        
        # Save session
        repo.save_current_session(
            open_files=["/test/file1.wav", "/test/file2.wav"],
            results=[{"variant": "fwht", "score": 0.9}],
            current_profile="quality",
            settings={"theme": "dark"},
        )
        
        # Load session
        session = repo.load_current_session()
        assert session is not None
        assert session["current_profile"] == "quality"
        assert len(session["open_files"]) == 2
    
    def test_repository_factory(self, temp_dir):
        """Test RepositoryFactory."""
        from ui_new.repositories import RepositoryFactory
        
        RepositoryFactory.initialize(temp_dir / "factory_data")
        
        # Get repositories
        profile_repo = RepositoryFactory.get_profile_repository()
        settings_repo = RepositoryFactory.get_settings_repository()
        history_repo = RepositoryFactory.get_history_repository()
        session_repo = RepositoryFactory.get_session_repository()
        
        assert profile_repo is not None
        assert settings_repo is not None
        assert history_repo is not None
        assert session_repo is not None
        
        # Clear
        RepositoryFactory.clear_all()


# =============================================================================
# PIPELINE TESTS
# =============================================================================

class TestPipeline:
    """Tests for Pipeline Pattern."""
    
    def test_import_pipeline(self):
        """Test that pipeline can be imported."""
        from ui_new.pipeline import (
            AudioPipeline,
            PipelineStep,
            PipelineContext,
            PipelineStatus,
            PipelineFactory,
        )
        
        assert AudioPipeline is not None
        assert PipelineStep is not None
        assert PipelineContext is not None
    
    def test_pipeline_context(self):
        """Test PipelineContext."""
        from ui_new.pipeline import PipelineContext, PipelineStatus
        
        context = PipelineContext(
            source_path="/test/file.wav",
            output_dir="/test/output",
        )
        
        assert context.source_path == "/test/file.wav"
        assert context.status == PipelineStatus.PENDING
    
    def test_pipeline_context_progress(self):
        """Test PipelineContext progress callback."""
        from ui_new.pipeline import PipelineContext
        
        progress_values = []
        
        def callback(progress, message):
            progress_values.append((progress, message))
        
        context = PipelineContext(progress_callback=callback)
        
        context.update_progress(0.5, "Processing...")
        
        assert len(progress_values) == 1
        assert progress_values[0][0] == 0.5
    
    def test_pipeline_context_to_dict(self):
        """Test PipelineContext serialization."""
        from ui_new.pipeline import PipelineContext
        
        context = PipelineContext(
            source_path="/test/file.wav",
            output_dir="/test/output",
            method="fwht",
        )
        
        d = context.to_dict()
        
        assert d["source_path"] == "/test/file.wav"
        assert d["method"] == "fwht"
    
    def test_audio_pipeline_create(self):
        """Test creating AudioPipeline."""
        from ui_new.pipeline import AudioPipeline
        
        pipeline = AudioPipeline("test_pipeline")
        
        assert pipeline.name == "test_pipeline"
        assert len(pipeline.steps) == 0
    
    def test_audio_pipeline_add_steps(self):
        """Test adding steps to pipeline."""
        from ui_new.pipeline import AudioPipeline, LoadStep, MetricsStep
        
        pipeline = AudioPipeline("test")
        
        pipeline.add_step(LoadStep())
        pipeline.add_step(MetricsStep())
        
        assert len(pipeline.steps) == 2
    
    def test_pipeline_factory(self):
        """Test PipelineFactory."""
        from ui_new.pipeline import PipelineFactory
        
        # Create analysis pipeline
        pipeline = PipelineFactory.create_analysis_pipeline("fwht")
        
        assert pipeline is not None
        assert len(pipeline.steps) > 0
    
    def test_pipeline_factory_batch(self):
        """Test PipelineFactory batch creation."""
        from ui_new.pipeline import PipelineFactory
        
        pipelines = PipelineFactory.create_batch_pipeline(["fwht", "fft", "standard"])
        
        assert len(pipelines) == 3
    
    def test_pipeline_factory_quick(self):
        """Test PipelineFactory quick pipeline."""
        from ui_new.pipeline import PipelineFactory
        
        pipeline = PipelineFactory.create_quick_pipeline()
        
        assert pipeline is not None
    
    def test_load_step_properties(self):
        """Test LoadStep properties."""
        from ui_new.pipeline import LoadStep
        
        step = LoadStep()
        
        assert step.name == "load"
        assert step.weight > 0
    
    def test_transform_step_properties(self):
        """Test TransformStep properties."""
        from ui_new.pipeline import TransformStep
        
        step = TransformStep("fwht")
        
        assert step.name == "transform"
        assert step.method == "fwht"
    
    def test_metrics_step_properties(self):
        """Test MetricsStep properties."""
        from ui_new.pipeline import MetricsStep
        
        step = MetricsStep()
        
        assert step.name == "metrics"
        assert step.weight > 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestArchitecturalIntegration:
    """Integration tests for architectural components."""
    
    def test_event_bus_with_pipeline(self):
        """Test EventBus integration with Pipeline."""
        try:
            from ui_new.events import EventBus, EventType, ProcessingEvent
            from ui_new.pipeline import PipelineContext, PipelineStatus
            
            events_received = []
            
            def event_handler(event_dict):
                events_received.append(event_dict)
            
            # Subscribe to processing events
            EventBus.subscribe(EventType.PROCESSING_STARTED, event_handler)
            EventBus.subscribe(EventType.PROCESSING_FINISHED, event_handler)
            
            # Create context
            context = PipelineContext(
                source_path="/test/file.wav",
                status=PipelineStatus.RUNNING,
            )
            
            # Emit events
            EventBus.publish_sync(ProcessingEvent(
                type=EventType.PROCESSING_STARTED,
                file_path="/test/file.wav",
                total_files=1,
            ))
            
            # Check event received
            assert len(events_received) == 1
            
            # Cleanup
            EventBus.unsubscribe(EventType.PROCESSING_STARTED, event_handler)
            EventBus.unsubscribe(EventType.PROCESSING_FINISHED, event_handler)
        except ImportError:
            pytest.skip("PySide6 not available")
    
    def test_repository_with_events(self, temp_dir):
        """Test Repository integration with Events."""
        try:
            from ui_new.repositories import ProfileRepository
            from ui_new.events import EventBus, EventType, ProfileEvent
            
            events = []
            
            def handler(event_dict):
                events.append(event_dict)
            
            EventBus.subscribe(EventType.PROFILE_CHANGED, handler)
            
            repo = ProfileRepository(temp_dir / "profiles_test")
            
            # Save custom profile
            repo.save("custom_test", {
                "name": "custom_test",
                "display_name": "Custom Test",
                "settings": {"block_size": 4096},
            })
            
            # Emit event
            EventBus.publish_sync(ProfileEvent(
                type=EventType.PROFILE_CHANGED,
                profile_name="custom_test",
            ))
            
            assert len(events) == 1
            
            # Cleanup
            EventBus.unsubscribe(EventType.PROFILE_CHANGED, handler)
        except ImportError:
            pytest.skip("PySide6 not available")
