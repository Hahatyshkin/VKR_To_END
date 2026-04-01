"""
Tests for new Phase 4 features.

Tests verify:
- PDF Report generation
- 3D Spectrogram widget
- ML Integration
- Audio Editor
"""
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPDFReport:
    """Tests for PDF report generation."""
    
    def test_has_reportlab_check(self):
        """Test HAS_REPORTLAB constant."""
        from ui_new.reports import HAS_REPORTLAB
        
        # Should be a boolean
        assert isinstance(HAS_REPORTLAB, bool)
    
    def test_report_generator_pdf_available_property(self):
        """Test pdf_available property."""
        from ui_new.reports import ReportGenerator, HAS_REPORTLAB
        
        generator = ReportGenerator()
        
        assert generator.pdf_available == HAS_REPORTLAB
    
    def test_report_generator_is_pdf_available(self):
        """Test static is_pdf_available method."""
        from ui_new.reports import ReportGenerator, HAS_REPORTLAB
        
        assert ReportGenerator.is_pdf_available() == HAS_REPORTLAB
    
    def test_generate_pdf_without_reportlab(self):
        """Test PDF generation without reportlab raises error."""
        from ui_new.reports import ReportGenerator, HAS_REPORTLAB, ReportFormat
        
        generator = ReportGenerator()
        
        if not HAS_REPORTLAB:
            with pytest.raises(ImportError):
                generator.generate([], format=ReportFormat.PDF)
    
    def test_save_pdf(self):
        """Test saving PDF to file."""
        from ui_new.reports import ReportGenerator, HAS_REPORTLAB
        
        generator = ReportGenerator()
        
        if not HAS_REPORTLAB:
            pytest.skip("reportlab not installed")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.pdf"
            
            result = generator.save_pdf([], str(output_path))
            
            # Should succeed if reportlab is available
            assert result is True


class Test3DSpectrogram:
    """Tests for 3D Spectrogram widget."""
    
    def test_has_matplotlib_3d_check(self):
        """Test HAS_MATPLOTLIB_3D constant."""
        from ui_new.widgets.spectrogram_3d import HAS_MATPLOTLIB_3D
        
        assert isinstance(HAS_MATPLOTLIB_3D, bool)
    
    def test_create_fallback_widget(self):
        """Test creating fallback widget."""
        from ui_new.widgets.spectrogram_3d import (
            Spectrogram3DWidgetFallback,
            create_3d_spectrogram_widget,
        )
        
        # Should always be able to create fallback
        widget = Spectrogram3DWidgetFallback()
        assert widget is not None
    
    def test_create_widget_factory(self):
        """Test factory function."""
        from ui_new.widgets.spectrogram_3d import create_3d_spectrogram_widget
        
        widget = create_3d_spectrogram_widget()
        assert widget is not None
    
    def test_available_colormaps(self):
        """Test getting available colormaps."""
        from ui_new.widgets.spectrogram_3d import HAS_MATPLOTLIB_3D
        
        if HAS_MATPLOTLIB_3D:
            from ui_new.widgets.spectrogram_3d import Spectrogram3DWidget
            
            widget = Spectrogram3DWidget()
            colormaps = widget.get_available_colormaps()
            
            assert isinstance(colormaps, list)
            assert len(colormaps) > 0
            assert 'viridis' in colormaps


class TestMLIntegration:
    """Tests for ML Integration."""
    
    def test_audio_type_enum(self):
        """Test AudioType enum."""
        from ui_new.ml_integration import AudioType
        
        assert AudioType.SPEECH
        assert AudioType.MUSIC
        assert AudioType.NOISE
        assert AudioType.MIXED
        assert AudioType.SILENCE
    
    def test_classification_result(self):
        """Test ClassificationResult dataclass."""
        from ui_new.ml_integration import ClassificationResult, AudioType
        
        result = ClassificationResult(
            audio_type=AudioType.MUSIC,
            confidence=0.85,
            probabilities={'music': 0.85, 'speech': 0.15}
        )
        
        assert result.audio_type == AudioType.MUSIC
        assert result.confidence == 0.85
        assert 'music' in result.probabilities
        
        d = result.to_dict()
        assert d['audio_type'] == 'music'
    
    def test_quality_prediction(self):
        """Test QualityPrediction dataclass."""
        from ui_new.ml_integration import QualityPrediction
        
        prediction = QualityPrediction(
            predicted_snr=25.0,
            predicted_lsd=1.5,
            quality_score=85.0,
            recommendations=["Good quality"]
        )
        
        assert prediction.predicted_snr == 25.0
        assert prediction.quality_score == 85.0
        
        d = prediction.to_dict()
        assert d['predicted_snr'] == 25.0
    
    def test_feature_extractor(self):
        """Test AudioFeatureExtractor."""
        from ui_new.ml_integration import AudioFeatureExtractor
        
        # Создаём тестовый сигнал
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        features = AudioFeatureExtractor.extract_features(signal, sample_rate)
        
        assert 'rms' in features
        assert 'spectral_centroid' in features
        assert 'mfcc_mean' in features
        
        assert features['rms'] > 0
        assert features['spectral_centroid'] > 0
        
        # Feature vector
        vector = AudioFeatureExtractor.extract_feature_vector(signal, sample_rate)
        
        assert isinstance(vector, np.ndarray)
        assert len(vector) > 0
    
    def test_audio_classifier(self):
        """Test AudioClassifier."""
        from ui_new.ml_integration import AudioClassifier, AudioType
        
        classifier = AudioClassifier()
        
        assert classifier.name == "AudioClassifier"
        assert classifier.version == "1.0.0"
        assert classifier.is_loaded()
        
        # Тестовый сигнал
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Синусоида (музыкальный сигнал)
        music_signal = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        result = classifier.classify(music_signal, sample_rate)
        
        assert isinstance(result.audio_type, AudioType)
        assert 0 <= result.confidence <= 1
    
    def test_quality_predictor(self):
        """Test QualityPredictor."""
        from ui_new.ml_integration import QualityPredictor
        
        predictor = QualityPredictor()
        
        assert predictor.name == "QualityPredictor"
        assert predictor.is_loaded()
        
        # Тестовый сигнал
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        result = predictor.predict_quality(signal, sample_rate)
        
        assert result.predicted_snr >= 0
        assert 0 <= result.quality_score <= 100
        assert len(result.recommendations) > 0
    
    def test_model_registry(self):
        """Test MLModelRegistry."""
        from ui_new.ml_integration import MLModelRegistry
        
        MLModelRegistry.initialize()
        
        # Check available models
        models = MLModelRegistry.get_available_models()
        
        assert 'audio_classifier' in models
        assert 'quality_predictor' in models
        
        # Get model
        classifier = MLModelRegistry.get('audio_classifier')
        assert classifier is not None
    
    def test_classify_audio_function(self):
        """Test classify_audio convenience function."""
        from ui_new.ml_integration import classify_audio
        
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        result = classify_audio(signal, sample_rate)
        
        assert result.audio_type is not None
    
    def test_predict_audio_quality_function(self):
        """Test predict_audio_quality convenience function."""
        from ui_new.ml_integration import predict_audio_quality
        
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        result = predict_audio_quality(signal, sample_rate)
        
        assert result.quality_score >= 0


class TestAudioEditor:
    """Tests for Audio Editor."""
    
    def test_edit_operation_enum(self):
        """Test EditOperation enum."""
        from ui_new.audio_editor import EditOperation
        
        assert EditOperation.TRIM
        assert EditOperation.NORMALIZE
        assert EditOperation.FADE_IN
        assert EditOperation.FADE_OUT
    
    def test_export_format_enum(self):
        """Test ExportFormat enum."""
        from ui_new.audio_editor import ExportFormat
        
        assert ExportFormat.WAV
        assert ExportFormat.MP3
        assert ExportFormat.FLAC
    
    def test_edit_result(self):
        """Test EditResult dataclass."""
        from ui_new.audio_editor import EditResult, EditOperation
        
        result = EditResult(
            signal=np.zeros(1000),
            sample_rate=44100,
            operation=EditOperation.NORMALIZE,
            success=True,
            message="OK"
        )
        
        assert result.success is True
        assert result.operation == EditOperation.NORMALIZE
        
        d = result.to_dict()
        assert d['success'] is True
    
    def test_trim_params(self):
        """Test TrimParams dataclass."""
        from ui_new.audio_editor import TrimParams
        
        params = TrimParams(start_time=1.0, end_time=5.0)
        
        start, end = params.validate(10.0)
        
        assert start == 1.0
        assert end == 5.0
    
    def test_trim_params_validation(self):
        """Test TrimParams validation."""
        from ui_new.audio_editor import TrimParams
        
        params = TrimParams(start_time=10.0, end_time=5.0)
        
        with pytest.raises(ValueError):
            params.validate(20.0)
    
    def test_fade_params(self):
        """Test FadeParams dataclass."""
        from ui_new.audio_editor import FadeParams
        
        params = FadeParams(duration=2.0, curve="exponential")
        
        curve = params.get_curve()
        
        assert len(curve) > 0
        assert curve[-1] > curve[0]  # Curve should increase
    
    def test_audio_editor_trim(self):
        """Test AudioEditor trim operation."""
        from ui_new.audio_editor import AudioEditor, EditOperation
        
        editor = AudioEditor()
        
        sample_rate = 44100
        signal = np.random.randn(sample_rate * 5).astype(np.float32)  # 5 seconds
        
        result = editor.apply(
            signal, sample_rate, EditOperation.TRIM,
            start_time=1.0, end_time=3.0
        )
        
        assert result.success
        assert len(result.signal) == sample_rate * 2  # 2 seconds
    
    def test_audio_editor_normalize(self):
        """Test AudioEditor normalize operation."""
        from ui_new.audio_editor import AudioEditor, EditOperation
        
        editor = AudioEditor()
        
        sample_rate = 44100
        signal = np.random.randn(sample_rate).astype(np.float32) * 0.1
        
        result = editor.apply(
            signal, sample_rate, EditOperation.NORMALIZE,
            target_db=-3.0
        )
        
        assert result.success
        
        # Peak should be near -3dB
        peak = np.max(np.abs(result.signal))
        expected_peak = 10 ** (-3.0 / 20)
        assert abs(peak - expected_peak) < 0.01
    
    def test_audio_editor_fade_in(self):
        """Test AudioEditor fade in operation."""
        from ui_new.audio_editor import AudioEditor, EditOperation
        
        editor = AudioEditor()
        
        sample_rate = 44100
        signal = np.ones(sample_rate).astype(np.float32)
        
        result = editor.apply(
            signal, sample_rate, EditOperation.FADE_IN,
            duration=0.1
        )
        
        assert result.success
        
        # First sample should be near 0
        assert abs(result.signal[0]) < 0.1
    
    def test_audio_editor_fade_out(self):
        """Test AudioEditor fade out operation."""
        from ui_new.audio_editor import AudioEditor, EditOperation
        
        editor = AudioEditor()
        
        sample_rate = 44100
        signal = np.ones(sample_rate).astype(np.float32)
        
        result = editor.apply(
            signal, sample_rate, EditOperation.FADE_OUT,
            duration=0.1
        )
        
        assert result.success
        
        # Last sample should be near 0
        assert abs(result.signal[-1]) < 0.1
    
    def test_audio_editor_reverse(self):
        """Test AudioEditor reverse operation."""
        from ui_new.audio_editor import AudioEditor, EditOperation
        
        editor = AudioEditor()
        
        sample_rate = 44100
        signal = np.arange(10).astype(np.float32)
        
        result = editor.apply(
            signal, sample_rate, EditOperation.REVERSE
        )
        
        assert result.success
        np.testing.assert_array_equal(result.signal, signal[::-1])
    
    def test_audio_editor_amplify(self):
        """Test AudioEditor amplify operation."""
        from ui_new.audio_editor import AudioEditor, EditOperation
        
        editor = AudioEditor()
        
        sample_rate = 44100
        signal = np.ones(1000).astype(np.float32) * 0.5
        
        # +6dB = 2x gain
        result = editor.apply(
            signal, sample_rate, EditOperation.AMPLIFY,
            gain_db=6.0
        )
        
        assert result.success
        assert np.allclose(result.signal, signal * 2, atol=0.01)
    
    def test_audio_editor_chain(self):
        """Test AudioEditor apply_chain."""
        from ui_new.audio_editor import AudioEditor, EditOperation
        
        editor = AudioEditor()
        
        sample_rate = 44100
        signal = np.random.randn(sample_rate * 2).astype(np.float32)
        
        operations = [
            (EditOperation.NORMALIZE, {'target_db': -6.0}),
            (EditOperation.FADE_IN, {'duration': 0.1}),
            (EditOperation.FADE_OUT, {'duration': 0.1}),
        ]
        
        result = editor.apply_chain(signal, sample_rate, operations)
        
        assert result.success
    
    def test_export_wav(self):
        """Test WAV export."""
        from ui_new.audio_editor import AudioEditor
        
        editor = AudioEditor()
        
        sample_rate = 44100
        signal = np.random.randn(sample_rate).astype(np.float32) * 0.5
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.wav"
            
            result = editor.export(signal, sample_rate, str(output_path))
            
            assert result
            assert output_path.exists()
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        from ui_new.audio_editor import (
            trim_audio, normalize_audio, apply_fade
        )
        
        sample_rate = 44100
        signal = np.random.randn(sample_rate * 3).astype(np.float32)
        
        # trim
        trimmed = trim_audio(signal, sample_rate, 1.0, 2.0)
        assert len(trimmed) == sample_rate
        
        # normalize
        normalized = normalize_audio(signal, sample_rate, -3.0)
        assert len(normalized) == len(signal)
        
        # fade
        faded = apply_fade(signal, sample_rate, 0.1, 0.1)
        assert len(faded) == len(signal)


class TestExports:
    """Tests for module exports."""
    
    def test_reports_exports(self):
        """Test reports module exports."""
        from ui_new.reports import __all__
        
        assert "ReportGenerator" in __all__
        assert "ReportFormat" in __all__
        assert "HAS_REPORTLAB" in __all__
    
    def test_spectrogram_3d_exports(self):
        """Test spectrogram_3d module exports."""
        from ui_new.widgets.spectrogram_3d import __all__
        
        assert "Spectrogram3DWidget" in __all__
        assert "create_3d_spectrogram_widget" in __all__
    
    def test_ml_integration_exports(self):
        """Test ml_integration module exports."""
        from ui_new.ml_integration import __all__
        
        assert "AudioClassifier" in __all__
        assert "QualityPredictor" in __all__
        assert "MLModelRegistry" in __all__
    
    def test_audio_editor_exports(self):
        """Test audio_editor module exports."""
        from ui_new.audio_editor import __all__
        
        assert "AudioEditor" in __all__
        assert "EditOperation" in __all__
        assert "ExportFormat" in __all__
