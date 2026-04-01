"""
Extended unit tests for AudioAnalyzer services and components.

These tests focus on increasing coverage for:
- Service layer (container, config, file_service, audio_service)
- Worker module
- Profile management
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# =============================================================================
# CONTAINER TESTS
# =============================================================================

class TestServiceContainerExtended:
    """Extended tests for the DI container."""
    
    @pytest.fixture(autouse=True)
    def reset_container(self):
        """Reset container before and after each test."""
        from ui_new.services import reset_container as _reset
        _reset()
        yield
        _reset()
    
    def test_container_lazy_initialization(self):
        """Test that services are lazily initialized."""
        from ui_new.services import ServiceContainer
        
        container = ServiceContainer()
        
        # Config should be initialized immediately
        assert container._config is not None
        
        # Services dict should be empty initially
        assert len(container._services) == 0
    
    def test_container_audio_processing_property(self):
        """Test audio processing service property creates instance."""
        from ui_new.services import ServiceContainer
        
        container = ServiceContainer()
        
        # First access creates the service
        ap1 = container.audio_processing
        assert ap1 is not None
        
        # Second access returns the same instance
        ap2 = container.audio_processing
        assert ap1 is ap2
    
    def test_container_spectrum_property(self):
        """Test spectrum service property creates instance."""
        from ui_new.services import ServiceContainer
        
        container = ServiceContainer()
        
        ss1 = container.spectrum
        assert ss1 is not None
        
        ss2 = container.spectrum
        assert ss1 is ss2
    
    def test_container_file_property(self):
        """Test file service property creates instance."""
        from ui_new.services import ServiceContainer
        
        container = ServiceContainer()
        
        fs1 = container.file
        assert fs1 is not None
        
        fs2 = container.file
        assert fs1 is fs2
    
    def test_get_container_creates_if_none(self):
        """Test get_container creates container if not initialized."""
        from ui_new.services import get_container, reset_container
        
        reset_container()
        container = get_container()
        assert container is not None
    
    def test_init_container_replaces_existing(self):
        """Test init_container replaces existing container."""
        from ui_new.services import init_container, get_container, reset_container
        
        reset_container()
        container1 = init_container()
        container2 = get_container()
        assert container1 is container2
        
        container3 = init_container()
        container4 = get_container()
        assert container3 is container4
    
    def test_register_service(self):
        """Test manual service registration."""
        from ui_new.services import ServiceContainer
        
        container = ServiceContainer()
        mock_service = MagicMock()
        
        container.register_service('custom', mock_service)
        
        assert 'custom' in container._services
        assert container._services['custom'] is mock_service
    
    def test_register_factory(self):
        """Test factory registration."""
        from ui_new.services import ServiceContainer
        
        container = ServiceContainer()
        factory = lambda: MagicMock()
        
        container.register_factory('custom_factory', factory)
        
        assert 'custom_factory' in container._factories
    
    def test_clear_services(self):
        """Test clearing services."""
        from ui_new.services import ServiceContainer
        
        container = ServiceContainer()
        _ = container.audio_processing  # Initialize
        
        assert len(container._services) > 0
        
        container.clear()
        
        assert len(container._services) == 0
    
    def test_reconfigure(self):
        """Test reconfiguring container."""
        from ui_new.services import ServiceContainer
        from ui_new.services.config import create_app_config
        
        container = ServiceContainer()
        _ = container.audio_processing  # Initialize
        
        new_config = create_app_config()
        container.reconfigure(new_config)
        
        assert container._config is new_config
        assert len(container._services) == 0


# =============================================================================
# CONFIG TESTS
# =============================================================================

class TestConfigExtended:
    """Extended tests for configuration."""
    
    def test_create_app_config(self):
        """Test app config creation."""
        from ui_new.services.config import create_app_config
        
        config = create_app_config()
        
        assert config is not None
        assert config.project_root is not None
    
    def test_progress_ranges_complete(self):
        """Test that all methods have progress ranges."""
        from ui_new.services.config import PROGRESS_RANGES
        
        expected_methods = ['fwht', 'fft', 'dct', 'dwt', 'huffman', 'rosenbrock', 'standard']
        
        for method in expected_methods:
            assert method in PROGRESS_RANGES
            start, end = PROGRESS_RANGES[method]
            assert 0 <= start < end <= 100
    
    def test_spectrum_max_points(self):
        """Test spectrum max points constant."""
        from ui_new.services.config import SPECTRUM_MAX_POINTS
        
        assert SPECTRUM_MAX_POINTS > 0
        assert SPECTRUM_MAX_POINTS <= 100000  # Reasonable upper limit


# =============================================================================
# FILE SERVICE TESTS
# =============================================================================

class TestFileServiceExtended:
    """Extended tests for FileService."""
    
    @pytest.fixture
    def file_service(self, service_container):
        """Provide a FileService instance."""
        from ui_new.services.file_service import FileService
        return FileService(service_container.config)
    
    def test_method_suffixes_complete(self, file_service):
        """Test that all methods have suffixes."""
        expected_methods = ['fwht', 'fft', 'dct', 'dwt', 'huffman', 'rosenbrock', 'standard']
        
        for method in expected_methods:
            assert method in file_service.METHOD_SUFFIXES
    
    def test_get_file_size_existing(self, file_service):
        """Test get_file_size with existing file."""
        size = file_service.get_file_size(__file__)
        assert size > 0
    
    def test_get_file_size_nonexistent(self, file_service):
        """Test get_file_size with nonexistent file."""
        size = file_service.get_file_size('/nonexistent/path/file.wav')
        assert size == 0
    
    def test_validate_audio_file_nonexistent(self, file_service):
        """Test validation of nonexistent file."""
        is_valid, error = file_service.validate_audio_file('/nonexistent/file.wav')
        assert not is_valid
        assert error  # Should have an error message
    
    def test_validate_audio_file_wrong_extension(self, file_service, temp_dir):
        """Test validation of file with wrong extension."""
        # Create a text file
        text_file = temp_dir / "test.txt"
        text_file.write_text("not an audio file")
        
        is_valid, error = file_service.validate_audio_file(str(text_file))
        assert not is_valid


# =============================================================================
# AUDIO SERVICE TESTS
# =============================================================================

class TestAudioServiceExtended:
    """Extended tests for AudioProcessingService."""
    
    @pytest.fixture
    def audio_service(self, service_container):
        """Provide an AudioProcessingService instance."""
        from ui_new.services.audio_service import AudioProcessingService
        return AudioProcessingService(service_container.config)
    
    def test_get_default_settings(self, audio_service):
        """Test default settings retrieval."""
        settings = audio_service.get_default_settings()
        
        assert 'block_size' in settings
        assert settings['block_size'] > 0
        assert 'bitrate' in settings
    
    def test_validate_settings_valid(self, audio_service):
        """Test validation of valid settings."""
        settings = {
            'block_size': 2048,
            'bitrate': '192k',
        }
        is_valid, errors = audio_service.validate_settings(settings)
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_settings_invalid_block_size(self, audio_service):
        """Test validation with invalid block size."""
        settings = {'block_size': 1000}  # Not a power of 2
        is_valid, errors = audio_service.validate_settings(settings)
        assert not is_valid
    
    def test_format_eta(self, audio_service):
        """Test ETA formatting."""
        assert audio_service.format_eta(0) == "00:00"
        assert audio_service.format_eta(59) == "00:59"
        assert audio_service.format_eta(60) == "01:00"
        assert audio_service.format_eta(65) == "01:05"
        assert audio_service.format_eta(3600) == "1:00:00"
        assert audio_service.format_eta(3665) == "1:01:05"
    
    def test_get_method_recommendations(self, audio_service):
        """Test method recommendations."""
        # Short speech file
        recommendations = audio_service.get_method_recommendations({
            'duration_sec': 5,
            'dynamic_range_db': 30,
            'spectral_centroid_hz': 2000,
            'is_speech': True,
        })
        
        assert len(recommendations) > 0
        
        # Each recommendation should be (method, score, reason)
        for rec in recommendations:
            assert len(rec) >= 2
            method, score = rec[0], rec[1]
            assert isinstance(method, str)
            assert 0 <= score <= 1
    
    def test_get_method_recommendations_music(self, audio_service):
        """Test method recommendations for music."""
        # Long music file
        recommendations = audio_service.get_method_recommendations({
            'duration_sec': 300,  # 5 minutes
            'dynamic_range_db': 50,
            'spectral_centroid_hz': 5000,
            'is_speech': False,
        })
        
        assert len(recommendations) > 0


# =============================================================================
# SPECTRUM SERVICE TESTS
# =============================================================================

class TestSpectrumServiceExtended:
    """Extended tests for SpectrumService."""
    
    @pytest.fixture
    def spectrum_service(self, service_container):
        """Provide a SpectrumService instance."""
        from ui_new.services.spectrum_service import SpectrumService
        return SpectrumService(service_container.config)
    
    def test_compute_spectrum_sine(self, spectrum_service, sine_signal, sample_rate):
        """Test spectrum computation with sine wave."""
        freqs, spectrum = spectrum_service.compute_spectrum(sine_signal, sample_rate)
        
        assert len(freqs) > 0
        assert len(spectrum) == len(freqs)
        
        # Peak should be around 440 Hz
        peak_idx = np.argmax(spectrum)
        peak_freq = freqs[peak_idx]
        assert abs(peak_freq - 440) < 10
    
    def test_compute_spectrum_empty(self, spectrum_service, sample_rate):
        """Test spectrum computation with empty signal."""
        freqs, spectrum = spectrum_service.compute_spectrum(np.array([]), sample_rate)
        
        assert len(freqs) == 0
        assert len(spectrum) == 0
    
    def test_compute_spectrum_silence(self, spectrum_service, silence, sample_rate):
        """Test spectrum computation with silence."""
        freqs, spectrum = spectrum_service.compute_spectrum(silence, sample_rate)
        
        # Spectrum should be very small
        assert np.max(spectrum) < 1e-10
    
    def test_compute_spectrum_downsampling(self, spectrum_service, sample_rate):
        """Test that spectrum is downsampled for visualization."""
        from ui_new.services.config import SPECTRUM_MAX_POINTS
        
        # Create a very long signal
        long_signal = np.random.randn(sample_rate * 60).astype(np.float32)  # 1 minute
        freqs, _ = spectrum_service.compute_spectrum(long_signal, sample_rate)
        
        # Should be downsampled
        assert len(freqs) <= SPECTRUM_MAX_POINTS


# =============================================================================
# PROFILE TESTS
# =============================================================================

class TestProfileExtended:
    """Extended tests for profile management."""
    
    def test_builtin_profiles_exist(self):
        """Test that builtin profiles exist."""
        from ui_new.profiles_new import BUILTIN_PROFILES
        
        assert 'standard' in BUILTIN_PROFILES
        assert 'fast' in BUILTIN_PROFILES
        assert 'quality' in BUILTIN_PROFILES
    
    def test_get_profile_existing(self):
        """Test getting an existing profile."""
        from ui_new.profiles_new import get_profile
        
        profile = get_profile('standard')
        assert profile is not None
        assert profile.name is not None
        assert profile.settings is not None
    
    def test_get_profile_nonexistent(self):
        """Test getting a nonexistent profile."""
        from ui_new.profiles_new import get_profile
        
        profile = get_profile('nonexistent_profile_xyz')
        assert profile is None
    
    def test_profile_manager_save_load(self, temp_dir):
        """Test profile save and load."""
        from ui_new.profiles_new import ProfileManager
        
        manager = ProfileManager(profiles_dir=temp_dir)
        
        # Save a custom profile
        manager.save_profile(
            'test_custom',
            {'block_size': 4096, 'bitrate': '320k'},
            'Custom Test Profile'
        )
        
        # Load it back
        profile = manager.get_profile('test_custom')
        assert profile is not None
        assert profile.settings['block_size'] == 4096
        assert profile.settings['bitrate'] == '320k'
    
    def test_profile_manager_list(self, temp_dir):
        """Test listing profiles."""
        from ui_new.profiles_new import ProfileManager
        
        manager = ProfileManager(profiles_dir=temp_dir)
        
        profiles = manager.get_all_profiles()
        assert 'standard' in profiles


# =============================================================================
# CONSTANTS TESTS
# =============================================================================

class TestConstantsExtended:
    """Extended tests for constants."""
    
    def test_variants_count(self):
        """Test variants count."""
        from ui_new.constants import VARIANTS
        
        assert len(VARIANTS) == 7
    
    def test_variants_suffixes_match(self):
        """Test that variants and suffixes match."""
        from ui_new.constants import VARIANTS, VARIANT_SUFFIXES
        
        for variant in VARIANTS:
            assert variant in VARIANT_SUFFIXES
    
    def test_metric_keys_structure(self):
        """Test metric keys structure."""
        from ui_new.constants import METRIC_KEYS
        
        for key, value in METRIC_KEYS.items():
            assert len(value) == 3  # (display_name, attribute, higher_is_better)
            display_name, attr, higher_better = value
            assert isinstance(display_name, str)
            assert isinstance(attr, str)
            assert isinstance(higher_better, bool)
