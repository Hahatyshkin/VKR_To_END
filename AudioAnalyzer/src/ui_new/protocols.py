"""
Protocol definitions for type-safe interfaces.

This module provides Protocol interfaces that can be used for:
- Static type checking with mypy
- Runtime protocol checking with isinstance()
- Duck typing support
- More flexible inheritance than ABC

Protocols vs ABC:
- Protocols support structural subtyping (duck typing)
- ABCs require explicit inheritance
- Protocols work better with type checkers
- Both can be used together for maximum flexibility

Usage:
------
>>> from ui_new.protocols import RepositoryProtocol
>>> 
>>> def save_data(repo: RepositoryProtocol) -> None:
...     repo.save("key", {"data": "value"})
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar, runtime_checkable

# Type variables
T = TypeVar("T")
ID = TypeVar("ID", str, int)


# =============================================================================
# REPOSITORY PROTOCOL
# =============================================================================

@runtime_checkable
class RepositoryProtocol(Protocol[T, ID]):
    """Protocol for repository implementations.
    
    Any class that implements these methods conforms to this protocol,
    regardless of inheritance.
    
    Example:
    -------
    >>> class MyRepository:
    ...     def get(self, id: str) -> Optional[dict]:
    ...         return {"id": id}
    ...     # ... other methods
    >>> 
    >>> repo = MyRepository()
    >>> isinstance(repo, RepositoryProtocol)  # True
    """
    
    def get(self, id: ID) -> Optional[T]:
        """Retrieve entity by ID."""
        ...
    
    def get_all(self) -> Dict[ID, T]:
        """Retrieve all entities."""
        ...
    
    def save(self, id: ID, entity: T) -> None:
        """Save entity with given ID."""
        ...
    
    def delete(self, id: ID) -> bool:
        """Delete entity by ID. Returns True if deleted."""
        ...
    
    def exists(self, id: ID) -> bool:
        """Check if entity exists."""
        ...


@runtime_checkable
class JsonRepositoryProtocol(Protocol):
    """Protocol for JSON-based repositories."""
    
    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        ...
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all entities."""
        ...
    
    def save(self, id: str, entity: Dict[str, Any]) -> None:
        """Save entity."""
        ...
    
    def delete(self, id: str) -> bool:
        """Delete entity."""
        ...
    
    def exists(self, id: str) -> bool:
        """Check if entity exists."""
        ...
    
    def get_ids(self) -> List[str]:
        """Get all entity IDs."""
        ...


@runtime_checkable
class ProfileRepositoryProtocol(Protocol):
    """Protocol for profile repositories."""
    
    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get profile by name."""
        ...
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all profiles including built-ins."""
        ...
    
    def save(self, name: str, profile: Dict[str, Any]) -> None:
        """Save custom profile."""
        ...
    
    def delete(self, name: str) -> bool:
        """Delete profile (cannot delete built-ins)."""
        ...
    
    def is_builtin(self, name: str) -> bool:
        """Check if profile is built-in."""
        ...
    
    def get_profile_names(self) -> List[str]:
        """Get all profile names."""
        ...


@runtime_checkable
class SettingsRepositoryProtocol(Protocol):
    """Protocol for settings repositories."""
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting value."""
        ...
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set setting value."""
        ...
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        ...
    
    def reset_to_defaults(self) -> None:
        """Reset to default settings."""
        ...


# =============================================================================
# PIPELINE PROTOCOL
# =============================================================================

class PipelineContextProtocol(Protocol):
    """Protocol for pipeline context."""
    
    source_path: str
    output_dir: str
    output_path: str
    audio_data: Optional[Any]
    sample_rate: int
    channels: int
    current_step: str
    step_index: int
    total_steps: int
    progress: float
    settings: Dict[str, Any]
    method: str
    metrics: Dict[str, float]
    processing_time: float
    status: Any  # PipelineStatus
    error_message: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    
    def update_progress(self, progress: float, message: str = "") -> None:
        """Update progress."""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        ...


@runtime_checkable
class PipelineStepProtocol(Protocol):
    """Protocol for pipeline steps."""
    
    @property
    def name(self) -> str:
        """Step name."""
        ...
    
    @property
    def description(self) -> str:
        """Step description."""
        ...
    
    @property
    def weight(self) -> float:
        """Relative weight for progress calculation."""
        ...
    
    def execute(self, context: PipelineContextProtocol) -> PipelineContextProtocol:
        """Execute the step."""
        ...
    
    def can_execute(self, context: PipelineContextProtocol) -> bool:
        """Check if step can execute."""
        ...
    
    def on_error(
        self, 
        context: PipelineContextProtocol, 
        error: Exception
    ) -> PipelineContextProtocol:
        """Handle step error."""
        ...


@runtime_checkable
class AudioPipelineProtocol(Protocol):
    """Protocol for audio pipelines."""
    
    @property
    def name(self) -> str:
        """Pipeline name."""
        ...
    
    @property
    def steps(self) -> List[PipelineStepProtocol]:
        """List of pipeline steps."""
        ...
    
    def add_step(self, step: PipelineStepProtocol) -> "AudioPipelineProtocol":
        """Add a step to the pipeline."""
        ...
    
    def cancel(self) -> None:
        """Request pipeline cancellation."""
        ...
    
    def execute_sync(
        self, 
        context: PipelineContextProtocol
    ) -> PipelineContextProtocol:
        """Execute pipeline synchronously."""
        ...


# =============================================================================
# TRANSFORM PROTOCOL
# =============================================================================

@runtime_checkable
class AudioTransformProtocol(Protocol):
    """Protocol for audio transformations."""
    
    @property
    def name(self) -> str:
        """Transform name."""
        ...
    
    @property
    def description(self) -> str:
        """Transform description."""
        ...
    
    def forward(self, signal: Any) -> Any:
        """Apply forward transform."""
        ...
    
    def inverse(self, coeffs: Any) -> Any:
        """Apply inverse transform."""
        ...
    
    def get_block_size(self) -> int:
        """Get block size for transform."""
        ...
    
    def set_block_size(self, size: int) -> None:
        """Set block size for transform."""
        ...


@runtime_checkable
class TransformFactoryProtocol(Protocol):
    """Protocol for transform factories."""
    
    def create(self, name: str, **kwargs) -> AudioTransformProtocol:
        """Create transform by name."""
        ...
    
    def get_available_transforms(self) -> List[str]:
        """Get list of available transform names."""
        ...
    
    def get_transform_info(self, name: str) -> Dict[str, Any]:
        """Get information about a transform."""
        ...


# =============================================================================
# SERVICE PROTOCOL
# =============================================================================

@runtime_checkable
class AudioServiceProtocol(Protocol):
    """Protocol for audio processing services."""
    
    def process_file(
        self,
        source_path: str,
        output_dir: str,
        method: str,
        settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process a single file."""
        ...
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported input formats."""
        ...
    
    def get_available_methods(self) -> List[str]:
        """Get list of available processing methods."""
        ...


@runtime_checkable
class FileServiceProtocol(Protocol):
    """Protocol for file services."""
    
    def get_files(self, directory: str, pattern: str = "*") -> List[str]:
        """Get files matching pattern in directory."""
        ...
    
    def get_audio_files(self, directory: str) -> List[str]:
        """Get audio files in directory."""
        ...
    
    def ensure_directory(self, path: str) -> None:
        """Ensure directory exists."""
        ...
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file information."""
        ...


@runtime_checkable
class SpectrumServiceProtocol(Protocol):
    """Protocol for spectrum services."""
    
    def compute_spectrum(
        self,
        signal: Any,
        sample_rate: int,
    ) -> tuple:
        """Compute spectrum of signal."""
        ...
    
    def compare_spectra(
        self,
        original: Any,
        processed: Any,
        sample_rate: int,
    ) -> Dict[str, float]:
        """Compare two spectra."""
        ...


# =============================================================================
# EVENT HANDLER PROTOCOL
# =============================================================================

@runtime_checkable
class EventHandlerProtocol(Protocol):
    """Protocol for event handlers."""
    
    def handle(self, event: Dict[str, Any]) -> None:
        """Handle an event."""
        ...


@runtime_checkable
class EventEmitterProtocol(Protocol):
    """Protocol for event emitters."""
    
    def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event."""
        ...
    
    def subscribe(
        self, 
        event_type: str, 
        handler: EventHandlerProtocol
    ) -> None:
        """Subscribe to events."""
        ...
    
    def unsubscribe(
        self, 
        event_type: str, 
        handler: EventHandlerProtocol
    ) -> None:
        """Unsubscribe from events."""
        ...


# =============================================================================
# UI COMPONENT PROTOCOL
# =============================================================================

@runtime_checkable
class WidgetProtocol(Protocol):
    """Protocol for UI widgets."""
    
    def show(self) -> None:
        """Show the widget."""
        ...
    
    def hide(self) -> None:
        """Hide the widget."""
        ...
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        ...
    
    def get_value(self) -> Any:
        """Get current value."""
        ...
    
    def set_value(self, value: Any) -> None:
        """Set current value."""
        ...


@runtime_checkable
class MainWindowProtocol(Protocol):
    """Protocol for main window."""
    
    def show_toast(self, message: str, type: str = "info") -> None:
        """Show toast notification."""
        ...
    
    def set_status(self, message: str) -> None:
        """Set status message."""
        ...
    
    def refresh_ui(self) -> None:
        """Refresh UI state."""
        ...
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current settings."""
        ...


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Repository protocols
    "RepositoryProtocol",
    "JsonRepositoryProtocol",
    "ProfileRepositoryProtocol",
    "SettingsRepositoryProtocol",
    # Pipeline protocols
    "PipelineContextProtocol",
    "PipelineStepProtocol",
    "AudioPipelineProtocol",
    # Transform protocols
    "AudioTransformProtocol",
    "TransformFactoryProtocol",
    # Service protocols
    "AudioServiceProtocol",
    "FileServiceProtocol",
    "SpectrumServiceProtocol",
    # Event protocols
    "EventHandlerProtocol",
    "EventEmitterProtocol",
    # UI protocols
    "WidgetProtocol",
    "MainWindowProtocol",
]
