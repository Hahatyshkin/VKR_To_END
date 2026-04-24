#!/usr/bin/env python3
"""Generate code screenshots for processing methods."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

matplotlib.font_manager.fontManager.addfont('/usr/share/fonts/truetype/chinese/SimHei.ttf')
matplotlib.font_manager.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
matplotlib.font_manager.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
plt.rcParams['font.family'] = 'monospace'
plt.rcParams['axes.unicode_minus'] = False

OUT = "/home/z/my-project/download/repo/docs/figures_gost/png"
DPI = 200


def render_code(code_lines, filename, title=""):
    """Render code lines as a formatted screenshot."""
    n = len(code_lines)
    fig_h = max(3, n * 0.32 + 0.5)
    fig, ax = plt.subplots(1, 1, figsize=(8, fig_h))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, n + 0.5)
    ax.axis('off')
    
    # Background
    bg = FancyBbox = plt.Rectangle((0, -0.2), 10, n + 0.7,
                                    facecolor='#FAFAFA', edgecolor='#CCCCCC',
                                    linewidth=1.0)
    ax.add_patch(bg)
    
    # Title bar
    titlebar = plt.Rectangle((0, n + 0.1), 10, 0.4,
                              facecolor='#E8E8E8', edgecolor='#CCCCCC',
                              linewidth=0.5)
    ax.add_patch(titlebar)
    if title:
        ax.text(0.3, n + 0.3, title, fontsize=8, va='center',
                fontfamily='DejaVu Sans', color='#333333')
    
    # Code lines
    for i, line in enumerate(code_lines):
        y = n - 0.3 - i
        # Line number
        ax.text(0.2, y, f'{i+1:>3}', fontsize=7, va='center',
                fontfamily='DejaVu Sans Mono', color='#888888')
        # Code
        # Basic syntax highlighting via color
        color = '#333333'
        if line.strip().startswith('#'):
            color = '#6A9955'  # green for comments
        elif any(kw in line.split() for kw in ['import', 'from', 'def', 'class', 'return', 'if', 'else', 'for', 'in', 'with', 'as', 'try', 'except', 'self', 'None', 'True', 'False']):
            color = '#0000CC'  # blue for keywords
        
        ax.text(0.9, y, line, fontsize=7, va='center',
                fontfamily='DejaVu Sans Mono', color=color)
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/{filename}', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"{filename} done")


# === FFT Implementation ===
render_code([
    'import numpy as np',
    'from scipy.io import wavfile',
    '',
    'class FFTTransform:',
    '    def __init__(self, threshold=0.01):',
    '        self.threshold = threshold',
    '',
    '    def forward(self, signal):',
    '        """Прямое FFT преобразование"""',
    '        spectrum = np.fft.rfft(signal)',
    '        return spectrum',
    '',
    '    def process(self, input_path, output_path):',
    '        sr, data = wavfile.read(input_path)',
    '        if data.ndim > 1:',
    '            data = data.mean(axis=1)',
    '        spectrum = self.forward(data)',
    '        # Пороговая обработка',
    '        mask = np.abs(spectrum) > self.threshold',
    '        spectrum *= mask',
    '        result = np.fft.irfft(spectrum, n=len(data))',
    '        result = result.astype(np.int16)',
    '        wavfile.write(output_path, sr, result)',
], 'fig_2_7_fft_code.png', 'fft_transform.py')


# === FWHT Implementation ===
render_code([
    'import numpy as np',
    'from scipy.io import wavfile',
    '',
    'class FWHTTransform:',
    '    def __init__(self, threshold=0.005):',
    '        self.threshold = threshold',
    '',
    '    def _fwht(self, x):',
    '        """Быстрое преобразование Уолша-Адамара"""',
    '        n = len(x)',
    '        h = 1',
    '        while h < n:',
    '            for i in range(0, n, h * 2):',
    '                for j in range(i, i + h):',
    '                    u = x[j]',
    '                    v = x[j + h]',
    '                    x[j] = u + v',
    '                    x[j + h] = u - v',
    '            h *= 2',
    '        return x / np.sqrt(n)',
    '',
    '    def process(self, input_path, output_path):',
    '        sr, data = wavfile.read(input_path)',
    '        coeffs = self._fwht(data.copy())',
    '        coeffs[np.abs(coeffs) < self.threshold] = 0',
    '        result = self._fwht(coeffs)',
    '        result = result.astype(np.int16)',
    '        wavfile.write(output_path, sr, result)',
], 'fig_2_8_fwht_code.png', 'fwht_transform.py')


# === DCT Implementation ===
render_code([
    'import numpy as np',
    'from scipy.fft import dct, idct',
    'from scipy.io import wavfile',
    '',
    'class DCTTransform:',
    '    def __init__(self, threshold=0.01):',
    '        self.threshold = threshold',
    '',
    '    def process(self, input_path, output_path):',
    '        sr, data = wavfile.read(input_path)',
    '        # Прямое DCT-II преобразование',
    '        coeffs = dct(data.astype(float), type=2)',
    '        # Квантование коэффициентов',
    '        coeffs[np.abs(coeffs) < self.threshold] = 0',
    '        # Обратное DCT-II',
    '        result = idct(coeffs, type=2)[:len(data)]',
    '        result = np.clip(result, -32768, 32767)',
    '        result = result.astype(np.int16)',
    '        wavfile.write(output_path, sr, result)',
], 'fig_2_9_dct_code.png', 'dct_transform.py')


# === DWT Implementation ===
render_code([
    'import numpy as np',
    'import pywt',
    'from scipy.io import wavfile',
    '',
    'class DWTTransform:',
    '    def __init__(self, wavelet="haar", level=4,',
    '                 threshold=0.01):',
    '        self.wavelet = wavelet',
    '        self.level = level',
    '        self.threshold = threshold',
    '',
    '    def process(self, input_path, output_path):',
    '        sr, data = wavfile.read(input_path)',
    '        # Прямое вейвлет-преобразование',
    '        coeffs = pywt.wavedec(data, self.wavelet,',
    '                              level=self.level)',
    '        # Порог обработки деталей',
    '        thresholded = [coeffs[0]]',
    '        for detail in coeffs[1:]:',
    '            d = np.where(np.abs(detail) > self.threshold,',
    '                        detail, 0)',
    '            thresholded.append(d)',
    '        # Обратное преобразование',
    '        result = pywt.waverec(thresholded, self.wavelet)',
    '        result = result[:len(data)].astype(np.int16)',
    '        wavfile.write(output_path, sr, result)',
], 'fig_2_10_dwt_code.png', 'dwt_transform.py')


# === mu-law Implementation ===
render_code([
    'import numpy as np',
    'from scipy.io import wavfile',
    '',
    'class MuLawTransform:',
    '    def __init__(self, mu=255):',
    '        self.mu = mu',
    '',
    '    def _compress(self, x):',
    '        """mu-law компандирование (сжатие)"""',
    '        y = np.sign(x) * np.log(1 + self.mu * np.abs(x))',
    '        return y / np.log(1 + self.mu)',
    '',
    '    def _expand(self, y):',
    '        """mu-law расширение (восстановление)"""',
    '        x = np.sign(y) * (1.0 / self.mu) * \\',
    '            (np.power(1 + self.mu, np.abs(y)) - 1)',
    '        return x',
    '',
    '    def process(self, input_path, output_path):',
    '        sr, data = wavfile.read(input_path)',
    '        norm = data / 32768.0',
    '        compressed = self._compress(norm)',
    '        expanded = self._expand(compressed)',
    '        result = (expanded * 32768).astype(np.int16)',
    '        wavfile.write(output_path, sr, result)',
], 'fig_2_11_mulaw_code.png', 'mulaw_transform.py')


# === Rosenbrock Implementation ===
render_code([
    'import numpy as np',
    'from scipy.io import wavfile',
    '',
    'class RosenbrockTransform:',
    '    def __init__(self, a=1.0, b=100.0,',
    '                 frame_size=1024, hop=512):',
    '        self.a = a',
    '        self.b = b',
    '        self.frame_size = frame_size',
    '        self.hop = hop',
    '',
    '    def _rosenbrock_smooth(self, frame):',
    '        """Нелинейное сглаживание Розенброка"""',
    '        x = frame.astype(float)',
    '        y = np.zeros_like(x)',
    '        for i in range(1, len(x) - 1):',
    '            y[i] = (x[i-1] + x[i] + x[i+1]) / 3.0',
    '            # Модифицированная функция Розенброка',
    '            penalty = self.b * (x[i] - x[i-1])**2',
    '            factor = 1.0 / (1.0 + penalty * 0.0001)',
    '            y[i] = x[i] * factor + y[i] * (1 - factor)',
    '        return y',
    '',
    '    def process(self, input_path, output_path):',
    '        sr, data = wavfile.read(input_path)',
    '        result = np.zeros_like(data, dtype=float)',
    '        for i in range(0, len(data), self.hop):',
    '            frame = data[i:i+self.frame_size]',
    '            result[i:i+self.frame_size] += \\',
    '                self._rosenbrock_smooth(frame)',
    '        wavfile.write(output_path, sr,',
    '                      result.astype(np.int16))',
], 'fig_2_12_rosen_code.png', 'rosenbrock_transform.py')


print("\nAll code screenshots generated!")
