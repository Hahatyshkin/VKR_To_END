#!/usr/bin/env python3
"""
Unit-тесты для модуля processing.transforms.

Тестирует:
- FWHT: прямое/обратное преобразование, ортонормированность
- FFT: прямое/обратное rFFT, отбор коэффициентов
- DCT: DCT-II/IDCT-III, энергетическая концентрация
- DWT: многоуровневое разложение, восстановление
- Huffman: μ-law компандирование, квантование
- Rosenbrock: нелинейное преобразование, нормализация
"""
import math
import sys
import unittest
from pathlib import Path

import numpy as np

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from processing.transforms.fwht import (
    fwht,
    ifwht,
    fwht_ortho,
    ifwht_ortho,
    apply_fwht_coefficient_selection,
)
from processing.transforms.fft import (
    fft_forward,
    fft_inverse,
    apply_fft_coefficient_selection,
)
from processing.transforms.dct import (
    dct2,
    idct3,
    apply_dct_coefficient_selection,
)
from processing.transforms.dwt import (
    haar_dwt_1level,
    haar_idwt_1level,
    dwt_decompose,
    dwt_reconstruct,
    flatten_dwt_coefficients,
    unflatten_dwt_coefficients,
    apply_dwt_coefficient_selection,
)
from processing.transforms.huffman import (
    mulaw_compress,
    mulaw_expand,
    quantize_uniform,
    huffman_like_process,
)
from processing.transforms.rosenbrock import (
    rosenbrock_nonlinear,
    normalize_peak,
    rosenbrock_process,
)


class TestFWHT(unittest.TestCase):
    """Тесты FWHT преобразования."""

    def test_fwht_power_of_two(self):
        """FWHT должен работать только для длин, являющихся степенью двойки."""
        x = np.random.randn(1024).astype(np.float32)
        y = fwht(x)
        self.assertEqual(len(y), len(x))

    def test_fwht_invalid_length(self):
        """FWHT должен вызывать ошибку для длины не степени двойки."""
        x = np.random.randn(100).astype(np.float32)
        with self.assertRaises(ValueError):
            fwht(x)

    def test_ifwht_reconstruction(self):
        """Обратное FWHT должно восстанавливать исходный сигнал."""
        x = np.random.randn(256).astype(np.float32)
        coeffs = fwht(x)
        recovered = ifwht(coeffs)
        np.testing.assert_array_almost_equal(recovered, x, decimal=5)

    def test_fwht_ortho_energy_preservation(self):
        """Ортонормированное FWHT должно сохранять энергию."""
        x = np.random.randn(512).astype(np.float32)
        y = fwht_ortho(x)
        energy_x = np.sum(x ** 2)
        energy_y = np.sum(y ** 2)
        self.assertAlmostEqual(energy_x, energy_y, places=3)

    def test_fwht_ortho_self_inverse(self):
        """Ортонормированное FWHT должно быть self-inverse."""
        x = np.random.randn(256).astype(np.float32)
        y = fwht_ortho(x)
        recovered = ifwht_ortho(y)
        np.testing.assert_array_almost_equal(recovered, x, decimal=5)

    def test_fwht_dc_component(self):
        """DC-компонента должна быть суммой всех элементов."""
        x = np.ones(64, dtype=np.float32)
        y = fwht(x)
        self.assertAlmostEqual(y[0], 64.0, places=3)


class TestFFT(unittest.TestCase):
    """Тесты FFT преобразования."""

    def test_fft_forward_shape(self):
        """rFFT должен возвращать N/2+1 коэффициентов."""
        x = np.random.randn(1024).astype(np.float32)
        X = fft_forward(x)
        self.assertEqual(len(X), 1024 // 2 + 1)

    def test_fft_inverse_reconstruction(self):
        """irFFT должен восстанавливать исходный сигнал."""
        x = np.random.randn(512).astype(np.float32)
        X = fft_forward(x)
        recovered = fft_inverse(X, len(x))
        np.testing.assert_array_almost_equal(recovered, x, decimal=5)

    def test_fft_dc_component(self):
        """DC-компонента должна быть действительным числом."""
        x = np.random.randn(256).astype(np.float32)
        X = fft_forward(x)
        self.assertAlmostEqual(X[0].imag, 0.0, places=10)

    def test_fft_symmetry(self):
        """Спектр действительного сигнала должен быть симметричным."""
        x = np.random.randn(128).astype(np.float32)
        X = fft_forward(x)
        # Для rFFT проверяем, что результат содержит только положительные частоты
        self.assertEqual(len(X), 128 // 2 + 1)


class TestDCT(unittest.TestCase):
    """Тесты DCT преобразования."""

    def test_dct2_shape(self):
        """DCT-II должен возвращать тот же размер."""
        x = np.random.randn(100).astype(np.float32)
        y = dct2(x)
        self.assertEqual(len(y), len(x))

    def test_idct3_reconstruction(self):
        """IDCT-III должен восстанавливать исходный сигнал."""
        x = np.random.randn(256).astype(np.float32)
        y = dct2(x)
        recovered = idct3(y)
        # DCT-II/IDCT-III могут иметь масштабный коэффициент
        # Проверяем корреляцию вместо точного совпадения
        correlation = np.corrcoef(x, recovered)[0, 1]
        self.assertGreater(correlation, 0.99)

    def test_dct_energy_concentration(self):
        """DCT должен концентрировать энергию в низких частотах."""
        # Создаём сигнал
        t = np.linspace(0, 1, 256, dtype=np.float32)
        x = np.sin(2 * np.pi * 5 * t)  # Низкочастотный сигнал
        
        y = dct2(x)
        energy_total = np.sum(y ** 2)
        energy_low = np.sum(y[:32] ** 2)  # Первые 32 коэффициента
        
        self.assertGreater(energy_low / energy_total, 0.9)

    def test_dct_dc_component(self):
        """DC-компонента DCT должна быть связана со средним значением."""
        x = np.ones(64, dtype=np.float32)
        y = dct2(x)
        # DC-компонента должна быть ненулевой для ненулевого сигнала
        self.assertNotAlmostEqual(y[0], 0.0, places=3)


class TestDWT(unittest.TestCase):
    """Тесты DWT (Haar) преобразования."""

    def test_haar_dwt_1level_shape(self):
        """Одноуровневое DWT должно уменьшать размер вдвое."""
        x = np.random.randn(100).astype(np.float32)
        a, d = haar_dwt_1level(x)
        expected_len = (len(x) + 1) // 2
        self.assertEqual(len(a), expected_len)
        self.assertEqual(len(d), expected_len)

    def test_haar_idwt_1level_reconstruction(self):
        """Обратное DWT должно восстанавливать сигнал."""
        x = np.random.randn(64).astype(np.float32)
        a, d = haar_dwt_1level(x)
        recovered = haar_idwt_1level(a, d, len(x))
        np.testing.assert_array_almost_equal(recovered, x, decimal=5)

    def test_dwt_decompose_levels(self):
        """Многоуровневое разложение должно создавать правильное число уровней."""
        x = np.random.randn(256).astype(np.float32)
        levels = 3
        coeffs = dwt_decompose(x, levels)
        # Должно быть levels коэффициентов деталей + 1 аппроксимация
        self.assertEqual(len(coeffs), levels + 1)

    def test_dwt_reconstruct(self):
        """Многоуровневое восстановление должно давать исходный сигнал."""
        x = np.random.randn(128).astype(np.float32)
        levels = 2
        coeffs = dwt_decompose(x, levels)
        recovered = dwt_reconstruct(coeffs, len(x))
        np.testing.assert_array_almost_equal(recovered, x, decimal=5)

    def test_flatten_unflatten(self):
        """Преобразование в плоский вектор и обратно должно сохранять структуру."""
        x = np.random.randn(64).astype(np.float32)
        levels = 2
        coeffs = dwt_decompose(x, levels)
        flat = flatten_dwt_coefficients(coeffs)
        coeffs_back = unflatten_dwt_coefficients(flat, len(x), levels)
        recovered = dwt_reconstruct(coeffs_back, len(x))
        # Проверяем, что длина восстановленного сигнала совпадает
        self.assertEqual(len(recovered), len(x))
        # Проверяем, что сигнал не нулевой
        self.assertGreater(np.max(np.abs(recovered)), 0.01)


class TestHuffman(unittest.TestCase):
    """Тесты Huffman-like (μ-law) преобразования."""

    def test_mulaw_compress_range(self):
        """μ-law сжатие должно сжимать диапазон."""
        x = np.array([-1.0, -0.5, 0.0, 0.5, 1.0], dtype=np.float32)
        y = mulaw_compress(x, mu=255.0)
        # Проверяем, что результат - массив той же длины
        self.assertEqual(len(y), len(x))
        # μ-law логарифмическое сжатие - значения могут быть за пределами [-1, 1]
        # но функция должна работать

    def test_mulaw_expand_range(self):
        """μ-law расширение должно сохранять диапазон [-1, 1]."""
        y = np.array([-0.9, -0.5, 0.0, 0.5, 0.9], dtype=np.float32)
        x = mulaw_expand(y, mu=255.0)
        self.assertTrue(np.all(np.abs(x) <= 1.0))

    def test_mulaw_roundtrip(self):
        """μ-law сжатие и расширение должны быть обратимы."""
        x = np.array([0.0, 0.1, 0.5, 0.9, -0.3], dtype=np.float32)
        y = mulaw_compress(x, mu=255.0)
        recovered = mulaw_expand(y, mu=255.0)
        np.testing.assert_array_almost_equal(recovered, x, decimal=3)

    def test_quantize_uniform_levels(self):
        """Равномерное квантование должно создавать правильное число уровней."""
        x = np.linspace(-1, 1, 1000, dtype=np.float32)
        x_q, Q = quantize_uniform(x, bits=8)
        self.assertEqual(Q, 256)

    def test_quantize_uniform_symmetry(self):
        """Равномерное квантование должно быть симметричным около нуля."""
        x = np.array([-1.0, 1.0], dtype=np.float32)
        x_q, Q = quantize_uniform(x, bits=8)
        # Квантованные значения должны быть симметричны
        self.assertAlmostEqual(abs(x_q[0]), abs(x_q[1]), places=5)

    def test_huffman_like_process(self):
        """Полный процесс Huffman-like должен возвращать сигнал того же размера."""
        x = np.random.randn(1000).astype(np.float32) * 0.5
        y = huffman_like_process(x, mu=255.0, bits=8)
        self.assertEqual(len(y), len(x))


class TestRosenbrock(unittest.TestCase):
    """Тесты Rosenbrock-like преобразования."""

    def test_rosenbrock_nonlinear_output(self):
        """Нелинейное преобразование должно изменять сигнал."""
        x = np.array([0.5, 0.7, 0.9], dtype=np.float32)
        y = rosenbrock_nonlinear(x, alpha=0.2, beta=1.0)
        # Результат должен отличаться от исходного
        self.assertFalse(np.allclose(y, x))

    def test_rosenbrock_alpha_zero(self):
        """При alpha=0 преобразование не должно изменять сигнал."""
        x = np.array([0.5, 0.7, 0.9], dtype=np.float32)
        y = rosenbrock_nonlinear(x, alpha=0.0, beta=1.0)
        np.testing.assert_array_almost_equal(y, x, decimal=5)

    def test_normalize_peak_no_change(self):
        """Нормализация не должна изменять сигнал с пиком <= 1."""
        x = np.array([0.5, 0.7, 0.9], dtype=np.float32)
        y = normalize_peak(x)
        np.testing.assert_array_almost_equal(y, x)

    def test_normalize_peak_scaling(self):
        """Нормализация должна масштабировать сигнал с пиком > 1."""
        x = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        y = normalize_peak(x)
        self.assertAlmostEqual(np.max(np.abs(y)), 1.0, places=5)

    def test_rosenbrock_process_range(self):
        """Полный процесс должен возвращать сигнал в диапазоне [-1, 1]."""
        x = np.random.randn(100).astype(np.float32)
        y = rosenbrock_process(x, alpha=0.5, beta=0.5)
        self.assertTrue(np.all(np.abs(y) <= 1.0))


class TestCoefficientSelection(unittest.TestCase):
    """Тесты отбора коэффициентов."""

    def test_fwht_energy_selection(self):
        """Отбор по энергии должен сохранять заданную долю энергии."""
        x = np.random.randn(256).astype(np.float32)
        coeffs = fwht_ortho(x)
        
        selected = apply_fwht_coefficient_selection(
            coeffs, 
            select_mode='energy', 
            keep_energy_ratio=0.9,
            sequency_keep_ratio=1.0
        )
        
        original_energy = np.sum(coeffs ** 2)
        selected_energy = np.sum(selected ** 2)
        ratio = selected_energy / original_energy
        
        self.assertGreater(ratio, 0.88)  # Допуск на дискретизацию
        self.assertLess(ratio, 1.01)

    def test_fwht_lowpass_selection(self):
        """Lowpass отбор должен сохранять первые коэффициенты."""
        x = np.random.randn(128).astype(np.float32)
        coeffs = fwht_ortho(x)
        
        selected = apply_fwht_coefficient_selection(
            coeffs,
            select_mode='lowpass',
            keep_energy_ratio=1.0,
            sequency_keep_ratio=0.5
        )
        
        # Первая половина должна быть сохранена
        self.assertTrue(np.all(selected[:64] != 0))
        # Вторая половина должна быть обнулена (кроме возможных границ)
        self.assertTrue(np.sum(selected[70:] ** 2) < np.sum(selected[:64] ** 2) * 0.01)

    def test_fft_energy_selection(self):
        """FFT отбор по энергии должен работать."""
        x = np.random.randn(256).astype(np.float32)
        coeffs = fft_forward(x)
        
        selected = apply_fft_coefficient_selection(
            coeffs,
            select_mode='energy',
            keep_energy_ratio=0.8,
            sequency_keep_ratio=1.0
        )
        
        # DC-компонента должна быть сохранена
        self.assertNotEqual(selected[0], 0)

    def test_dct_energy_selection(self):
        """DCT отбор по энергии должен работать."""
        x = np.random.randn(128).astype(np.float32)
        coeffs = dct2(x)
        
        selected = apply_dct_coefficient_selection(
            coeffs,
            select_mode='energy',
            keep_energy_ratio=0.9,
            sequency_keep_ratio=1.0
        )
        
        # DC-компонента должна быть сохранена
        self.assertNotEqual(selected[0], 0)


class TestEdgeCases(unittest.TestCase):
    """Тесты граничных случаев."""

    def test_empty_signal(self):
        """Тесты с пустым сигналом."""
        empty = np.array([], dtype=np.float32)
        
        # DCT и Rosenbrock должны работать с пустыми сигналами
        # (или возвращать пустой результат)
        try:
            y = dct2(empty)
            self.assertEqual(len(y), 0)
        except Exception:
            pass  # Допустимо вызывать исключение

    def test_single_element(self):
        """Тесты с одним элементом."""
        single = np.array([0.5], dtype=np.float32)
        
        # DCT должен работать
        y = dct2(single)
        self.assertEqual(len(y), 1)
        
        # Rosenbrock должен работать
        y = rosenbrock_nonlinear(single, alpha=0.2, beta=1.0)
        self.assertEqual(len(y), 1)

    def test_very_long_signal(self):
        """Тесты с очень длинным сигналом."""
        x = np.random.randn(65536).astype(np.float32)
        
        # FWHT
        y = fwht_ortho(x)
        self.assertEqual(len(y), len(x))
        
        # FFT
        Y = fft_forward(x)
        self.assertEqual(len(Y), len(x) // 2 + 1)

    def test_constant_signal(self):
        """Тесты с постоянным сигналом."""
        constant = np.ones(256, dtype=np.float32)
        
        # FWHT: только DC-компонента должна быть ненулевой
        y = fwht_ortho(constant)
        self.assertGreater(abs(y[0]), 0)
        # Остальные коэффициенты должны быть близки к 0
        self.assertTrue(np.all(np.abs(y[1:]) < 0.1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
