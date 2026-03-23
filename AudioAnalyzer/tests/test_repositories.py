"""
Tests for Repository Pattern implementation.

Tests verify:
- BaseRepository abstract interface
- JsonRepository CRUD operations
- ProfileRepository with built-in profiles
- SettingsRepository with defaults
- HistoryRepository with filtering
- SessionRepository for state persistence
- RepositoryFactory singleton pattern
"""
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestBaseRepository:
    """Tests for BaseRepository abstract class."""
    
    def test_base_repository_is_abstract(self):
        """Test that BaseRepository cannot be instantiated directly."""
        from ui_new.repositories import BaseRepository
        
        with pytest.raises(TypeError):
            BaseRepository()
    
    def test_base_repository_has_required_methods(self):
        """Test that BaseRepository defines required abstract methods."""
        from ui_new.repositories import BaseRepository
        import inspect
        
        abstract_methods = [
            name for name, method in inspect.getmembers(BaseRepository)
            if getattr(method, '__isabstractmethod__', False)
        ]
        
        assert 'get' in abstract_methods
        assert 'get_all' in abstract_methods
        assert 'save' in abstract_methods
        assert 'delete' in abstract_methods
        assert 'exists' in abstract_methods
    
    def test_base_repository_default_methods(self):
        """Test that BaseRepository provides default implementations."""
        from ui_new.repositories import BaseRepository
        
        # Check default methods exist
        assert hasattr(BaseRepository, 'get_or_default')
        assert hasattr(BaseRepository, 'save_all')
        assert hasattr(BaseRepository, 'delete_all')
        assert hasattr(BaseRepository, 'count')
        assert hasattr(BaseRepository, 'clear')


class TestJsonRepository:
    """Tests for JsonRepository implementation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def repo(self, temp_dir):
        """Create JsonRepository instance."""
        from ui_new.repositories import JsonRepository
        return JsonRepository(temp_dir)
    
    def test_save_and_get(self, repo):
        """Test saving and retrieving an entity."""
        entity = {"name": "test", "value": 123}
        repo.save("test_id", entity)
        
        result = repo.get("test_id")
        
        assert result is not None
        assert result["name"] == "test"
        assert result["value"] == 123
    
    def test_get_nonexistent(self, repo):
        """Test getting a nonexistent entity."""
        result = repo.get("nonexistent")
        
        assert result is None
    
    def test_get_all(self, repo):
        """Test getting all entities."""
        repo.save("id1", {"name": "first"})
        repo.save("id2", {"name": "second"})
        
        all_entities = repo.get_all()
        
        assert len(all_entities) == 2
        assert "id1" in all_entities
        assert "id2" in all_entities
    
    def test_delete(self, repo):
        """Test deleting an entity."""
        repo.save("to_delete", {"name": "delete_me"})
        
        assert repo.exists("to_delete")
        
        result = repo.delete("to_delete")
        
        assert result is True
        assert not repo.exists("to_delete")
    
    def test_delete_nonexistent(self, repo):
        """Test deleting a nonexistent entity."""
        result = repo.delete("nonexistent")
        
        assert result is False
    
    def test_exists(self, repo):
        """Test checking if entity exists."""
        repo.save("existing", {"name": "exists"})
        
        assert repo.exists("existing") is True
        assert repo.exists("nonexistent") is False
    
    def test_get_ids(self, repo):
        """Test getting all entity IDs."""
        repo.save("id1", {"name": "first"})
        repo.save("id2", {"name": "second"})
        
        ids = repo.get_ids()
        
        assert len(ids) == 2
        assert "id1" in ids
        assert "id2" in ids


class TestProfileRepository:
    """Tests for ProfileRepository implementation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def repo(self, temp_dir):
        """Create ProfileRepository instance."""
        from ui_new.repositories import ProfileRepository
        return ProfileRepository(temp_dir)
    
    def test_builtin_profiles_exist(self, repo):
        """Test that built-in profiles are available."""
        # Check that BUILTIN_PROFILES is defined
        from ui_new.repositories import ProfileRepository
        
        assert hasattr(ProfileRepository, 'BUILTIN_PROFILES')
        assert len(ProfileRepository.BUILTIN_PROFILES) > 0
    
    def test_get_builtin_profile(self, repo):
        """Test getting a built-in profile."""
        from ui_new.repositories import ProfileRepository
        
        # Get first builtin profile
        first_builtin = list(ProfileRepository.BUILTIN_PROFILES.keys())[0]
        profile = repo.get(first_builtin)
        
        assert profile is not None
    
    def test_get_all_includes_builtins(self, repo):
        """Test that get_all includes built-in profiles."""
        from ui_new.repositories import ProfileRepository
        
        all_profiles = repo.get_all()
        
        # Should include at least the builtin profiles
        for name in ProfileRepository.BUILTIN_PROFILES.keys():
            assert name in all_profiles
    
    def test_save_custom_profile(self, repo):
        """Test saving a custom profile."""
        custom = {
            "name": "custom",
            "display_name": "Custom Profile",
            "settings": {"block_size": 8192},
        }
        
        repo.save("custom", custom)
        
        result = repo.get("custom")
        assert result is not None
        assert result["name"] == "custom"
    
    def test_cannot_delete_builtin(self, repo):
        """Test that built-in profiles cannot be deleted."""
        from ui_new.repositories import ProfileRepository
        
        first_builtin = list(ProfileRepository.BUILTIN_PROFILES.keys())[0]
        result = repo.delete(first_builtin)
        
        assert result is False
    
    def test_is_builtin(self, repo):
        """Test checking if profile is built-in."""
        from ui_new.repositories import ProfileRepository
        
        first_builtin = list(ProfileRepository.BUILTIN_PROFILES.keys())[0]
        
        assert repo.is_builtin(first_builtin) is True
        assert repo.is_builtin("custom_nonexistent") is False
    
    def test_get_profile_names(self, repo):
        """Test getting all profile names."""
        names = repo.get_profile_names()
        
        assert isinstance(names, list)
        assert len(names) > 0


class TestSettingsRepository:
    """Tests for SettingsRepository implementation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def repo(self, temp_dir):
        """Create SettingsRepository instance."""
        from ui_new.repositories import SettingsRepository
        return SettingsRepository(temp_dir)
    
    def test_get_setting(self, repo):
        """Test getting a setting."""
        # Default setting should exist
        from ui_new.repositories import SettingsRepository
        
        first_default = list(SettingsRepository.DEFAULT_SETTINGS.keys())[0]
        value = repo.get_setting(first_default)
        assert value is not None
    
    def test_get_setting_with_default(self, repo):
        """Test getting a setting with default value."""
        value = repo.get_setting("nonexistent_key", default="default_value")
        
        assert value == "default_value"
    
    def test_set_setting(self, repo):
        """Test setting a value."""
        repo.set_setting("custom_key", "custom_value")
        
        assert repo.get_setting("custom_key") == "custom_value"
    
    def test_get_all_settings(self, repo):
        """Test getting all settings."""
        settings = repo.get_all_settings()
        
        assert isinstance(settings, dict)
    
    def test_reset_to_defaults(self, repo):
        """Test resetting settings to defaults."""
        repo.set_setting("theme", "dark")
        
        repo.reset_to_defaults()
        
        # After reset, default settings should be restored
        from ui_new.repositories import SettingsRepository
        
        for key, value in SettingsRepository.DEFAULT_SETTINGS.items():
            assert repo.get_setting(key) == value


class TestHistoryRepository:
    """Tests for HistoryRepository implementation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def repo(self, temp_dir):
        """Create HistoryRepository instance."""
        from ui_new.repositories import HistoryRepository
        return HistoryRepository(temp_dir, max_entries=10)
    
    def test_add_entry(self, repo):
        """Test adding a history entry."""
        entry_id = repo.add_entry(
            source_file="/path/to/source.wav",
            output_file="/path/to/output.mp3",
            method="fwht",
            metrics={"lsd_db": 1.5},
            settings={"block_size": 2048},
        )
        
        assert entry_id is not None
        
        entry = repo.get(entry_id)
        assert entry is not None
        assert entry["source_file"] == "/path/to/source.wav"
        assert entry["method"] == "fwht"
    
    def test_get_entries_by_source(self, repo):
        """Test filtering entries by source file."""
        repo.add_entry(
            source_file="/path/file1.wav",
            output_file="/path/out1.mp3",
            method="fwht",
            metrics={},
            settings={},
        )
        repo.add_entry(
            source_file="/path/file2.wav",
            output_file="/path/out2.mp3",
            method="fft",
            metrics={},
            settings={},
        )
        repo.add_entry(
            source_file="/path/file1.wav",
            output_file="/path/out3.mp3",
            method="fft",
            metrics={},
            settings={},
        )
        
        entries = repo.get_entries_by_source("/path/file1.wav")
        
        assert len(entries) == 2
    
    def test_get_entries_by_method(self, repo):
        """Test filtering entries by method."""
        repo.add_entry(
            source_file="/path/file.wav",
            output_file="/path/out1.mp3",
            method="fwht",
            metrics={},
            settings={},
        )
        repo.add_entry(
            source_file="/path/file.wav",
            output_file="/path/out2.mp3",
            method="fft",
            metrics={},
            settings={},
        )
        
        fwht_entries = repo.get_entries_by_method("fwht")
        
        assert len(fwht_entries) == 1
        assert fwht_entries[0]["method"] == "fwht"
    
    def test_get_recent_entries(self, repo):
        """Test getting recent entries."""
        for i in range(5):
            repo.add_entry(
                source_file=f"/path/file{i}.wav",
                output_file=f"/path/out{i}.mp3",
                method="fwht",
                metrics={},
                settings={},
            )
        
        recent = repo.get_recent_entries(limit=3)
        
        assert len(recent) == 3


class TestSessionRepository:
    """Tests for SessionRepository implementation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def repo(self, temp_dir):
        """Create SessionRepository instance."""
        from ui_new.repositories import SessionRepository
        return SessionRepository(temp_dir)
    
    def test_save_and_load_session(self, repo):
        """Test saving and loading current session."""
        repo.save_current_session(
            open_files=["/path/file1.wav", "/path/file2.wav"],
            results=[{"variant": "fwht"}],
            current_profile="quality",
            settings={"block_size": 4096},
        )
        
        session = repo.load_current_session()
        
        assert session is not None
        assert len(session["open_files"]) == 2
        assert session["current_profile"] == "quality"
    
    def test_clear_session(self, repo):
        """Test clearing current session."""
        repo.save_current_session(
            open_files=["/path/file.wav"],
            results=[],
            current_profile="standard",
            settings={},
        )
        
        repo.clear_current_session()
        
        session = repo.load_current_session()
        assert session is None


class TestRepositoryFactory:
    """Tests for RepositoryFactory."""
    
    def test_factory_initialization(self):
        """Test factory initialization."""
        from ui_new.repositories import RepositoryFactory
        
        with tempfile.TemporaryDirectory() as tmpdir:
            RepositoryFactory.initialize(tmpdir)
            
            assert RepositoryFactory._data_dir == Path(tmpdir)
            
            # Cleanup
            RepositoryFactory.clear_all()
    
    def test_get_profile_repository(self):
        """Test getting profile repository from factory."""
        from ui_new.repositories import RepositoryFactory, ProfileRepository
        
        with tempfile.TemporaryDirectory() as tmpdir:
            RepositoryFactory.initialize(tmpdir)
            
            repo = RepositoryFactory.get_profile_repository()
            
            assert isinstance(repo, ProfileRepository)
            
            # Cleanup
            RepositoryFactory.clear_all()
    
    def test_get_settings_repository(self):
        """Test getting settings repository from factory."""
        from ui_new.repositories import RepositoryFactory, SettingsRepository
        
        with tempfile.TemporaryDirectory() as tmpdir:
            RepositoryFactory.initialize(tmpdir)
            
            repo = RepositoryFactory.get_settings_repository()
            
            assert isinstance(repo, SettingsRepository)
            
            # Cleanup
            RepositoryFactory.clear_all()
    
    def test_singleton_repositories(self):
        """Test that factory returns same instances."""
        from ui_new.repositories import RepositoryFactory
        
        with tempfile.TemporaryDirectory() as tmpdir:
            RepositoryFactory.initialize(tmpdir)
            
            repo1 = RepositoryFactory.get_profile_repository()
            repo2 = RepositoryFactory.get_profile_repository()
            
            assert repo1 is repo2
            
            # Cleanup
            RepositoryFactory.clear_all()
    
    def test_clear_all(self):
        """Test clearing all repository instances."""
        from ui_new.repositories import RepositoryFactory
        
        with tempfile.TemporaryDirectory() as tmpdir:
            RepositoryFactory.initialize(tmpdir)
            
            RepositoryFactory.get_profile_repository()
            RepositoryFactory.get_settings_repository()
            
            RepositoryFactory.clear_all()
            
            assert len(RepositoryFactory._instances) == 0


class TestDataClasses:
    """Tests for data classes."""
    
    def test_profile_to_dict(self):
        """Test Profile serialization."""
        from ui_new.repositories import Profile
        
        profile = Profile(
            name="test",
            display_name="Test Profile",
            settings={"block_size": 2048},
            is_builtin=False,
        )
        
        d = profile.to_dict()
        
        assert d["name"] == "test"
        assert d["display_name"] == "Test Profile"
        assert d["settings"] == {"block_size": 2048}
    
    def test_profile_from_dict(self):
        """Test Profile deserialization."""
        from ui_new.repositories import Profile
        
        d = {
            "name": "test",
            "display_name": "Test Profile",
            "settings": {"block_size": 2048},
            "is_builtin": False,
        }
        
        profile = Profile.from_dict(d)
        
        assert profile.name == "test"
        assert profile.display_name == "Test Profile"
    
    def test_history_entry_to_dict(self):
        """Test HistoryEntry serialization."""
        from ui_new.repositories import HistoryEntry
        
        entry = HistoryEntry(
            id="test_id",
            source_file="/path/source.wav",
            output_file="/path/output.mp3",
            method="fwht",
            timestamp=datetime.now(),
            metrics={"lsd_db": 1.5},
            settings={"block_size": 2048},
        )
        
        d = entry.to_dict()
        
        assert d["id"] == "test_id"
        assert d["source_file"] == "/path/source.wav"
        assert d["method"] == "fwht"
    
    def test_session_to_dict(self):
        """Test Session serialization."""
        from ui_new.repositories import Session
        
        session = Session(
            id="session_id",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            open_files=["/path/file.wav"],
            results=[{"variant": "fwht"}],
            current_profile="standard",
            settings_snapshot={"block_size": 2048},
        )
        
        d = session.to_dict()
        
        assert d["id"] == "session_id"
        assert len(d["open_files"]) == 1
        assert d["current_profile"] == "standard"


class TestExports:
    """Tests for module exports."""
    
    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        from ui_new.repositories import __all__
        
        expected = [
            "BaseRepository",
            "JsonRepository",
            "Profile",
            "HistoryEntry",
            "Session",
            "ProfileRepository",
            "SettingsRepository",
            "HistoryRepository",
            "SessionRepository",
            "RepositoryFactory",
        ]
        
        for export in expected:
            assert export in __all__


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_factory():
    """Cleanup RepositoryFactory after each test."""
    yield
    
    from ui_new.repositories import RepositoryFactory
    RepositoryFactory.clear_all()
