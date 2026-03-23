"""
Repository Pattern for data access abstraction.

Provides:
- Base repository interface for CRUD operations
- JSON-based repositories for profiles, settings, history
- Migration support for data format changes
- Thread-safe file operations

Usage:
------
>>> from ui_new.repositories import ProfileRepository
>>> 
>>> repo = ProfileRepository(Path("./data/profiles"))
>>> profile = repo.get("standard")
>>> repo.save("custom", {"block_size": 4096})
"""
from __future__ import annotations

import json
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

logger = logging.getLogger("ui_new.repositories")

# Type variables
T = TypeVar("T")
ID = TypeVar("ID", str, int)


# =============================================================================
# BASE REPOSITORY INTERFACE
# =============================================================================

class BaseRepository(ABC, Generic[T, ID]):
    """Abstract base repository for CRUD operations.
    
    Subclasses must implement:
    - get(id): Retrieve entity by ID
    - get_all(): Retrieve all entities
    - save(id, entity): Save entity with given ID
    - delete(id): Delete entity by ID
    - exists(id): Check if entity exists
    """
    
    @abstractmethod
    def get(self, id: ID) -> Optional[T]:
        """Retrieve an entity by ID.
        
        Parameters
        ----------
        id : ID
            Entity identifier
            
        Returns
        -------
        Optional[T]
            Entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[ID, T]:
        """Retrieve all entities.
        
        Returns
        -------
        Dict[ID, T]
            Dictionary of all entities
        """
        pass
    
    @abstractmethod
    def save(self, id: ID, entity: T) -> None:
        """Save an entity.
        
        Parameters
        ----------
        id : ID
            Entity identifier
        entity : T
            Entity to save
        """
        pass
    
    @abstractmethod
    def delete(self, id: ID) -> bool:
        """Delete an entity.
        
        Parameters
        ----------
        id : ID
            Entity identifier
            
        Returns
        -------
        bool
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def exists(self, id: ID) -> bool:
        """Check if entity exists.
        
        Parameters
        ----------
        id : ID
            Entity identifier
            
        Returns
        -------
        bool
            True if entity exists
        """
        pass
    
    # Default implementations for common operations
    
    def get_or_default(self, id: ID, default: T) -> T:
        """Get entity or return default."""
        entity = self.get(id)
        return entity if entity is not None else default
    
    def save_all(self, entities: Dict[ID, T]) -> None:
        """Save multiple entities."""
        for id, entity in entities.items():
            self.save(id, entity)
    
    def delete_all(self, ids: List[ID]) -> int:
        """Delete multiple entities. Returns count of deleted."""
        count = 0
        for id in ids:
            if self.delete(id):
                count += 1
        return count
    
    def count(self) -> int:
        """Get count of all entities."""
        return len(self.get_all())
    
    def clear(self) -> int:
        """Delete all entities. Returns count of deleted."""
        ids = list(self.get_all().keys())
        return self.delete_all(ids)


# =============================================================================
# JSON REPOSITORY
# =============================================================================

class JsonRepository(BaseRepository[Dict[str, Any], str]):
    """JSON file-based repository.
    
    Stores entities as JSON files in a directory.
    Thread-safe for concurrent access.
    
    Parameters
    ----------
    directory : Path
        Directory to store JSON files
    file_suffix : str
        Suffix for JSON files (default: ".json")
    """
    
    def __init__(
        self, 
        directory: Union[str, Path],
        file_suffix: str = ".json"
    ):
        self._directory = Path(directory)
        self._file_suffix = file_suffix
        self._lock = threading.RLock()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_valid: bool = False
        
        # Ensure directory exists
        self._directory.mkdir(parents=True, exist_ok=True)
        logger.debug("JsonRepository initialized at %s", self._directory)
    
    def _get_file_path(self, id: str) -> Path:
        """Get file path for entity ID."""
        # Sanitize ID for filesystem
        safe_id = "".join(c for c in id if c.isalnum() or c in "_-")
        return self._directory / f"{safe_id}{self._file_suffix}"
    
    def _invalidate_cache(self) -> None:
        """Invalidate the cache."""
        self._cache_valid = False
        self._cache.clear()
    
    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an entity by ID."""
        with self._lock:
            file_path = self._get_file_path(id)
            
            if not file_path.exists():
                return None
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Error reading %s: %s", id, e)
                return None
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Retrieve all entities."""
        with self._lock:
            if self._cache_valid:
                return self._cache.copy()
            
            entities = {}
            
            for file_path in self._directory.glob(f"*{self._file_suffix}"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Use filename without suffix as ID
                        entity_id = file_path.stem
                        entities[entity_id] = data
                except Exception as e:
                    logger.error("Error reading %s: %s", file_path, e)
            
            self._cache = entities
            self._cache_valid = True
            
            return entities
    
    def save(self, id: str, entity: Dict[str, Any]) -> None:
        """Save an entity."""
        with self._lock:
            file_path = self._get_file_path(id)
            
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(entity, f, ensure_ascii=False, indent=2)
                
                self._invalidate_cache()
                logger.debug("Saved entity: %s", id)
                
            except Exception as e:
                logger.error("Error saving %s: %s", id, e)
                raise
    
    def delete(self, id: str) -> bool:
        """Delete an entity."""
        with self._lock:
            file_path = self._get_file_path(id)
            
            if not file_path.exists():
                return False
            
            try:
                file_path.unlink()
                self._invalidate_cache()
                logger.debug("Deleted entity: %s", id)
                return True
            except Exception as e:
                logger.error("Error deleting %s: %s", id, e)
                return False
    
    def exists(self, id: str) -> bool:
        """Check if entity exists."""
        return self._get_file_path(id).exists()
    
    def get_ids(self) -> List[str]:
        """Get all entity IDs."""
        with self._lock:
            return [
                f.stem for f in self._directory.glob(f"*{self._file_suffix}")
            ]


# =============================================================================
# PROFILE REPOSITORY
# =============================================================================

@dataclass
class Profile:
    """Profile data structure."""
    
    name: str
    display_name: str
    settings: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_builtin: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "settings": self.settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_builtin": self.is_builtin,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            display_name=data.get("display_name", ""),
            settings=data.get("settings", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            is_builtin=data.get("is_builtin", False),
        )


class ProfileRepository(JsonRepository):
    """Repository for profiles with built-in profile support.
    
    Built-in profiles are stored in code and cannot be deleted.
    Custom profiles are stored in JSON files.
    """
    
    BUILTIN_PROFILES: Dict[str, Dict[str, Any]] = {
        "standard": {
            "name": "standard",
            "display_name": "Стандартный",
            "settings": {
                "block_size": 2048,
                "bitrate": "192k",
            },
            "is_builtin": True,
        },
        "fast": {
            "name": "fast",
            "display_name": "Быстрый",
            "settings": {
                "block_size": 1024,
                "bitrate": "128k",
            },
            "is_builtin": True,
        },
        "quality": {
            "name": "quality",
            "display_name": "Качество",
            "settings": {
                "block_size": 4096,
                "bitrate": "320k",
            },
            "is_builtin": True,
        },
        "speech": {
            "name": "speech",
            "display_name": "Речь",
            "settings": {
                "block_size": 2048,
                "bitrate": "128k",
                "select_mode": "energy",
                "keep_energy_ratio": 0.95,
            },
            "is_builtin": True,
        },
    }
    
    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get profile by name."""
        # Check built-in first
        if id in self.BUILTIN_PROFILES:
            return self.BUILTIN_PROFILES[id].copy()
        
        # Then check custom profiles
        return super().get(id)
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all profiles."""
        # Start with built-in profiles
        profiles = {k: v.copy() for k, v in self.BUILTIN_PROFILES.items()}
        
        # Add custom profiles (they can override built-in)
        profiles.update(super().get_all())
        
        return profiles
    
    def delete(self, id: str) -> bool:
        """Delete profile. Cannot delete built-in profiles."""
        if id in self.BUILTIN_PROFILES:
            logger.warning("Cannot delete built-in profile: %s", id)
            return False
        
        return super().delete(id)
    
    def exists(self, id: str) -> bool:
        """Check if profile exists (includes built-in profiles)."""
        if id in self.BUILTIN_PROFILES:
            return True
        return super().exists(id)
    
    def is_builtin(self, id: str) -> bool:
        """Check if profile is built-in."""
        return id in self.BUILTIN_PROFILES
    
    def get_profile_names(self) -> List[str]:
        """Get list of profile names."""
        return list(self.get_all().keys())


# =============================================================================
# SETTINGS REPOSITORY
# =============================================================================

class SettingsRepository(JsonRepository):
    """Repository for application settings.
    
    Settings are stored in a single JSON file with key-value pairs.
    Provides type-safe access with default values.
    """
    
    DEFAULT_SETTINGS: Dict[str, Any] = {
        "theme": "light",
        "language": "ru",
        "last_open_dir": "",
        "auto_refresh_output": True,
        "show_heatmap": True,
        "default_profile": "standard",
        "max_workers": 4,
        "parallel_processing": False,
    }
    
    def __init__(self, directory: Union[str, Path]):
        """Initialize settings repository."""
        super().__init__(directory, file_suffix=".json")
        self._settings_file = Path(directory) / "settings.json"
        self._ensure_defaults()
    
    def _ensure_defaults(self) -> None:
        """Ensure all default settings exist."""
        current = self.get("settings") or {}
        
        # Add missing defaults
        for key, value in self.DEFAULT_SETTINGS.items():
            if key not in current:
                current[key] = value
        
        self.save("settings", current)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        settings = self.get("settings") or {}
        return settings.get(key, default if default is not None else self.DEFAULT_SETTINGS.get(key))
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value."""
        settings = self.get("settings") or {}
        settings[key] = value
        self.save("settings", settings)
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        return self.get("settings") or self.DEFAULT_SETTINGS.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self.save("settings", self.DEFAULT_SETTINGS.copy())


# =============================================================================
# HISTORY REPOSITORY
# =============================================================================

@dataclass
class HistoryEntry:
    """History entry for processed file."""
    
    id: str
    source_file: str
    output_file: str
    method: str
    timestamp: datetime
    metrics: Dict[str, float]
    settings: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "source_file": self.source_file,
            "output_file": self.output_file,
            "method": self.method,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics,
            "settings": self.settings,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            source_file=data.get("source_file", ""),
            output_file=data.get("output_file", ""),
            method=data.get("method", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            metrics=data.get("metrics", {}),
            settings=data.get("settings", {}),
        )


class HistoryRepository(JsonRepository):
    """Repository for processing history.
    
    History entries are stored as JSON files with timestamp-based IDs.
    Supports pagination and filtering.
    """
    
    def __init__(self, directory: Union[str, Path], max_entries: int = 1000):
        """Initialize history repository."""
        super().__init__(directory, file_suffix=".history.json")
        self._max_entries = max_entries
    
    def add_entry(
        self,
        source_file: str,
        output_file: str,
        method: str,
        metrics: Dict[str, float],
        settings: Dict[str, Any],
    ) -> str:
        """Add a history entry.
        
        Returns
        -------
        str
            Entry ID
        """
        timestamp = datetime.now()
        entry_id = timestamp.strftime("%Y%m%d_%H%M%S_%f")
        
        entry = HistoryEntry(
            id=entry_id,
            source_file=source_file,
            output_file=output_file,
            method=method,
            timestamp=timestamp,
            metrics=metrics,
            settings=settings,
        )
        
        self.save(entry_id, entry.to_dict())
        self._cleanup_old_entries()
        
        return entry_id
    
    def _cleanup_old_entries(self) -> None:
        """Remove old entries beyond max_entries."""
        ids = sorted(self.get_ids(), reverse=True)
        
        if len(ids) > self._max_entries:
            for old_id in ids[self._max_entries:]:
                self.delete(old_id)
    
    def get_entries_by_source(self, source_file: str) -> List[Dict[str, Any]]:
        """Get all entries for a source file."""
        all_entries = self.get_all()
        return [
            entry for entry in all_entries.values()
            if entry.get("source_file") == source_file
        ]
    
    def get_entries_by_method(self, method: str) -> List[Dict[str, Any]]:
        """Get all entries for a method."""
        all_entries = self.get_all()
        return [
            entry for entry in all_entries.values()
            if entry.get("method") == method
        ]
    
    def get_recent_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get most recent entries."""
        all_entries = self.get_all()
        
        # Sort by timestamp
        sorted_entries = sorted(
            all_entries.values(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        return sorted_entries[:limit]


# =============================================================================
# SESSION REPOSITORY
# =============================================================================

@dataclass
class Session:
    """Session data for state persistence."""
    
    id: str
    created_at: datetime
    updated_at: datetime
    open_files: List[str]
    results: List[Dict[str, Any]]
    current_profile: str
    settings_snapshot: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "open_files": self.open_files,
            "results": self.results,
            "current_profile": self.current_profile,
            "settings_snapshot": self.settings_snapshot,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            open_files=data.get("open_files", []),
            results=data.get("results", []),
            current_profile=data.get("current_profile", "standard"),
            settings_snapshot=data.get("settings_snapshot", {}),
        )


class SessionRepository(JsonRepository):
    """Repository for application sessions.
    
    Supports session save/restore for application state persistence.
    """
    
    CURRENT_SESSION_FILE = "current_session"
    
    def __init__(self, directory: Union[str, Path]):
        """Initialize session repository."""
        super().__init__(directory, file_suffix=".session.json")
    
    def save_current_session(
        self,
        open_files: List[str],
        results: List[Dict[str, Any]],
        current_profile: str,
        settings: Dict[str, Any],
    ) -> None:
        """Save current session state."""
        now = datetime.now()
        
        # Try to get existing session
        existing = self.get(self.CURRENT_SESSION_FILE)
        
        if existing:
            session = {
                "id": existing.get("id", self.CURRENT_SESSION_FILE),
                "created_at": existing.get("created_at", now.isoformat()),
                "updated_at": now.isoformat(),
                "open_files": open_files,
                "results": results,
                "current_profile": current_profile,
                "settings_snapshot": settings,
            }
        else:
            session = {
                "id": self.CURRENT_SESSION_FILE,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "open_files": open_files,
                "results": results,
                "current_profile": current_profile,
                "settings_snapshot": settings,
            }
        
        self.save(self.CURRENT_SESSION_FILE, session)
    
    def load_current_session(self) -> Optional[Dict[str, Any]]:
        """Load current session state."""
        return self.get(self.CURRENT_SESSION_FILE)
    
    def clear_current_session(self) -> None:
        """Clear current session."""
        self.delete(self.CURRENT_SESSION_FILE)


# =============================================================================
# REPOSITORY FACTORY
# =============================================================================

class RepositoryFactory:
    """Factory for creating repositories.
    
    Provides centralized repository creation with shared configuration.
    """
    
    _instances: Dict[str, BaseRepository] = {}
    _data_dir: Optional[Path] = None
    
    @classmethod
    def initialize(cls, data_dir: Union[str, Path]) -> None:
        """Initialize factory with data directory."""
        cls._data_dir = Path(data_dir)
        cls._data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("RepositoryFactory initialized at %s", cls._data_dir)
    
    @classmethod
    def get_profile_repository(cls) -> ProfileRepository:
        """Get profile repository."""
        if "profile" not in cls._instances:
            if cls._data_dir is None:
                cls.initialize(Path.home() / ".audioanalyzer" / "data")
            cls._instances["profile"] = ProfileRepository(cls._data_dir / "profiles")
        return cls._instances["profile"]
    
    @classmethod
    def get_settings_repository(cls) -> SettingsRepository:
        """Get settings repository."""
        if "settings" not in cls._instances:
            if cls._data_dir is None:
                cls.initialize(Path.home() / ".audioanalyzer" / "data")
            cls._instances["settings"] = SettingsRepository(cls._data_dir / "settings")
        return cls._instances["settings"]
    
    @classmethod
    def get_history_repository(cls) -> HistoryRepository:
        """Get history repository."""
        if "history" not in cls._instances:
            if cls._data_dir is None:
                cls.initialize(Path.home() / ".audioanalyzer" / "data")
            cls._instances["history"] = HistoryRepository(cls._data_dir / "history")
        return cls._instances["history"]
    
    @classmethod
    def get_session_repository(cls) -> SessionRepository:
        """Get session repository."""
        if "session" not in cls._instances:
            if cls._data_dir is None:
                cls.initialize(Path.home() / ".audioanalyzer" / "data")
            cls._instances["session"] = SessionRepository(cls._data_dir / "sessions")
        return cls._instances["session"]
    
    @classmethod
    def clear_all(cls) -> None:
        """Clear all repository instances."""
        cls._instances.clear()


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Base classes
    "BaseRepository",
    "JsonRepository",
    # Data classes
    "Profile",
    "HistoryEntry",
    "Session",
    # Specific repositories
    "ProfileRepository",
    "SettingsRepository",
    "HistoryRepository",
    "SessionRepository",
    # Factory
    "RepositoryFactory",
]
