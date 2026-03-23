"""
pytest configuration and fixtures for AudioAnalyzer tests.

Provides shared fixtures for:
- Audio signal generation
- Mock objects
- Test configuration
- Temporary files
"""
import tempfile
from pathlib import Path
from typing import Generator

import numpy as np
import pytest

# Add src to path
import sys
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# =============================================================================
# AUDIO SIGNAL FIXTURES
# =============================================================================

@pytest.fixture
def sample_rate() -> int:
    """Standard sample rate for tests."""
    return 44100


@pytest.fixture
def duration_sec() -> float:
    """Standard duration for test signals."""
    return 1.0


@pytest.fixture
def sine_signal(sample_rate: int, duration_sec: float) -> np.ndarray:
    """Generate a sine wave signal at 440 Hz."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), dtype=np.float32)
    return np.sin(2 * np.pi * 440 * t)


@pytest.fixture
def sine_signal_1k(sample_rate: int, duration_sec: float) -> np.ndarray:
    """Generate a sine wave signal at 1000 Hz."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), dtype=np.float32)
    return np.sin(2 * np.pi * 1000 * t)


@pytest.fixture
def multi_tone_signal(sample_rate: int, duration_sec: float) -> np.ndarray:
    """Generate a multi-tone signal (A major chord: A, C#, E)."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), dtype=np.float32)
    return (
        np.sin(2 * np.pi * 440 * t) +   # A4
        np.sin(2 * np.pi * 554.37 * t) +  # C#5
        np.sin(2 * np.pi * 659.25 * t)    # E5
    ).astype(np.float32) / 3


@pytest.fixture
def white_noise(sample_rate: int, duration_sec: float) -> np.ndarray:
    """Generate white noise signal."""
    np.random.seed(42)
    return np.random.randn(int(sample_rate * duration_sec)).astype(np.float32) * 0.1


@pytest.fixture
def pink_noise(sample_rate: int, duration_sec: float) -> np.ndarray:
    """Generate pink noise (1/f noise) signal."""
    np.random.seed(42)
    n_samples = int(sample_rate * duration_sec)
    # Pink noise: decrease power by 3dB per octave
    white = np.random.randn(n_samples)
    # Simple approximation using first-order filter
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    from scipy import signal as sig
    pink = sig.lfilter(b, a, white)
    return pink.astype(np.float32) * 0.1


@pytest.fixture
def silence(sample_rate: int, duration_sec: float) -> np.ndarray:
    """Generate silence (all zeros)."""
    return np.zeros(int(sample_rate * duration_sec), dtype=np.float32)


@pytest.fixture
def impulse_signal(sample_rate: int) -> np.ndarray:
    """Generate impulse signal for impulse response testing."""
    signal = np.zeros(sample_rate, dtype=np.float32)  # 1 second
    signal[0] = 1.0
    return signal


@pytest.fixture
def chirp_signal(sample_rate: int, duration_sec: float) -> np.ndarray:
    """Generate chirp signal (frequency sweep)."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), dtype=np.float32)
    # Linear chirp from 20 Hz to 20 kHz
    f0, f1 = 20, 20000
    return np.sin(2 * np.pi * (f0 * t + (f1 - f0) / (2 * duration_sec) * t**2)).astype(np.float32)


# =============================================================================
# POWER-OF-TWO SIGNAL FIXTURES (for transforms like FWHT)
# =============================================================================

@pytest.fixture(params=[64, 128, 256, 512, 1024, 2048])
def power_of_two_length(request) -> int:
    """Power-of-two lengths for transform testing."""
    return request.param


@pytest.fixture
def random_signal_power2(power_of_two_length: int) -> np.ndarray:
    """Random signal with power-of-two length."""
    np.random.seed(42)
    return np.random.randn(power_of_two_length).astype(np.float32)


# =============================================================================
# TEMPORARY FILES AND DIRECTORIES
# =============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_wav_file(temp_dir: Path, sine_signal: np.ndarray, sample_rate: int) -> Path:
    """Create a temporary WAV file with a sine signal."""
    import soundfile as sf
    filepath = temp_dir / "test_signal.wav"
    sf.write(str(filepath), sine_signal, sample_rate)
    return filepath


@pytest.fixture
def temp_mp3_file(temp_dir: Path, sine_signal: np.ndarray, sample_rate: int) -> Path:
    """Create a temporary MP3 file using pydub."""
    from pydub import AudioSegment
    import soundfile as sf
    
    # First create WAV
    wav_path = temp_dir / "temp.wav"
    sf.write(str(wav_path), sine_signal, sample_rate)
    
    # Convert to MP3
    mp3_path = temp_dir / "test_signal.mp3"
    audio = AudioSegment.from_wav(str(wav_path))
    audio.export(str(mp3_path), format="mp3", bitrate="192k")
    
    # Clean up temp WAV
    wav_path.unlink()
    
    return mp3_path


@pytest.fixture
def temp_profile_file(temp_dir: Path) -> Path:
    """Create a temporary profile JSON file."""
    import json
    profile = {
        "name": "Test Profile",
        "settings": {
            "block_size": 2048,
            "bitrate": "192k",
            "method": "fwht"
        }
    }
    filepath = temp_dir / "test_profile.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(profile, f)
    return filepath


# =============================================================================
# MOCK FIXTURES
# =============================================================================

@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    from unittest.mock import MagicMock
    config = MagicMock()
    config.project_root = Path("/tmp/audio_analyzer_test")
    config.log_level = "DEBUG"
    config.max_workers = 4
    return config


@pytest.fixture
def mock_container(mock_config):
    """Create a mock service container."""
    from unittest.mock import MagicMock
    container = MagicMock()
    container.config = mock_config
    return container


@pytest.fixture
def mock_qapplication():
    """Create a mock QApplication for UI tests."""
    from unittest.mock import MagicMock, patch
    with patch('PySide6.QtWidgets.QApplication') as mock_app:
        mock_app.instance.return_value = None
        mock_app.return_value = MagicMock()
        yield mock_app


# =============================================================================
# SERVICE FIXTURES
# =============================================================================

@pytest.fixture
def reset_container():
    """Reset the service container before and after each test."""
    from ui_new.services import reset_container as _reset
    _reset()
    yield
    _reset()


@pytest.fixture
def service_container(reset_container):
    """Provide a fresh service container."""
    from ui_new.services import ServiceContainer
    return ServiceContainer()


@pytest.fixture
def file_service(service_container):
    """Provide a FileService instance."""
    from ui_new.services.file_service import FileService
    return FileService(service_container.config)


@pytest.fixture
def spectrum_service(service_container):
    """Provide a SpectrumService instance."""
    from ui_new.services.spectrum_service import SpectrumService
    return SpectrumService(service_container.config)


@pytest.fixture
def audio_service(service_container):
    """Provide an AudioProcessingService instance."""
    from ui_new.services.audio_service import AudioProcessingService
    return AudioProcessingService(service_container.config)


# =============================================================================
# MARKERS
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "ui: marks tests that require UI (pytest-qt)"
    )
    config.addinivalue_line(
        "markers", "requires_audio: marks tests that require audio files"
    )


# =============================================================================
# SKIP CONDITIONS
# =============================================================================

def pytest_collection_modifyitems(config, items):
    """Skip tests based on markers and conditions."""
    skip_slow = pytest.mark.skip(reason="need -m slow option to run")
    skip_ui = pytest.mark.skip(reason="need display for UI tests")
    
    for item in items:
        # Skip slow tests unless explicitly requested
        if "slow" in item.keywords and not config.getoption("-m", default=""):
            item.add_marker(skip_slow)
        
        # Skip UI tests if no display
        if "ui" in item.keywords:
            import os
            if not os.environ.get("DISPLAY") and not os.environ.get("QT_QPA_PLATFORM"):
                item.add_marker(skip_ui)
