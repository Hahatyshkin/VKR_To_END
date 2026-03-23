"""
Pipeline Pattern for audio processing.

Provides:
- Chain of responsibility for audio processing steps
- Configurable processing pipelines
- Progress reporting and cancellation support
- Parallel processing capabilities

Usage:
------
>>> from ui_new.pipeline import AudioPipeline, LoadStep, TransformStep, EncodeStep
>>> 
>>> pipeline = AudioPipeline()
>>> pipeline.add_step(LoadStep())
>>> pipeline.add_step(TransformStep(method="fwht"))
>>> pipeline.add_step(EncodeStep(bitrate="192k"))
>>> 
>>> result = await pipeline.execute("/path/to/file.wav", "/output/dir")
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("ui_new.pipeline")


# =============================================================================
# PIPELINE CONTEXT
# =============================================================================

class PipelineStatus(Enum):
    """Status of pipeline execution."""
    
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class PipelineContext:
    """Context passed between pipeline steps.
    
    Holds all state for a single pipeline execution:
    - Input/output paths
    - Audio data (loaded and processed)
    - Processing settings
    - Progress and error information
    """
    
    # Input/Output
    source_path: str = ""
    output_dir: str = ""
    output_path: str = ""
    
    # Audio data
    audio_data: Optional[Any] = None  # numpy array
    sample_rate: int = 44100
    channels: int = 1
    
    # Processing state
    current_step: str = ""
    step_index: int = 0
    total_steps: int = 0
    progress: float = 0.0  # 0.0 to 1.0
    
    # Settings
    settings: Dict[str, Any] = field(default_factory=dict)
    method: str = "standard"
    
    # Results
    metrics: Dict[str, float] = field(default_factory=dict)
    processing_time: float = 0.0
    
    # Status
    status: PipelineStatus = PipelineStatus.PENDING
    error_message: str = ""
    
    # Metadata
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    # Callbacks
    progress_callback: Optional[Callable[[float, str], None]] = None
    
    def update_progress(self, progress: float, message: str = "") -> None:
        """Update progress and call callback."""
        self.progress = max(0.0, min(1.0, progress))
        
        if self.progress_callback:
            try:
                self.progress_callback(self.progress, message)
            except Exception as e:
                logger.error("Progress callback error: %s", e)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "source_path": self.source_path,
            "output_dir": self.output_dir,
            "output_path": self.output_path,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "current_step": self.current_step,
            "step_index": self.step_index,
            "total_steps": self.total_steps,
            "progress": self.progress,
            "settings": self.settings,
            "method": self.method,
            "metrics": self.metrics,
            "processing_time": self.processing_time,
            "status": self.status.name,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


# =============================================================================
# PIPELINE STEP
# =============================================================================

class PipelineStep(ABC):
    """Abstract base class for pipeline steps.
    
    Each step performs a single operation in the processing pipeline.
    Steps are executed in order and can modify the context.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Step name for display and logging."""
        pass
    
    @property
    def description(self) -> str:
        """Step description."""
        return ""
    
    @property
    def weight(self) -> float:
        """Relative weight for progress calculation (0.0 to 1.0)."""
        return 1.0
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute the step.
        
        Parameters
        ----------
        context : PipelineContext
            Current pipeline context
            
        Returns
        -------
        PipelineContext
            Updated context after step execution
        """
        pass
    
    def can_execute(self, context: PipelineContext) -> bool:
        """Check if step can execute with current context."""
        return context.status == PipelineStatus.RUNNING
    
    def on_error(self, context: PipelineContext, error: Exception) -> PipelineContext:
        """Handle step error."""
        context.status = PipelineStatus.FAILED
        context.error_message = f"{self.name}: {str(error)}"
        logger.error("Pipeline step %s failed: %s", self.name, error)
        return context


# =============================================================================
# BUILT-IN STEPS
# =============================================================================

class LoadStep(PipelineStep):
    """Step for loading audio files."""
    
    @property
    def name(self) -> str:
        return "load"
    
    @property
    def description(self) -> str:
        return "Загрузка аудиофайла"
    
    @property
    def weight(self) -> float:
        return 0.1
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Load audio file into context."""
        from processing.codecs import load_wav_mono, decode_audio_to_mono
        
        context.current_step = self.name
        context.update_progress(0.0, "Загрузка файла...")
        
        try:
            source_path = Path(context.source_path)
            
            if source_path.suffix.lower() == ".wav":
                audio_data, sample_rate = load_wav_mono(str(source_path))
            else:
                audio_data, sample_rate = decode_audio_to_mono(str(source_path))
            
            context.audio_data = audio_data
            context.sample_rate = sample_rate
            context.channels = 1
            
            context.update_progress(1.0, f"Загружено: {len(audio_data)} сэмплов")
            
            logger.debug(
                "Loaded audio: %s, sr=%d, len=%d",
                source_path.name, sample_rate, len(audio_data)
            )
            
        except Exception as e:
            return self.on_error(context, e)
        
        return context


class TransformStep(PipelineStep):
    """Step for audio transformation."""
    
    def __init__(self, method: str = "fwht"):
        self._method = method
    
    @property
    def name(self) -> str:
        return "transform"
    
    @property
    def description(self) -> str:
        return f"Преобразование: {self._method.upper()}"
    
    @property
    def weight(self) -> float:
        return 0.5
    
    @property
    def method(self) -> str:
        return self._method
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Apply transformation to audio."""
        context.current_step = self.name
        context.method = self._method
        
        def progress_cb(frac: float, msg: str):
            context.update_progress(frac, msg)
        
        try:
            from processing import audio_ops
            
            method = self._method.lower()
            
            if method == "fwht":
                output_path, time_sec = audio_ops.fwht_transform_and_mp3(
                    context.source_path,
                    context.output_dir,
                    block_size=context.settings.get("block_size", 2048),
                    select_mode=context.settings.get("select_mode", "none"),
                    keep_energy_ratio=context.settings.get("keep_energy_ratio", 1.0),
                    sequency_keep_ratio=context.settings.get("sequency_keep_ratio", 1.0),
                    bitrate=context.settings.get("bitrate", "192k"),
                    progress_cb=progress_cb,
                )
            elif method == "fft":
                output_path, time_sec = audio_ops.fft_transform_and_mp3(
                    context.source_path,
                    context.output_dir,
                    block_size=context.settings.get("block_size", 2048),
                    select_mode=context.settings.get("select_mode", "none"),
                    keep_energy_ratio=context.settings.get("keep_energy_ratio", 1.0),
                    sequency_keep_ratio=context.settings.get("sequency_keep_ratio", 1.0),
                    bitrate=context.settings.get("bitrate", "192k"),
                    progress_cb=progress_cb,
                )
            elif method == "dct":
                output_path, time_sec = audio_ops.dct_transform_and_mp3(
                    context.source_path,
                    context.output_dir,
                    block_size=context.settings.get("block_size", 2048),
                    select_mode=context.settings.get("select_mode", "none"),
                    keep_energy_ratio=context.settings.get("keep_energy_ratio", 1.0),
                    sequency_keep_ratio=context.settings.get("sequency_keep_ratio", 1.0),
                    bitrate=context.settings.get("bitrate", "192k"),
                    progress_cb=progress_cb,
                )
            elif method == "dwt":
                output_path, time_sec = audio_ops.wavelet_transform_and_mp3(
                    context.source_path,
                    context.output_dir,
                    block_size=context.settings.get("block_size", 2048),
                    select_mode=context.settings.get("select_mode", "none"),
                    keep_energy_ratio=context.settings.get("keep_energy_ratio", 1.0),
                    sequency_keep_ratio=context.settings.get("sequency_keep_ratio", 1.0),
                    levels=context.settings.get("levels", 4),
                    bitrate=context.settings.get("bitrate", "192k"),
                    progress_cb=progress_cb,
                )
            elif method == "huffman":
                output_path, time_sec = audio_ops.huffman_like_transform_and_mp3(
                    context.source_path,
                    context.output_dir,
                    block_size=context.settings.get("block_size", 2048),
                    bitrate=context.settings.get("bitrate", "192k"),
                    mu=context.settings.get("mu", 255.0),
                    bits=context.settings.get("bits", 8),
                    progress_cb=progress_cb,
                )
            elif method == "rosenbrock":
                output_path, time_sec = audio_ops.rosenbrock_like_transform_and_mp3(
                    context.source_path,
                    context.output_dir,
                    alpha=context.settings.get("rosen_alpha", 0.2),
                    beta=context.settings.get("rosen_beta", 1.0),
                    bitrate=context.settings.get("bitrate", "192k"),
                    progress_cb=progress_cb,
                )
            elif method == "standard":
                output_path, time_sec = audio_ops.standard_convert_to_mp3(
                    context.source_path,
                    context.output_dir,
                    bitrate=context.settings.get("bitrate", "192k"),
                )
            else:
                raise ValueError(f"Unknown method: {method}")
            
            context.output_path = output_path
            context.processing_time = time_sec
            
            logger.debug(
                "Transform completed: method=%s, output=%s, time=%.3fs",
                method, output_path, time_sec
            )
            
        except Exception as e:
            return self.on_error(context, e)
        
        return context


class MetricsStep(PipelineStep):
    """Step for computing quality metrics."""
    
    @property
    def name(self) -> str:
        return "metrics"
    
    @property
    def description(self) -> str:
        return "Вычисление метрик"
    
    @property
    def weight(self) -> float:
        return 0.3
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Compute quality metrics."""
        context.current_step = self.name
        context.update_progress(0.0, "Вычисление метрик...")
        
        try:
            from processing.codecs import load_wav_mono, decode_audio_to_mono, get_audio_meta
            from processing.metrics import (
                compute_snr_db,
                compute_rmse,
                compute_si_sdr_db,
                compute_lsd_db,
                compute_spectral_convergence,
                compute_spectral_centroid_diff_hz,
                compute_spectral_cosine_similarity,
            )
            
            # Load original
            source_path = Path(context.source_path)
            if source_path.suffix.lower() == ".wav":
                original, sr_orig = load_wav_mono(str(source_path))
            else:
                original, sr_orig = decode_audio_to_mono(str(source_path))
            
            # Load processed
            processed, sr_proc = decode_audio_to_mono(context.output_path)
            
            # Compute metrics
            context.metrics = {
                "snr_db": compute_snr_db(original, processed),
                "rmse": compute_rmse(original, processed),
                "si_sdr_db": compute_si_sdr_db(original, processed),
                "lsd_db": compute_lsd_db(original, processed, sr_orig, sr_proc),
                "spec_conv": compute_spectral_convergence(original, processed, sr_orig, sr_proc),
                "spec_centroid_diff_hz": compute_spectral_centroid_diff_hz(original, processed, sr_orig, sr_proc),
                "spec_cosine": compute_spectral_cosine_similarity(original, processed, sr_orig, sr_proc),
            }
            
            # Add file size
            context.metrics["size_bytes"] = Path(context.output_path).stat().st_size
            
            context.update_progress(1.0, "Метрики вычислены")
            
            logger.debug("Metrics computed: %s", context.metrics)
            
        except Exception as e:
            # Metrics computation failure is not critical
            logger.warning("Metrics computation failed: %s", e)
            context.metrics = {}
        
        return context


class EncodeStep(PipelineStep):
    """Step for encoding audio to MP3."""
    
    def __init__(self, bitrate: str = "192k"):
        self._bitrate = bitrate
    
    @property
    def name(self) -> str:
        return "encode"
    
    @property
    def description(self) -> str:
        return "Кодирование в MP3"
    
    @property
    def weight(self) -> float:
        return 0.1
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Encode audio to MP3 (if not already done by transform)."""
        context.current_step = self.name
        
        # Most transforms already encode to MP3, so this step is often a no-op
        # But can be used for re-encoding with different settings
        
        if context.audio_data is not None:
            try:
                from processing.codecs import encode_pcm_to_mp3
                
                base_name = Path(context.source_path).stem
                output_path = str(Path(context.output_dir) / f"{base_name}_{context.method}.mp3")
                
                time_sec = encode_pcm_to_mp3(
                    context.audio_data,
                    context.sample_rate,
                    output_path,
                    bitrate=self._bitrate,
                )
                
                context.output_path = output_path
                context.processing_time += time_sec
                
                logger.debug("Encoded to MP3: %s", output_path)
                
            except Exception as e:
                return self.on_error(context, e)
        
        return context


# =============================================================================
# AUDIO PIPELINE
# =============================================================================

class AudioPipeline:
    """Configurable audio processing pipeline.
    
    Pipelines are composed of steps that are executed in order.
    Each step can modify the context and report progress.
    
    Features:
    - Configurable step sequence
    - Progress reporting
    - Cancellation support
    - Error handling
    
    Example:
    -------
    >>> pipeline = AudioPipeline()
    >>> pipeline.add_step(LoadStep())
    >>> pipeline.add_step(TransformStep("fwht"))
    >>> pipeline.add_step(MetricsStep())
    >>> result = pipeline.execute_sync(context)
    """
    
    def __init__(self, name: str = "default"):
        self._name = name
        self._steps: List[PipelineStep] = []
        self._cancelled = False
    
    @property
    def name(self) -> str:
        """Pipeline name."""
        return self._name
    
    @property
    def steps(self) -> List[PipelineStep]:
        """List of pipeline steps."""
        return self._steps.copy()
    
    def add_step(self, step: PipelineStep) -> "AudioPipeline":
        """Add a step to the pipeline.
        
        Parameters
        ----------
        step : PipelineStep
            Step to add
            
        Returns
        -------
        AudioPipeline
            Self for chaining
        """
        self._steps.append(step)
        return self
    
    def add_steps(self, *steps: PipelineStep) -> "AudioPipeline":
        """Add multiple steps to the pipeline."""
        for step in steps:
            self._steps.append(step)
        return self
    
    def clear_steps(self) -> None:
        """Remove all steps."""
        self._steps.clear()
    
    def cancel(self) -> None:
        """Request pipeline cancellation."""
        self._cancelled = True
    
    def _calculate_total_weight(self) -> float:
        """Calculate total weight of all steps."""
        return sum(step.weight for step in self._steps)
    
    def execute_sync(
        self, 
        context: PipelineContext,
    ) -> PipelineContext:
        """Execute pipeline synchronously.
        
        Parameters
        ----------
        context : PipelineContext
            Initial context with source file and settings
            
        Returns
        -------
        PipelineContext
            Final context with results
        """
        self._cancelled = False
        context.status = PipelineStatus.RUNNING
        context.started_at = datetime.now()
        context.total_steps = len(self._steps)
        
        total_weight = self._calculate_total_weight()
        current_weight = 0.0
        
        for i, step in enumerate(self._steps):
            if self._cancelled:
                context.status = PipelineStatus.CANCELLED
                context.error_message = "Pipeline cancelled"
                break
            
            if not step.can_execute(context):
                continue
            
            context.step_index = i
            logger.info("Executing step: %s (%d/%d)", step.name, i + 1, len(self._steps))
            
            try:
                # Execute step
                context = step.execute(context)
                
                # Update overall progress
                current_weight += step.weight
                overall_progress = current_weight / total_weight if total_weight > 0 else 0
                context.progress = overall_progress
                
            except Exception as e:
                context = step.on_error(context, e)
                break
        
        # Set final status
        if context.status == PipelineStatus.RUNNING:
            context.status = PipelineStatus.COMPLETED
        
        context.finished_at = datetime.now()
        
        logger.info(
            "Pipeline %s finished: status=%s, steps=%d",
            self._name, context.status.name, context.step_index + 1
        )
        
        return context
    
    async def execute_async(
        self,
        context: PipelineContext,
        executor: Optional[ThreadPoolExecutor] = None,
    ) -> PipelineContext:
        """Execute pipeline asynchronously.
        
        Parameters
        ----------
        context : PipelineContext
            Initial context
        executor : Optional[ThreadPoolExecutor]
            Thread pool for CPU-bound operations
            
        Returns
        -------
        PipelineContext
            Final context
        """
        loop = asyncio.get_event_loop()
        
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=1)
        
        return await loop.run_in_executor(
            executor,
            self.execute_sync,
            context
        )


# =============================================================================
# PIPELINE FACTORY
# =============================================================================

class PipelineFactory:
    """Factory for creating pre-configured pipelines."""
    
    @staticmethod
    def create_analysis_pipeline(method: str = "standard") -> AudioPipeline:
        """Create pipeline for audio analysis.
        
        Parameters
        ----------
        method : str
            Transformation method
            
        Returns
        -------
        AudioPipeline
            Configured pipeline
        """
        pipeline = AudioPipeline(f"analysis_{method}")
        pipeline.add_steps(
            LoadStep(),
            TransformStep(method),
            MetricsStep(),
        )
        return pipeline
    
    @staticmethod
    def create_batch_pipeline(methods: List[str]) -> List[AudioPipeline]:
        """Create multiple pipelines for batch processing.
        
        Parameters
        ----------
        methods : List[str]
            List of methods to apply
            
        Returns
        -------
        List[AudioPipeline]
            List of configured pipelines
        """
        return [
            PipelineFactory.create_analysis_pipeline(method)
            for method in methods
        ]
    
    @staticmethod
    def create_quick_pipeline() -> AudioPipeline:
        """Create quick processing pipeline (no metrics)."""
        pipeline = AudioPipeline("quick")
        pipeline.add_steps(
            TransformStep("standard"),
        )
        return pipeline
    
    @staticmethod
    def create_quality_pipeline() -> AudioPipeline:
        """Create quality-focused pipeline with all metrics."""
        pipeline = AudioPipeline("quality")
        pipeline.add_steps(
            LoadStep(),
            TransformStep("fwht"),  # Best quality method
            MetricsStep(),
        )
        return pipeline


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Context
    "PipelineStatus",
    "PipelineContext",
    # Steps
    "PipelineStep",
    "LoadStep",
    "TransformStep",
    "MetricsStep",
    "EncodeStep",
    # Pipeline
    "AudioPipeline",
    "PipelineFactory",
]
