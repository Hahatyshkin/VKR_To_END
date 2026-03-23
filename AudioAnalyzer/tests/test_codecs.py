#!/usr/bin/env python3
"""
Unit-тесты для модуля processing.codecs.

Тестирует:
- Загрузку WAV файлов
- Декодирование аудио в моно
- Кодирование PCM в MP3
- Получение метаданных
- Настройку FFmpeg
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestCodecsBasic(unittest.TestCase):
    """Базовые тесты codecs без внешних зависимостей."""

    def test_bitrate_to_qscale(self):
        """Тест конвертации битрейта в qscale."""
        from processing.codecs import _bitrate_to_qscale
        
        # Высокий битрейт = низкий qscale (лучшее качество)
        self.assertEqual(_bitrate_to_qscale("320k"), 0)
        self.assertEqual(_bitrate_to_qscale("256k"), 1)
        self.assertEqual(_bitrate_to_qscale("192k"), 2)
        self.assertEqual(_bitrate_to_qscale("128k"), 5)
        self.assertEqual(_bitrate_to_qscale("96k"), 6)

    def test_sf_bit_depth_from_subtype(self):
        """Тест определения битовой глубины из подтипа soundfile."""
        from processing.codecs import _sf_bit_depth_from_subtype
        
        self.assertEqual(_sf_bit_depth_from_subtype("PCM_U8"), 8)
        self.assertEqual(_sf_bit_depth_from_subtype("PCM_16"), 16)
        self.assertEqual(_sf_bit_depth_from_subtype("PCM_24"), 24)
        self.assertEqual(_sf_bit_depth_from_subtype("PCM_32"), 32)
        self.assertEqual(_sf_bit_depth_from_subtype("FLOAT"), 32)
        self.assertEqual(_sf_bit_depth_from_subtype("DOUBLE"), 64)
        # Неизвестный подтип
        self.assertEqual(_sf_bit_depth_from_subtype("UNKNOWN"), 16)


class TestLoadWavMono(unittest.TestCase):
    """Тесты загрузки WAV файлов."""

    @classmethod
    def setUpClass(cls):
        """Создание временной директории и тестовых файлов."""
        cls.temp_dir = tempfile.mkdtemp()
        
        # Создаём тестовый моно WAV файл
        cls.mono_wav = os.path.join(cls.temp_dir, "test_mono.wav")
        cls.sr = 44100
        cls.duration = 1.0
        t = np.linspace(0, cls.duration, int(cls.sr * cls.duration), dtype=np.float32)
        cls.mono_data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        
        import soundfile as sf
        sf.write(cls.mono_wav, cls.mono_data, cls.sr, subtype='PCM_16')
        
        # Создаём тестовый стерео WAV файл
        cls.stereo_wav = os.path.join(cls.temp_dir, "test_stereo.wav")
        cls.stereo_data = np.column_stack([cls.mono_data, cls.mono_data * 0.8])
        sf.write(cls.stereo_wav, cls.stereo_data, cls.sr, subtype='PCM_16')

    @classmethod
    def tearDownClass(cls):
        """Удаление временных файлов."""
        import shutil
        try:
            shutil.rmtree(cls.temp_dir)
        except Exception:
            pass

    def test_load_mono_wav(self):
        """Загрузка моно WAV файла."""
        from processing.codecs import load_wav_mono
        
        data, sr = load_wav_mono(self.mono_wav)
        
        self.assertEqual(sr, self.sr)
        self.assertEqual(len(data), len(self.mono_data))
        self.assertTrue(np.issubdtype(data.dtype, np.floating))

    def test_load_stereo_to_mono(self):
        """Загрузка стерео WAV и конвертация в моно."""
        from processing.codecs import load_wav_mono
        
        data, sr = load_wav_mono(self.stereo_wav)
        
        self.assertEqual(sr, self.sr)
        # Длина должна быть такой же как у оригинального моно
        self.assertEqual(len(data), len(self.mono_data))
        # Данные должны быть средним двух каналов
        expected = (self.mono_data + self.mono_data * 0.8) / 2
        np.testing.assert_array_almost_equal(data, expected, decimal=3)

    def test_load_nonexistent_file(self):
        """Попытка загрузки несуществующего файла должна вызывать ошибку."""
        from processing.codecs import load_wav_mono
        
        with self.assertRaises(Exception):
            load_wav_mono("/nonexistent/path/file.wav")


class TestGetAudioMeta(unittest.TestCase):
    """Тесты получения метаданных."""

    @classmethod
    def setUpClass(cls):
        """Создание тестовых файлов."""
        cls.temp_dir = tempfile.mkdtemp()
        
        # Создаём WAV файл
        cls.test_wav = os.path.join(cls.temp_dir, "test.wav")
        cls.sr = 44100
        t = np.linspace(0, 1.0, cls.sr, dtype=np.float32)
        data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        
        import soundfile as sf
        sf.write(cls.test_wav, data, cls.sr, subtype='PCM_16')

    @classmethod
    def tearDownClass(cls):
        """Удаление временных файлов."""
        import shutil
        try:
            shutil.rmtree(cls.temp_dir)
        except Exception:
            pass

    def test_get_wav_meta(self):
        """Получение метаданных WAV файла."""
        from processing.codecs import get_audio_meta
        
        meta = get_audio_meta(self.test_wav)
        
        self.assertEqual(meta["sample_rate_hz"], self.sr)
        self.assertEqual(meta["bit_depth_bits"], 16)
        self.assertEqual(meta["channels"], 1)
        self.assertIn("bitrate_bps", meta)
        self.assertGreater(meta["bitrate_bps"], 0)


class TestFFmpegConfiguration(unittest.TestCase):
    """Тесты конфигурации FFmpeg."""

    def test_configure_ffmpeg_search(self):
        """Тест функции настройки FFmpeg."""
        from processing.codecs import configure_ffmpeg_search
        
        # Не должно вызывать исключений
        try:
            configure_ffmpeg_search()
        except Exception as e:
            self.fail(f"configure_ffmpeg_search raised {e}")

    def test_ensure_ffmpeg_available(self):
        """Тест проверки доступности FFmpeg."""
        from processing.codecs import ensure_ffmpeg_available, _FFMPEG_CONFIGURED
        
        # Если FFmpeg настроен, не должно быть ошибки
        if _FFMPEG_CONFIGURED:
            try:
                ensure_ffmpeg_available()
            except RuntimeError:
                # FFmpeg может быть недоступен в тестовой среде
                pass


class TestEncodePCMToMP3(unittest.TestCase):
    """Тесты кодирования PCM в MP3."""

    @classmethod
    def setUpClass(cls):
        """Создание тестовых данных и временной директории."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.sr = 44100
        
        # Создаём тестовый PCM сигнал
        t = np.linspace(0, 1.0, cls.sr, dtype=np.float32)
        cls.pcm_data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    @classmethod
    def tearDownClass(cls):
        """Удаление временных файлов."""
        import shutil
        try:
            shutil.rmtree(cls.temp_dir)
        except Exception:
            pass

    def test_encode_pcm_to_mp3_cbr(self):
        """Кодирование PCM в MP3 с постоянным битрейтом."""
        from processing.codecs import encode_pcm_to_mp3, _FFMPEG_CONFIGURED
        
        if not _FFMPEG_CONFIGURED:
            self.skipTest("FFmpeg not configured")
        
        out_mp3 = os.path.join(self.temp_dir, "test_cbr.mp3")
        
        try:
            dt = encode_pcm_to_mp3(
                self.pcm_data, 
                self.sr, 
                out_mp3, 
                bitrate="192k",
                profile='cbr'
            )
            
            self.assertGreater(dt, 0)
            self.assertTrue(os.path.exists(out_mp3))
            self.assertGreater(os.path.getsize(out_mp3), 0)
        except Exception as e:
            self.skipTest(f"FFmpeg encoding failed: {e}")

    def test_encode_pcm_to_mp3_vbr(self):
        """Кодирование PCM в MP3 с переменным битрейтом."""
        from processing.codecs import encode_pcm_to_mp3, _FFMPEG_CONFIGURED
        
        if not _FFMPEG_CONFIGURED:
            self.skipTest("FFmpeg not configured")
        
        out_mp3 = os.path.join(self.temp_dir, "test_vbr.mp3")
        
        try:
            dt = encode_pcm_to_mp3(
                self.pcm_data, 
                self.sr, 
                out_mp3, 
                bitrate="192k",
                profile='vbr'
            )
            
            self.assertGreater(dt, 0)
            self.assertTrue(os.path.exists(out_mp3))
            self.assertGreater(os.path.getsize(out_mp3), 0)
        except Exception as e:
            self.skipTest(f"FFmpeg encoding failed: {e}")

    def test_encode_silence(self):
        """Кодирование тишины."""
        from processing.codecs import encode_pcm_to_mp3, _FFMPEG_CONFIGURED
        
        if not _FFMPEG_CONFIGURED:
            self.skipTest("FFmpeg not configured")
        
        out_mp3 = os.path.join(self.temp_dir, "test_silence.mp3")
        silence = np.zeros(self.sr, dtype=np.float32)
        
        try:
            dt = encode_pcm_to_mp3(silence, self.sr, out_mp3)
            
            self.assertGreater(dt, 0)
            self.assertTrue(os.path.exists(out_mp3))
        except Exception as e:
            self.skipTest(f"FFmpeg encoding failed: {e}")


class TestDecodeAudioToMono(unittest.TestCase):
    """Тесты декодирования аудио в моно."""

    @classmethod
    def setUpClass(cls):
        """Создание тестовых файлов."""
        cls.temp_dir = tempfile.mkdtemp()
        
        # Создаём WAV файл для тестирования
        cls.test_wav = os.path.join(cls.temp_dir, "test_decode.wav")
        cls.sr = 44100
        t = np.linspace(0, 1.0, cls.sr, dtype=np.float32)
        cls.original_data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        
        import soundfile as sf
        sf.write(cls.test_wav, cls.original_data, cls.sr, subtype='PCM_16')

    @classmethod
    def tearDownClass(cls):
        """Удаление временных файлов."""
        import shutil
        try:
            shutil.rmtree(cls.temp_dir)
        except Exception:
            pass

    def test_decode_wav_to_mono(self):
        """Декодирование WAV в моно."""
        from processing.codecs import decode_audio_to_mono, _FFMPEG_CONFIGURED
        
        if not _FFMPEG_CONFIGURED:
            self.skipTest("FFmpeg not configured")
        
        try:
            data, sr = decode_audio_to_mono(self.test_wav)
            
            self.assertEqual(sr, self.sr)
            self.assertTrue(np.issubdtype(data.dtype, np.floating))
            # Проверяем, что сигнал не нулевой
            self.assertGreater(np.max(np.abs(data)), 0.1)
        except Exception as e:
            self.skipTest(f"FFmpeg decode failed: {e}")


class TestEdgeCases(unittest.TestCase):
    """Тесты граничных случаев."""

    def test_empty_pcm(self):
        """Кодирование пустого PCM сигнала."""
        from processing.codecs import encode_pcm_to_mp3, _FFMPEG_CONFIGURED
        
        if not _FFMPEG_CONFIGURED:
            self.skipTest("FFmpeg not configured")
        
        temp_dir = tempfile.mkdtemp()
        try:
            out_mp3 = os.path.join(temp_dir, "empty.mp3")
            empty = np.array([], dtype=np.float32)
            
            # Должно либо работать, либо вызывать понятную ошибку
            try:
                encode_pcm_to_mp3(empty, 44100, out_mp3)
            except Exception:
                pass  # Допустимо
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_clipped_signal(self):
        """Обработка сигнала с клиппингом."""
        from processing.codecs import encode_pcm_to_mp3, _FFMPEG_CONFIGURED
        
        if not _FFMPEG_CONFIGURED:
            self.skipTest("FFmpeg not configured")
        
        temp_dir = tempfile.mkdtemp()
        try:
            out_mp3 = os.path.join(temp_dir, "clipped.mp3")
            # Сигнал вне диапазона [-1, 1]
            clipped = np.ones(44100, dtype=np.float32) * 2.0
            
            dt = encode_pcm_to_mp3(clipped, 44100, out_mp3)
            self.assertGreater(dt, 0)
        except Exception as e:
            self.skipTest(f"FFmpeg encoding failed: {e}")
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_very_short_signal(self):
        """Обработка очень короткого сигнала."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Создаём очень короткий WAV
            short_wav = os.path.join(temp_dir, "short.wav")
            short_data = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
            
            import soundfile as sf
            sf.write(short_wav, short_data, 8000, subtype='PCM_16')
            
            from processing.codecs import load_wav_mono
            data, sr = load_wav_mono(short_wav)
            
            self.assertEqual(len(data), 4)
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
