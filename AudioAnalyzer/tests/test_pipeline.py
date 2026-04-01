"""
Tests for Pipeline Pattern implementation.

Tests verify:
- PipelineContext data handling
- PipelineStep abstract interface
- Built-in steps (LoadStep, TransformStep, MetricsStep, EncodeStep)
- AudioPipeline execution
- PipelineFactory configuration
"""
import asyncio
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPipelineStatus:
    """Tests for PipelineStatus enum."""
    
    def test_status_values(self):
        """Test that all status values are defined."""
        from ui_new.pipeline import PipelineStatus
        
        assert PipelineStatus.PENDING
        assert PipelineStatus.RUNNING
        assert PipelineStatus.COMPLETED
        assert PipelineStatus.FAILED
        assert PipelineStatus.CANCELLED
    
    def test_status_unique_values(self):
        """Test that all status values are unique."""
        from ui_new.pipeline import PipelineStatus
        
        values = [s.value for s in PipelineStatus]
        assert len(values) == len(set(values))


class TestPipelineContext:
    """Tests for PipelineContext dataclass."""
    
    def test_default_values(self):
        """Test default context values."""
        from ui_new.pipeline import PipelineContext, PipelineStatus
        
        ctx = PipelineContext()
        
        assert ctx.source_path == ""
        assert ctx.output_dir == ""
        assert ctx.audio_data is None
        assert ctx.sample_rate == 44100
        assert ctx.channels == 1
        assert ctx.progress == 0.0
        assert ctx.status == PipelineStatus.PENDING
    
    def test_custom_values(self):
        """Test context with custom values."""
        from ui_new.pipeline import PipelineContext, PipelineStatus
        
        ctx = PipelineContext(
            source_path="/path/to/file.wav",
            output_dir="/output",
            sample_rate=48000,
            settings={"block_size": 4096},
        )
        
        assert ctx.source_path == "/path/to/file.wav"
        assert ctx.sample_rate == 48000
        assert ctx.settings["block_size"] == 4096
    
    def test_update_progress(self):
        """Test progress update with callback."""
        from ui_new.pipeline import PipelineContext
        
        callback = Mock()
        ctx = PipelineContext(progress_callback=callback)
        
        ctx.update_progress(0.5, "Processing...")
        
        assert ctx.progress == 0.5
        callback.assert_called_once_with(0.5, "Processing...")
    
    def test_update_progress_bounds(self):
        """Test progress is bounded to [0, 1]."""
        from ui_new.pipeline import PipelineContext
        
        ctx = PipelineContext()
        
        ctx.update_progress(-0.5)
        assert ctx.progress == 0.0
        
        ctx.update_progress(1.5)
        assert ctx.progress == 1.0
    
    def test_to_dict(self):
        """Test context serialization."""
        from ui_new.pipeline import PipelineContext
        
        ctx = PipelineContext(
            source_path="/path/file.wav",
            output_dir="/output",
            sample_rate=44100,
            method="fwht",
            metrics={"snr_db": 1.5},
        )
        
        d = ctx.to_dict()
        
        assert d["source_path"] == "/path/file.wav"
        assert d["sample_rate"] == 44100
        assert d["method"] == "fwht"
        assert d["metrics"]["snr_db"] == 1.5
        assert "status" in d


class TestPipelineStep:
    """Tests for PipelineStep abstract class."""
    
    def test_is_abstract(self):
        """Test that PipelineStep cannot be instantiated directly."""
        from ui_new.pipeline import PipelineStep
        
        with pytest.raises(TypeError):
            PipelineStep()
    
    def test_default_methods(self):
        """Test default method implementations."""
        from ui_new.pipeline import PipelineStep, PipelineContext, PipelineStatus
        
        # Create concrete implementation
        class TestStep(PipelineStep):
            @property
            def name(self):
                return "test"
            
            def execute(self, context):
                return context
        
        step = TestStep()
        ctx = PipelineContext()
        ctx.status = PipelineStatus.RUNNING
        
        assert step.name == "test"
        assert step.description == ""
        assert step.weight == 1.0
        assert step.can_execute(ctx) is True
    
    def test_on_error(self):
        """Test error handling."""
        from ui_new.pipeline import PipelineStep, PipelineContext, PipelineStatus
        
        class TestStep(PipelineStep):
            @property
            def name(self):
                return "test"
            
            def execute(self, context):
                return context
        
        step = TestStep()
        ctx = PipelineContext()
        ctx.status = PipelineStatus.RUNNING
        
        error = Exception("Test error")
        result = step.on_error(ctx, error)
        
        assert result.status == PipelineStatus.FAILED
        assert "Test error" in result.error_message


class TestLoadStep:
    """Tests for LoadStep."""
    
    def test_step_properties(self):
        """Test LoadStep properties."""
        from ui_new.pipeline import LoadStep
        
        step = LoadStep()
        
        assert step.name == "load"
        assert "загрузк" in step.description.lower()
        assert step.weight == 0.1


class TestTransformStep:
    """Tests for TransformStep."""
    
    def test_default_method(self):
        """Test default method is fwht."""
        from ui_new.pipeline import TransformStep
        
        step = TransformStep()
        
        assert step.method == "fwht"
    
    def test_custom_method(self):
        """Test custom method."""
        from ui_new.pipeline import TransformStep
        
        step = TransformStep(method="fft")
        
        assert step.method == "fft"
        assert "FFT" in step.description
    
    def test_step_properties(self):
        """Test TransformStep properties."""
        from ui_new.pipeline import TransformStep
        
        step = TransformStep("dct")
        
        assert step.name == "transform"
        assert step.weight == 0.5


class TestMetricsStep:
    """Tests for MetricsStep."""
    
    def test_step_properties(self):
        """Test MetricsStep properties."""
        from ui_new.pipeline import MetricsStep
        
        step = MetricsStep()
        
        assert step.name == "metrics"
        assert "метрик" in step.description.lower()
        assert step.weight == 0.3


class TestEncodeStep:
    """Tests for EncodeStep."""
    
    def test_default_bitrate(self):
        """Test default bitrate."""
        from ui_new.pipeline import EncodeStep
        
        step = EncodeStep()
        
        assert step.name == "encode"
        assert step.weight == 0.1
    
    def test_custom_bitrate(self):
        """Test custom bitrate."""
        from ui_new.pipeline import EncodeStep
        
        step = EncodeStep(bitrate="320k")
        
        assert step.name == "encode"


class TestAudioPipeline:
    """Tests for AudioPipeline."""
    
    def test_pipeline_creation(self):
        """Test creating a pipeline."""
        from ui_new.pipeline import AudioPipeline
        
        pipeline = AudioPipeline("test")
        
        assert pipeline.name == "test"
        assert len(pipeline.steps) == 0
    
    def test_add_step(self):
        """Test adding steps."""
        from ui_new.pipeline import AudioPipeline, LoadStep
        
        pipeline = AudioPipeline()
        step = LoadStep()
        
        result = pipeline.add_step(step)
        
        assert result is pipeline  # Returns self for chaining
        assert len(pipeline.steps) == 1
    
    def test_add_steps(self):
        """Test adding multiple steps."""
        from ui_new.pipeline import AudioPipeline, LoadStep, MetricsStep
        
        pipeline = AudioPipeline()
        
        pipeline.add_steps(LoadStep(), MetricsStep())
        
        assert len(pipeline.steps) == 2
    
    def test_clear_steps(self):
        """Test clearing steps."""
        from ui_new.pipeline import AudioPipeline, LoadStep
        
        pipeline = AudioPipeline()
        pipeline.add_step(LoadStep())
        
        pipeline.clear_steps()
        
        assert len(pipeline.steps) == 0
    
    def test_cancel(self):
        """Test pipeline cancellation."""
        from ui_new.pipeline import AudioPipeline, PipelineContext, PipelineStatus
        
        pipeline = AudioPipeline()
        ctx = PipelineContext()
        
        pipeline.cancel()
        
        assert pipeline._cancelled is True


class TestPipelineFactory:
    """Tests for PipelineFactory."""
    
    def test_create_analysis_pipeline(self):
        """Test creating analysis pipeline."""
        from ui_new.pipeline import PipelineFactory, AudioPipeline
        
        pipeline = PipelineFactory.create_analysis_pipeline("fwht")
        
        assert isinstance(pipeline, AudioPipeline)
        assert "fwht" in pipeline.name
        assert len(pipeline.steps) == 3  # Load, Transform, Metrics
    
    def test_create_batch_pipelines(self):
        """Test creating batch pipelines."""
        from ui_new.pipeline import PipelineFactory
        
        pipelines = PipelineFactory.create_batch_pipeline(["fwht", "fft"])
        
        assert len(pipelines) == 2
    
    def test_create_quick_pipeline(self):
        """Test creating quick pipeline."""
        from ui_new.pipeline import PipelineFactory
        
        pipeline = PipelineFactory.create_quick_pipeline()
        
        assert pipeline.name == "quick"
    
    def test_create_quality_pipeline(self):
        """Test creating quality pipeline."""
        from ui_new.pipeline import PipelineFactory
        
        pipeline = PipelineFactory.create_quality_pipeline()
        
        assert pipeline.name == "quality"
        assert len(pipeline.steps) == 3


class TestExports:
    """Tests for module exports."""
    
    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        from ui_new.pipeline import __all__
        
        expected = [
            "PipelineStatus",
            "PipelineContext",
            "PipelineStep",
            "LoadStep",
            "TransformStep",
            "MetricsStep",
            "EncodeStep",
            "AudioPipeline",
            "PipelineFactory",
        ]
        
        for export in expected:
            assert export in __all__
