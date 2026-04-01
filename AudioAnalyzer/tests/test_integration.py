"""
Интеграционные тесты для AudioAnalyzer.

Тестирует:
- Полный пайплайн обработки
- Взаимодействие сервисов
- CLI функциональность
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Добавляем путь к src
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# =============================================================================
# ТЕСТЫ СЕРВИСОВ
# =============================================================================

class TestServiceContainer(unittest.TestCase):
    """Тесты DI контейнера."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
        from ui_new.services import reset_container
        reset_container()
    
    def tearDown(self):
        """Очистка после каждого теста."""
        from ui_new.services import reset_container
        reset_container()
    
    def test_container_initialization(self):
        """Тест инициализации контейнера."""
        from ui_new.services import ServiceContainer, init_container
        
        container = init_container()
        
        self.assertIsNotNone(container.config)
        self.assertIsNotNone(container.config.project_root)
    
    def test_get_container_singleton(self):
        """Тест получения singleton контейнера."""
        from ui_new.services import get_container, init_container
        
        init_container()
        container1 = get_container()
        container2 = get_container()
        
        self.assertIs(container1, container2)
    
    def test_config_creation(self):
        """Тест создания конфигурации."""
        from ui_new.services.config import create_app_config, PROGRESS_RANGES
        
        config = create_app_config()
        
        self.assertIsNotNone(config.project_root)
        self.assertIn('fwht', PROGRESS_RANGES)
        self.assertEqual(PROGRESS_RANGES['fwht'], (5, 55))
    
    def test_progress_ranges(self):
        """Тест диапазонов прогресса."""
        from ui_new.services.config import PROGRESS_RANGES
        
        # Проверяем что все методы имеют диапазоны
        methods = ['fwht', 'fft', 'dct', 'dwt', 'huffman', 'rosenbrock', 'standard']
        for method in methods:
            self.assertIn(method, PROGRESS_RANGES)
            start, end = PROGRESS_RANGES[method]
            self.assertGreaterEqual(start, 0)
            self.assertLessEqual(end, 100)
            self.assertLess(start, end)


class TestFileService(unittest.TestCase):
    """Тесты файлового сервиса."""
    
    def setUp(self):
        """Настройка тестов."""
        from ui_new.services import ServiceContainer, reset_container
        reset_container()
        self.container = ServiceContainer()
    
    def test_method_suffixes(self):
        """Тест суффиксов методов."""
        from ui_new.services.file_service import FileService
        
        self.assertIn('standard', FileService.METHOD_SUFFIXES)
        self.assertIn('_fwht', FileService.SUFFIX_TO_METHOD)
    
    def test_audio_extensions(self):
        """Тест поддерживаемых расширений."""
        from ui_new.services.file_service import FileService
        
        self.assertIn('.wav', FileService.AUDIO_EXTENSIONS)
        self.assertIn('.mp3', FileService.AUDIO_EXTENSIONS)
    
    def test_get_file_size(self):
        """Тест получения размера файла."""
        from ui_new.services.file_service import FileService
        
        service = FileService(self.container.config)
        
        # Несуществующий файл
        size = service.get_file_size('/nonexistent/file.wav')
        self.assertEqual(size, 0)
        
        # Существующий файл (этот тест)
        size = service.get_file_size(__file__)
        self.assertGreater(size, 0)
    
    def test_validate_audio_file(self):
        """Тест валидации аудиофайла."""
        from ui_new.services.file_service import FileService
        
        service = FileService(self.container.config)
        
        # Несуществующий файл
        is_valid, error = service.validate_audio_file('/nonexistent/file.wav')
        self.assertFalse(is_valid)
        self.assertIn('не существует', error.lower())


class TestSpectrumService(unittest.TestCase):
    """Тесты сервиса спектра."""
    
    def setUp(self):
        """Настройка тестов."""
        from ui_new.services import ServiceContainer, reset_container
        reset_container()
        self.container = ServiceContainer()
    
    def test_compute_spectrum_empty(self):
        """Тест вычисления спектра для пустого сигнала."""
        from ui_new.services.spectrum_service import SpectrumService
        import numpy as np
        
        service = SpectrumService(self.container.config)
        
        # Пустой сигнал
        freqs, spectrum = service.compute_spectrum(np.array([]), 44100)
        self.assertEqual(len(freqs), 0)
        self.assertEqual(len(spectrum), 0)
    
    def test_compute_spectrum_sine(self):
        """Тест вычисления спектра для синусоиды."""
        from ui_new.services.spectrum_service import SpectrumService
        import numpy as np
        
        service = SpectrumService(self.container.config)
        
        # Синусоида 440 Гц
        sr = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration))
        signal = np.sin(2 * np.pi * 440 * t)
        
        freqs, spectrum = service.compute_spectrum(signal, sr)
        
        self.assertGreater(len(freqs), 0)
        self.assertEqual(len(freqs), len(spectrum))
        
        # Пик должен быть около 440 Гц
        peak_idx = np.argmax(spectrum)
        peak_freq = freqs[peak_idx]
        self.assertAlmostEqual(peak_freq, 440, delta=10)
    
    def test_downsampling(self):
        """Тест downsampling для визуализации."""
        from ui_new.services.spectrum_service import SpectrumService
        from ui_new.services.config import SPECTRUM_MAX_POINTS
        import numpy as np
        
        service = SpectrumService(self.container.config)
        
        # Большой сигнал
        sr = 44100
        signal = np.random.randn(sr * 10)  # 10 секунд
        
        freqs, spectrum = service.compute_spectrum(signal, sr)
        
        # Проверяем что количество точек не превышает максимум
        self.assertLessEqual(len(freqs), SPECTRUM_MAX_POINTS)


class TestAudioProcessingService(unittest.TestCase):
    """Тесты сервиса обработки аудио."""
    
    def setUp(self):
        """Настройка тестов."""
        from ui_new.services import ServiceContainer, reset_container
        reset_container()
        self.container = ServiceContainer()
    
    def test_get_default_settings(self):
        """Тест настроек по умолчанию."""
        from ui_new.services.audio_service import AudioProcessingService
        
        service = AudioProcessingService(self.container.config)
        settings = service.get_default_settings()
        
        self.assertIn('block_size', settings)
        self.assertEqual(settings['block_size'], 2048)
        self.assertIn('bitrate', settings)
    
    def test_validate_settings(self):
        """Тест валидации настроек."""
        from ui_new.services.audio_service import AudioProcessingService
        
        service = AudioProcessingService(self.container.config)
        
        # Валидные настройки
        is_valid, errors = service.validate_settings({
            'block_size': 2048,
            'bitrate': '192k',
        })
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Невалидный block_size (не степень двойки)
        is_valid, errors = service.validate_settings({
            'block_size': 1000,
        })
        self.assertFalse(is_valid)
    
    def test_format_eta(self):
        """Тест форматирования ETA."""
        from ui_new.services.audio_service import AudioProcessingService
        
        service = AudioProcessingService(self.container.config)
        
        self.assertEqual(service.format_eta(65), "01:05")
        self.assertEqual(service.format_eta(3665), "1:01:05")
        self.assertEqual(service.format_eta(0), "00:00")
    
    def test_method_recommendations(self):
        """Тест рекомендаций методов."""
        from ui_new.services.audio_service import AudioProcessingService
        
        service = AudioProcessingService(self.container.config)
        
        # Короткий файл
        recommendations = service.get_method_recommendations({
            'duration_sec': 5,
            'dynamic_range_db': 30,
            'spectral_centroid_hz': 2000,
            'is_speech': True,
        })
        
        self.assertGreater(len(recommendations), 0)
        
        # Проверяем что fwht имеет высокую оценку для короткого файла
        fwht_rec = next((r for r in recommendations if r[0] == 'fwht'), None)
        self.assertIsNotNone(fwht_rec)
        self.assertGreater(fwht_rec[1], 0.7)


# =============================================================================
# ТЕСТЫ ПРОФИЛЕЙ
# =============================================================================

class TestProfiles(unittest.TestCase):
    """Тесты профилей методов."""
    
    def test_builtin_profiles(self):
        """Тест встроенных профилей."""
        from ui_new.profiles_new import BUILTIN_PROFILES
        
        self.assertIn('standard', BUILTIN_PROFILES)
        self.assertIn('fast', BUILTIN_PROFILES)
        self.assertIn('quality', BUILTIN_PROFILES)
        self.assertIn('speech', BUILTIN_PROFILES)
    
    def test_get_profile(self):
        """Тест получения профиля."""
        from ui_new.profiles_new import get_profile
        
        profile = get_profile('standard')
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, 'Стандартный')
        self.assertIn('block_size', profile.settings)
    
    def test_profile_manager(self):
        """Тест менеджера профилей."""
        from ui_new.profiles_new import ProfileManager
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProfileManager(profiles_dir=Path(tmpdir))
            
            # Получаем все профили
            all_profiles = manager.get_all_profiles()
            self.assertIn('standard', all_profiles)
            
            # Сохраняем профиль
            manager.save_profile(
                'test_profile',
                {'block_size': 1024},
                'Test profile'
            )
            
            # Загружаем обратно
            profile = manager.get_profile('test_profile')
            self.assertIsNotNone(profile)
            self.assertEqual(profile.settings['block_size'], 1024)


# =============================================================================
# ТЕСТЫ WORKER
# =============================================================================

class TestWorker(unittest.TestCase):
    """Тесты Worker."""
    
    @classmethod
    def setUpClass(cls):
        """Check if PySide6 is available."""
        try:
            import PySide6
            cls.has_pyside = True
        except ImportError:
            cls.has_pyside = False
    
    @unittest.skipUnless(hasattr(object, 'has_pyside') or True, "PySide6 required")
    def test_method_registry(self):
        """Тест реестра методов."""
        try:
            from ui_new.worker import MethodRegistry, create_default_registry
        except ImportError:
            self.skipTest("PySide6 not available")
        
        registry = create_default_registry()
        
        self.assertEqual(registry.count(), 7)
        self.assertTrue(registry.has_method('fwht'))
        self.assertTrue(registry.has_method('fft'))
        
        names = registry.get_method_names()
        self.assertIn('fwht', names)
        self.assertIn('standard', names)
    
    @unittest.skipUnless(hasattr(object, 'has_pyside') or True, "PySide6 required")
    def test_result_row(self):
        """Тест структуры результата."""
        try:
            from ui_new.worker import ResultRow
        except ImportError:
            self.skipTest("PySide6 not available")
        
        row = ResultRow(
            source='test.wav',
            genre='rock',
            variant='FWHT MP3',
            path='/output/test_fwht.mp3',
            size_bytes=1024000,
            lsd_db=1.5,
            snr_db=30.0,
            spec_conv=0.05,
            rmse=0.001,
            si_sdr_db=25.0,
            spec_centroid_diff_hz=100.0,
            spec_cosine=0.95,
            score=0.85,
            time_sec=2.5,
        )
        
        self.assertAlmostEqual(row.size_mb, 1024000 / (1024 * 1024), places=3)


# =============================================================================
# ТЕСТЫ КОНСТАНТ
# =============================================================================

class TestConstants(unittest.TestCase):
    """Тесты констант."""
    
    def test_variants(self):
        """Тест вариантов методов."""
        from ui_new.constants import VARIANTS, VARIANT_SUFFIXES
        
        self.assertEqual(len(VARIANTS), 7)
        self.assertIn('Стандартный MP3', VARIANTS)
        
        # Проверяем соответствие вариантов и суффиксов
        for variant in VARIANTS:
            self.assertIn(variant, VARIANT_SUFFIXES)
    
    def test_metric_keys(self):
        """Тест ключей метрик."""
        from ui_new.constants import METRIC_KEYS
        
        # Структура: key -> (display_name, attribute_name, higher_is_better)
        self.assertIn('lsd', METRIC_KEYS)
        self.assertIn('snr', METRIC_KEYS)
        
        # Проверяем структуру
        lsd_info = METRIC_KEYS['lsd']
        self.assertEqual(len(lsd_info), 3)
        self.assertEqual(lsd_info[0], 'LSD (дБ)')  # display_name
        self.assertEqual(lsd_info[1], 'lsd_db')   # attribute_name
        self.assertFalse(lsd_info[2])              # lower is better


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================

if __name__ == '__main__':
    unittest.main(verbosity=2)
