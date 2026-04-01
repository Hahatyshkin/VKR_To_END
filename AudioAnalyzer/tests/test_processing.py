"""
Additional tests for processing modules to increase coverage.

Focuses on:
- audio_ops module
- codecs module
- metrics module
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# =============================================================================
# METRICS MODULE TESTS - Using correct function names
# =============================================================================

class TestMetricsExtended:
    """Extended tests for metrics module."""
    
    def test_compute_snr_db_identical(self):
        """Test SNR with identical signals."""
        from processing.metrics import compute_snr_db
        
        signal = np.random.randn(1024).astype(np.float32)
        
        # Identical signals should have very high SNR
        snr_val = compute_snr_db(signal, signal)
        assert snr_val > 100 or np.isinf(snr_val)
    
    def test_compute_snr_db_different(self):
        """Test SNR with different signals."""
        from processing.metrics import compute_snr_db
        
        signal1 = np.random.randn(1024).astype(np.float32)
        signal2 = signal1 + np.random.randn(1024).astype(np.float32) * 0.1
        
        snr_val = compute_snr_db(signal1, signal2)
        assert 10 < snr_val < 50  # Reasonable range for noisy signal
    
    def test_compute_rmse_zero_identical(self):
        """Test RMSE with identical signals."""
        from processing.metrics import compute_rmse
        
        signal = np.random.randn(1024).astype(np.float32)
        
        rmse_val = compute_rmse(signal, signal)
        assert rmse_val < 1e-10
    
    def test_compute_rmse_different(self):
        """Test RMSE with different signals."""
        from processing.metrics import compute_rmse
        
        signal1 = np.ones(100, dtype=np.float32)
        signal2 = np.ones(100, dtype=np.float32) * 0.9
        
        rmse_val = compute_rmse(signal1, signal2)
        assert 0.09 < rmse_val < 0.11
    
    def test_compute_si_sdr_db_identical(self):
        """Test SI-SDR with identical signals."""
        from processing.metrics import compute_si_sdr_db
        
        signal = np.random.randn(1024).astype(np.float32)
        
        si_sdr = compute_si_sdr_db(signal, signal)
        assert si_sdr > 100 or np.isinf(si_sdr)
    
    def test_compute_lsd_db_identical(self):
        """Test LSD with identical signals."""
        from processing.metrics import compute_lsd_db
        
        signal = np.random.randn(2048).astype(np.float32)
        sr = 44100
        
        lsd = compute_lsd_db(signal, signal, sr, sr)
        assert lsd < 1e-6
    
    def test_compute_spectral_convergence_identical(self):
        """Test spectral convergence with identical signals."""
        from processing.metrics import compute_spectral_convergence
        
        signal = np.random.randn(2048).astype(np.float32)
        sr = 44100
        
        sc = compute_spectral_convergence(signal, signal, sr, sr)
        assert sc < 1e-6
    
    def test_compute_spectral_cosine_similarity_identical(self):
        """Test spectral cosine similarity with identical signals."""
        from processing.metrics import compute_spectral_cosine_similarity
        
        signal = np.random.randn(2048).astype(np.float32)
        sr = 44100
        
        cosine = compute_spectral_cosine_similarity(signal, signal, sr, sr)
        assert cosine > 0.999
    
    def test_compute_spectral_centroid_diff_identical(self):
        """Test spectral centroid difference with identical signals."""
        from processing.metrics import compute_spectral_centroid_diff_hz
        
        signal = np.random.randn(2048).astype(np.float32)
        sr = 44100
        
        diff = compute_spectral_centroid_diff_hz(signal, signal, sr, sr)
        assert diff < 1.0  # Should be very small
    
    def test_metrics_empty_signals(self):
        """Test metrics with empty signals."""
        from processing.metrics import compute_snr_db, compute_rmse, compute_si_sdr_db
        
        empty = np.array([], dtype=np.float32)
        
        assert np.isnan(compute_snr_db(empty, empty))
        assert np.isnan(compute_rmse(empty, empty))
        assert np.isnan(compute_si_sdr_db(empty, empty))
    
    def test_metrics_different_lengths(self):
        """Test metrics with different length signals."""
        from processing.metrics import compute_snr_db, compute_rmse
        
        short = np.random.randn(100).astype(np.float32)
        long = np.random.randn(500).astype(np.float32)
        
        # Should handle different lengths
        snr = compute_snr_db(short, long)
        rmse = compute_rmse(short, long)
        
        assert not np.isnan(snr)
        assert not np.isnan(rmse)


# =============================================================================
# CODECS MODULE TESTS
# =============================================================================

class TestCodecsExtended:
    """Extended tests for codecs module."""
    
    def test_module_imports(self):
        """Test that codecs module can be imported."""
        from processing import codecs
        assert codecs is not None
    
    def test_configure_ffmpeg_exists(self):
        """Test that configure_ffmpeg_search function exists."""
        from processing.codecs import configure_ffmpeg_search
        assert callable(configure_ffmpeg_search)
    
    def test_decode_audio_function_exists(self):
        """Test that decode_audio_to_mono function exists."""
        from processing.codecs import decode_audio_to_mono
        assert callable(decode_audio_to_mono)
    
    def test_load_wav_function_exists(self):
        """Test that load_wav_mono function exists."""
        from processing.codecs import load_wav_mono
        assert callable(load_wav_mono)


# =============================================================================
# AUDIO OPS MODULE TESTS
# =============================================================================

class TestAudioOps:
    """Tests for audio operations module."""
    
    def test_module_imports(self):
        """Test that audio_ops module can be imported."""
        from processing import audio_ops
        assert audio_ops is not None
    
    def test_module_has_functions(self):
        """Test that audio_ops has expected functions."""
        from processing import audio_ops
        
        expected_funcs = [
            'fwht_transform_and_mp3',
            'fft_transform_and_mp3',
            'dct_transform_and_mp3',
            'wavelet_transform_and_mp3',
            'huffman_like_transform_and_mp3',
            'rosenbrock_like_transform_and_mp3',
            'standard_convert_to_mp3',
        ]
        
        for func_name in expected_funcs:
            assert hasattr(audio_ops, func_name), f"Missing function: {func_name}"


# =============================================================================
# TRANSFORMS MODULE TESTS
# =============================================================================

class TestTransforms:
    """Tests for transform modules."""
    
    def test_fwht_module_imports(self):
        """Test that fwht module can be imported."""
        from processing.transforms import fwht
        assert fwht is not None
    
    def test_fft_module_imports(self):
        """Test that fft module can be imported."""
        from processing.transforms import fft
        assert fft is not None
    
    def test_dct_module_imports(self):
        """Test that dct module can be imported."""
        from processing.transforms import dct
        assert dct is not None
    
    def test_dwt_module_imports(self):
        """Test that dwt module can be imported."""
        from processing.transforms import dwt
        assert dwt is not None
    
    def test_huffman_module_imports(self):
        """Test that huffman module can be imported."""
        from processing.transforms import huffman
        assert huffman is not None
    
    def test_rosenbrock_module_imports(self):
        """Test that rosenbrock module can be imported."""
        from processing.transforms import rosenbrock
        assert rosenbrock is not None
    
    def test_base_module_imports(self):
        """Test that base module can be imported."""
        from processing.transforms import base
        assert base is not None


# =============================================================================
# FWHT TRANSFORM DETAILED TESTS
# =============================================================================

class TestFWHTDetailed:
    """Detailed tests for FWHT transform."""
    
    def test_fwht_basic(self):
        """Test basic FWHT operation."""
        from processing.transforms.fwht import fwht
        
        signal = np.random.randn(256).astype(np.float32)
        coeffs = fwht(signal)
        
        assert coeffs.shape == signal.shape
    
    def test_ifwht_basic(self):
        """Test basic IFWHT operation."""
        from processing.transforms.fwht import ifwht
        
        coeffs = np.random.randn(256).astype(np.float32)
        signal = ifwht(coeffs)
        
        assert signal.shape == coeffs.shape
    
    def test_fwht_ortho(self):
        """Test orthonormal FWHT."""
        from processing.transforms.fwht import fwht_ortho
        
        signal = np.random.randn(256).astype(np.float32)
        coeffs = fwht_ortho(signal)
        
        # Energy should be preserved
        energy_in = np.sum(signal ** 2)
        energy_out = np.sum(coeffs ** 2)
        assert abs(energy_in - energy_out) < 1e-3
    
    def test_fwht_roundtrip(self):
        """Test FWHT roundtrip."""
        from processing.transforms.fwht import fwht, ifwht
        
        original = np.random.randn(128).astype(np.float32)
        coeffs = fwht(original)
        reconstructed = ifwht(coeffs)
        
        np.testing.assert_array_almost_equal(original, reconstructed, decimal=5)


# =============================================================================
# FFT TRANSFORM DETAILED TESTS
# =============================================================================

class TestFFTDetailed:
    """Detailed tests for FFT transform."""
    
    def test_fft_forward(self):
        """Test FFT forward operation."""
        from processing.transforms.fft import fft_forward
        
        signal = np.random.randn(256).astype(np.float32)
        spectrum = fft_forward(signal)
        
        # rFFT output should have same length for our implementation
        assert len(spectrum) >= 128  # At least half the signal
    
    def test_fft_inverse(self):
        """Test FFT inverse operation."""
        from processing.transforms.fft import fft_forward, fft_inverse
        
        original = np.random.randn(256).astype(np.float32)
        spectrum = fft_forward(original)
        reconstructed = fft_inverse(spectrum, len(original))
        
        np.testing.assert_array_almost_equal(original, reconstructed, decimal=5)


# =============================================================================
# DCT TRANSFORM DETAILED TESTS
# =============================================================================

class TestDCTDetailed:
    """Detailed tests for DCT transform."""
    
    def test_dct2_basic(self):
        """Test DCT-II operation."""
        from processing.transforms.dct import dct2
        
        signal = np.random.randn(256).astype(np.float32)
        coeffs = dct2(signal)
        
        assert coeffs.shape == signal.shape
    
    def test_idct3_basic(self):
        """Test IDCT-III operation."""
        from processing.transforms.dct import idct3
        
        coeffs = np.random.randn(256).astype(np.float32)
        signal = idct3(coeffs)
        
        assert signal.shape == coeffs.shape


# =============================================================================
# DWT TRANSFORM DETAILED TESTS
# =============================================================================

class TestDWTDetailed:
    """Detailed tests for DWT transform."""
    
    def test_haar_dwt_1level(self):
        """Test single-level Haar DWT."""
        from processing.transforms.dwt import haar_dwt_1level
        
        signal = np.random.randn(256).astype(np.float32)
        a, d = haar_dwt_1level(signal)
        
        # Approximation and detail should each be half the length
        expected_len = (len(signal) + 1) // 2
        assert len(a) == expected_len
        assert len(d) == expected_len
    
    def test_haar_idwt_1level(self):
        """Test single-level inverse Haar DWT."""
        from processing.transforms.dwt import haar_dwt_1level, haar_idwt_1level
        
        original = np.random.randn(256).astype(np.float32)
        a, d = haar_dwt_1level(original)
        reconstructed = haar_idwt_1level(a, d, len(original))
        
        np.testing.assert_array_almost_equal(original, reconstructed, decimal=5)
    
    def test_dwt_decompose(self):
        """Test multi-level DWT decomposition."""
        from processing.transforms.dwt import dwt_decompose
        
        signal = np.random.randn(256).astype(np.float32)
        coeffs = dwt_decompose(signal, levels=3)
        
        # Should have levels + 1 coefficient arrays
        assert len(coeffs) == 4


# =============================================================================
# HUFFMAN TRANSFORM DETAILED TESTS
# =============================================================================

class TestHuffmanDetailed:
    """Detailed tests for Huffman-like transform."""
    
    def test_mulaw_compress(self):
        """Test μ-law compression."""
        from processing.transforms.huffman import mulaw_compress
        
        signal = np.array([0.0, 0.5, 1.0, -0.5, -1.0], dtype=np.float32)
        compressed = mulaw_compress(signal, mu=255.0)
        
        assert len(compressed) == len(signal)
    
    def test_mulaw_expand(self):
        """Test μ-law expansion."""
        from processing.transforms.huffman import mulaw_expand
        
        compressed = np.array([0.0, 0.5, 0.9, -0.5, -0.9], dtype=np.float32)
        expanded = mulaw_expand(compressed, mu=255.0)
        
        assert len(expanded) == len(compressed)
        # Output should be in [-1, 1]
        assert np.all(np.abs(expanded) <= 1.0)
    
    def test_mulaw_roundtrip(self):
        """Test μ-law roundtrip."""
        from processing.transforms.huffman import mulaw_compress, mulaw_expand
        
        original = np.array([0.0, 0.3, 0.7, -0.2, -0.8], dtype=np.float32)
        compressed = mulaw_compress(original, mu=255.0)
        expanded = mulaw_expand(compressed, mu=255.0)
        
        np.testing.assert_array_almost_equal(original, expanded, decimal=2)


# =============================================================================
# ROSENBROCK TRANSFORM DETAILED TESTS
# =============================================================================

class TestRosenbrockDetailed:
    """Detailed tests for Rosenbrock-like transform."""
    
    def test_rosenbrock_nonlinear(self):
        """Test Rosenbrock nonlinearity."""
        from processing.transforms.rosenbrock import rosenbrock_nonlinear
        
        signal = np.array([0.5, 0.7, 0.9], dtype=np.float32)
        result = rosenbrock_nonlinear(signal, alpha=0.2, beta=1.0)
        
        # Result should be different from input
        assert not np.allclose(result, signal)
    
    def test_normalize_peak(self):
        """Test peak normalization."""
        from processing.transforms.rosenbrock import normalize_peak
        
        signal = np.array([0.5, 1.5, 2.0], dtype=np.float32)
        normalized = normalize_peak(signal)
        
        # Peak should be 1.0
        assert abs(np.max(np.abs(normalized)) - 1.0) < 1e-5
    
    def test_rosenbrock_process(self):
        """Test full Rosenbrock process."""
        from processing.transforms.rosenbrock import rosenbrock_process
        
        signal = np.random.randn(100).astype(np.float32)
        result = rosenbrock_process(signal, alpha=0.5, beta=0.5)
        
        # Result should be normalized
        assert np.max(np.abs(result)) <= 1.0
