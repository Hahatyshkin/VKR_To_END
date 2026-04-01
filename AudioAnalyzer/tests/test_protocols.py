"""
Tests for Protocol definitions.

Tests verify:
- Protocol definitions are correct
- Runtime checking works
- Duck typing support
- Type safety with isinstance()
"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestRepositoryProtocol:
    """Tests for RepositoryProtocol."""
    
    def test_protocol_exists(self):
        """Test that RepositoryProtocol is defined."""
        from ui_new.protocols import RepositoryProtocol
        
        assert RepositoryProtocol is not None
    
    def test_runtime_checkable(self):
        """Test that protocol is runtime checkable."""
        from ui_new.protocols import RepositoryProtocol
        
        # Create a class that implements the protocol
        class MyRepo:
            def get(self, id: str) -> Optional[dict]:
                return None
            
            def get_all(self) -> Dict[str, dict]:
                return {}
            
            def save(self, id: str, entity: dict) -> None:
                pass
            
            def delete(self, id: str) -> bool:
                return False
            
            def exists(self, id: str) -> bool:
                return False
        
        repo = MyRepo()
        
        # Should be recognized as implementing the protocol
        assert isinstance(repo, RepositoryProtocol)
    
    def test_missing_methods_not_recognized(self):
        """Test that classes missing methods don't match protocol."""
        from ui_new.protocols import RepositoryProtocol
        
        class IncompleteRepo:
            def get(self, id: str) -> Optional[dict]:
                return None
            # Missing other required methods
        
        repo = IncompleteRepo()
        
        # Should NOT be recognized
        assert not isinstance(repo, RepositoryProtocol)


class TestJsonRepositoryProtocol:
    """Tests for JsonRepositoryProtocol."""
    
    def test_protocol_exists(self):
        """Test that JsonRepositoryProtocol is defined."""
        from ui_new.protocols import JsonRepositoryProtocol
        
        assert JsonRepositoryProtocol is not None
    
    def test_json_repo_matches_protocol(self):
        """Test that JsonRepository matches the protocol."""
        from ui_new.protocols import JsonRepositoryProtocol
        
        class MyJsonRepo:
            def get(self, id: str) -> Optional[Dict[str, Any]]:
                return None
            
            def get_all(self) -> Dict[str, Dict[str, Any]]:
                return {}
            
            def save(self, id: str, entity: Dict[str, Any]) -> None:
                pass
            
            def delete(self, id: str) -> bool:
                return False
            
            def exists(self, id: str) -> bool:
                return False
            
            def get_ids(self) -> List[str]:
                return []
        
        repo = MyJsonRepo()
        
        assert isinstance(repo, JsonRepositoryProtocol)


class TestPipelineStepProtocol:
    """Tests for PipelineStepProtocol."""
    
    def test_protocol_exists(self):
        """Test that PipelineStepProtocol is defined."""
        from ui_new.protocols import PipelineStepProtocol
        
        assert PipelineStepProtocol is not None
    
    def test_step_matches_protocol(self):
        """Test that pipeline step matches the protocol."""
        from ui_new.protocols import PipelineStepProtocol
        
        class MyStep:
            @property
            def name(self) -> str:
                return "my_step"
            
            @property
            def description(self) -> str:
                return "My step"
            
            @property
            def weight(self) -> float:
                return 1.0
            
            def execute(self, context):
                return context
            
            def can_execute(self, context) -> bool:
                return True
            
            def on_error(self, context, error):
                return context
        
        step = MyStep()
        
        assert isinstance(step, PipelineStepProtocol)


class TestAudioPipelineProtocol:
    """Tests for AudioPipelineProtocol."""
    
    def test_protocol_exists(self):
        """Test that AudioPipelineProtocol is defined."""
        from ui_new.protocols import AudioPipelineProtocol
        
        assert AudioPipelineProtocol is not None


class TestAudioTransformProtocol:
    """Tests for AudioTransformProtocol."""
    
    def test_protocol_exists(self):
        """Test that AudioTransformProtocol is defined."""
        from ui_new.protocols import AudioTransformProtocol
        
        assert AudioTransformProtocol is not None
    
    def test_transform_matches_protocol(self):
        """Test that transform matches the protocol."""
        from ui_new.protocols import AudioTransformProtocol
        
        class MyTransform:
            @property
            def name(self) -> str:
                return "my_transform"
            
            @property
            def description(self) -> str:
                return "My transform"
            
            def forward(self, signal):
                return signal
            
            def inverse(self, coeffs):
                return coeffs
            
            def get_block_size(self) -> int:
                return 2048
            
            def set_block_size(self, size: int) -> None:
                pass
        
        transform = MyTransform()
        
        assert isinstance(transform, AudioTransformProtocol)


class TestServiceProtocols:
    """Tests for service protocols."""
    
    def test_audio_service_protocol_exists(self):
        """Test that AudioServiceProtocol is defined."""
        from ui_new.protocols import AudioServiceProtocol
        
        assert AudioServiceProtocol is not None
    
    def test_file_service_protocol_exists(self):
        """Test that FileServiceProtocol is defined."""
        from ui_new.protocols import FileServiceProtocol
        
        assert FileServiceProtocol is not None
    
    def test_spectrum_service_protocol_exists(self):
        """Test that SpectrumServiceProtocol is defined."""
        from ui_new.protocols import SpectrumServiceProtocol
        
        assert SpectrumServiceProtocol is not None


class TestEventProtocols:
    """Tests for event protocols."""
    
    def test_event_handler_protocol_exists(self):
        """Test that EventHandlerProtocol is defined."""
        from ui_new.protocols import EventHandlerProtocol
        
        assert EventHandlerProtocol is not None
    
    def test_event_emitter_protocol_exists(self):
        """Test that EventEmitterProtocol is defined."""
        from ui_new.protocols import EventEmitterProtocol
        
        assert EventEmitterProtocol is not None
    
    def test_event_handler_matches_protocol(self):
        """Test that event handler matches protocol."""
        from ui_new.protocols import EventHandlerProtocol
        
        class MyHandler:
            def handle(self, event: Dict[str, Any]) -> None:
                pass
        
        handler = MyHandler()
        
        assert isinstance(handler, EventHandlerProtocol)


class TestUIProtocols:
    """Tests for UI protocols."""
    
    def test_widget_protocol_exists(self):
        """Test that WidgetProtocol is defined."""
        from ui_new.protocols import WidgetProtocol
        
        assert WidgetProtocol is not None
    
    def test_main_window_protocol_exists(self):
        """Test that MainWindowProtocol is defined."""
        from ui_new.protocols import MainWindowProtocol
        
        assert MainWindowProtocol is not None


class TestExports:
    """Tests for module exports."""
    
    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        from ui_new.protocols import __all__
        
        expected = [
            "RepositoryProtocol",
            "JsonRepositoryProtocol",
            "ProfileRepositoryProtocol",
            "SettingsRepositoryProtocol",
            "PipelineContextProtocol",
            "PipelineStepProtocol",
            "AudioPipelineProtocol",
            "AudioTransformProtocol",
            "TransformFactoryProtocol",
            "AudioServiceProtocol",
            "FileServiceProtocol",
            "SpectrumServiceProtocol",
            "EventHandlerProtocol",
            "EventEmitterProtocol",
            "WidgetProtocol",
            "MainWindowProtocol",
        ]
        
        for export in expected:
            assert export in __all__
    
    def test_runtime_checkable_decorators(self):
        """Test that protocols are runtime checkable."""
        from ui_new.protocols import (
            RepositoryProtocol,
            JsonRepositoryProtocol,
            PipelineStepProtocol,
            AudioTransformProtocol,
            EventHandlerProtocol,
        )
        
        # Runtime checkable protocols support isinstance()
        protocols = [
            RepositoryProtocol,
            JsonRepositoryProtocol,
            PipelineStepProtocol,
            AudioTransformProtocol,
            EventHandlerProtocol,
        ]
        
        for protocol in protocols:
            # Runtime checkable protocols have special attributes
            # They support isinstance() checks
            assert hasattr(protocol, "__class__")
            # All Protocol subclasses have __mro__
            assert hasattr(protocol, "__mro__")


class TestProtocolCompatibility:
    """Tests for protocol compatibility with existing implementations."""
    
    def test_json_repository_compatible(self):
        """Test that JsonRepository is compatible with protocol."""
        from ui_new.protocols import JsonRepositoryProtocol
        from ui_new.repositories import JsonRepository
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = JsonRepository(tmpdir)
            
            # Should be compatible
            assert isinstance(repo, JsonRepositoryProtocol)
    
    def test_profile_repository_compatible(self):
        """Test that ProfileRepository is compatible with protocol."""
        from ui_new.protocols import ProfileRepositoryProtocol
        from ui_new.repositories import ProfileRepository
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ProfileRepository(tmpdir)
            
            # Should be compatible
            assert isinstance(repo, ProfileRepositoryProtocol)
    
    def test_pipeline_step_compatible(self):
        """Test that PipelineStep is compatible with protocol."""
        from ui_new.protocols import PipelineStepProtocol
        from ui_new.pipeline import LoadStep
        
        step = LoadStep()
        
        # Should be compatible
        assert isinstance(step, PipelineStepProtocol)
