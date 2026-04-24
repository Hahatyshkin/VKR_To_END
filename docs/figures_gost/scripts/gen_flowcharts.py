#!/usr/bin/env python3
"""Generate GOST-compliant flowcharts for thesis figures."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

matplotlib.font_manager.fontManager.addfont('/usr/share/fonts/truetype/chinese/SimHei.ttf')
matplotlib.font_manager.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = "/home/z/my-project/download/repo/docs/figures_gost/png"
DPI = 200

# === HELPER FUNCTIONS ===
def draw_block(ax, x, y, w, h, text, style='rect', fontsize=8):
    """Draw a block in flowchart. style: rect, diamond, rounded, parallel"""
    if style == 'rect':
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                             boxstyle="square,pad=0", linewidth=1.2,
                             edgecolor='black', facecolor='white')
        ax.add_patch(box)
    elif style == 'rounded':
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                             boxstyle="round,pad=0.05", linewidth=1.2,
                             edgecolor='black', facecolor='white')
        ax.add_patch(box)
    elif style == 'diamond':
        diamond = plt.Polygon([(x, y+h/2), (x+w/2, y), (x, y-h/2), (x-w/2, y)],
                              linewidth=1.2, edgecolor='black', facecolor='white')
        ax.add_patch(diamond)
    elif style == 'parallel':
        # Two horizontal lines
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                             boxstyle="square,pad=0", linewidth=1.2,
                             edgecolor='black', facecolor='white')
        ax.add_patch(box)
        ax.plot([x - w/2, x + w/2], [y - h/4, y - h/4], 'k-', lw=0.8)
        ax.plot([x - w/2, x + w/2], [y + h/4, y + h/4], 'k-', lw=0.8)
    
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            fontfamily='DejaVu Sans', wrap=True,
            bbox=dict(facecolor='white', edgecolor='none', pad=0))

def draw_arrow(ax, x1, y1, x2, y2, label=''):
    """Draw arrow between blocks."""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.0))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx + 0.08, my, label, fontsize=7, ha='left', va='center',
                fontfamily='DejaVu Sans')

def draw_side_arrow(ax, x1, y1, x2, y2, label=''):
    """Draw horizontal arrow."""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.0))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my + 0.08, label, fontsize=7, ha='center', va='bottom',
                fontfamily='DejaVu Sans')


# === РИСУНОК 1.3 — Процесс кодирования WAV → MP3 ===
def gen_fig_1_3():
    fig, ax = plt.subplots(1, 1, figsize=(6, 10))
    ax.set_xlim(-1, 7)
    ax.set_ylim(-0.5, 11)
    ax.axis('off')
    
    bw, bh = 3.2, 0.7  # block width, height
    cx = 3  # center x
    
    blocks = [
        (cx, 10.0, bw, bh, 'WAV-файл\n(входной сигнал)', 'rounded', 8),
        (cx, 8.8, bw, bh, 'Разбиение на кадры\n(1152 отсчёта)', 'rect', 8),
        (cx, 7.6, bw, bh, 'Применение окна\n(Hann/MDCT)', 'rect', 8),
        (cx, 6.4, bw, bh, 'MDCT\n(модифицированное\nдискретное косинусное\nпреобразование)', 'rect', 7),
        (cx, 5.0, bw, bh, 'Психоакустическая\nмодель', 'rect', 8),
        (cx, 3.8, bw, bh, 'Квантование\nи распределение бит', 'rect', 8),
        (cx, 2.6, bw, bh, 'Кодирование Хаффмана\n(Huffman coding)', 'rect', 8),
        (cx, 1.4, bw, bh, 'Формирование\nMP3-фрейма', 'rect', 8),
        (cx, 0.2, bw, bh, 'MP3-поток\n(выходной файл)', 'rounded', 8),
    ]
    
    for (x, y, w, h, text, style, fs) in blocks:
        draw_block(ax, x, y, w, h, text, style, fs)
    
    # Arrows
    for i in range(len(blocks)-1):
        draw_arrow(ax, cx, blocks[i][1] - blocks[i][3]/2,
                   cx, blocks[i+1][1] + blocks[i+1][3]/2)
    
    # Side labels
    draw_side_arrow(ax, 5.5, 5.0, 6.5, 5.0, '')
    ax.text(6.5, 5.0, 'Маскирование\nпороги', fontsize=7, ha='left', va='center',
            fontfamily='DejaVu Sans')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_1_3.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_1_3.png done")


# === РИСУНОК 2.5 — Алгоритм OLA обработки ===
def gen_fig_2_5():
    fig, ax = plt.subplots(1, 1, figsize=(6, 11))
    ax.set_xlim(-1, 8)
    ax.set_ylim(-0.5, 12)
    ax.axis('off')
    
    bw, bh = 3.5, 0.65
    cx = 3.5
    
    blocks = [
        (cx, 11.0, bw, bh, 'Входной аудиосигнал x[n]', 'rounded', 8),
        (cx, 9.8, bw, bh, 'Разбиение на кадры\nс перекрытием 50%', 'rect', 8),
        (cx, 8.5, bw, bh, 'Применение весового окна\n(весовая функция w[n])', 'rect', 8),
        (cx, 7.1, bw, bh, 'Преобразование каждого кадра\n(FWHT / DCT / DWT)', 'rect', 8),
        (cx, 5.7, bw, bh, 'Пороговая обработка\nкоэффициентов', 'rect', 8),
        (cx, 4.3, bw, bh, 'Обратное преобразование', 'rect', 8),
        (cx, 2.9, bw, bh, 'Наложение-сложение\n(Overlap-Add)', 'rect', 8),
        (cx, 1.5, bw, bh, 'Нормализация амплитуды', 'rect', 8),
        (cx, 0.1, bw, bh, 'Выходной сигнал y[n]', 'rounded', 8),
    ]
    
    for (x, y, w, h, text, style, fs) in blocks:
        draw_block(ax, x, y, w, h, text, style, fs)
    
    for i in range(len(blocks)-1):
        draw_arrow(ax, cx, blocks[i][1] - blocks[i][3]/2,
                   cx, blocks[i+1][1] + blocks[i+1][3]/2)
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_2_5.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_2_5.png done")


# === Generic processing method flowchart (2.7-2.12) ===
def gen_method_flowchart(fig_num, method_name, steps, filename):
    """Generate a standardized flowchart for processing methods."""
    n = len(steps)
    fig_h = max(4, n * 0.9 + 1.5)
    fig, ax = plt.subplots(1, 1, figsize=(5.5, fig_h))
    
    margin = 0.8
    ax.set_xlim(-0.5, 6.5)
    ax.set_ylim(-0.5, fig_h - 0.3)
    ax.axis('off')
    
    bw, bh = 3.8, 0.55
    cx = 3.0
    start_y = fig_h - 1.0
    dy = 0.78
    
    blocks = []
    # Start
    blocks.append((cx, start_y, bw, bh, steps[0], 'rounded', 8))
    # Middle steps
    for i, step in enumerate(steps[1:-1]):
        blocks.append((cx, start_y - (i+1)*dy, bw, bh, step, 'rect', 8))
    # End
    blocks.append((cx, start_y - (n-1)*dy, bw, bh, steps[-1], 'rounded', 8))
    
    for (x, y, w, h, text, style, fs) in blocks:
        draw_block(ax, x, y, w, h, text, style, fs)
    
    for i in range(len(blocks)-1):
        draw_arrow(ax, cx, blocks[i][1] - bh/2,
                   cx, blocks[i+1][1] + bh/2)
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/{filename}', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"{filename} done")


# Generate all method flowcharts
gen_fig_1_3()
gen_fig_2_5()

gen_method_flowchart(2.7, 'FFT', [
    'Вход: WAV-файл',
    'Чтение аудиоданных',
    'Вычисление FFT\n(numpy.fft.rfft)',
    'Пороговая обработка\nкоэффициентов',
    'Обратное FFT\n(numpy.fft.irfft)',
    'Запись WAV-файла',
    'Выход: обработанный WAV'
], 'fig_2_7_fft_flow.png')

gen_method_flowchart(2.8, 'FWHT', [
    'Вход: WAV-файл',
    'Чтение аудиоданных',
    'Вычисление FWHT\n(баттерфляй-схема)',
    'Пороговая обработка\nкоэффициентов',
    'Обратное FWHT',
    'Запись WAV-файла',
    'Выход: обработанный WAV'
], 'fig_2_8_fwht_flow.png')

gen_method_flowchart(2.9, 'DCT', [
    'Вход: WAV-файл',
    'Чтение аудиоданных',
    'Прямое DCT-II\n(scipy.fft.dct)',
    'Квантование\nкоэффициентов',
    'Обратное DCT\n(scipy.fft.idct)',
    'Запись WAV-файла',
    'Выход: обработанный WAV'
], 'fig_2_9_dct_flow.png')

gen_method_flowchart(2.10, 'DWT', [
    'Вход: WAV-файл',
    'Чтение аудиоданных',
    'Прямое DWT Хаара\n(pywt.wavedec)',
    'Пороговая обработка\nдетализирующих коэффициентов',
    'Обратное DWT\n(pywt.waverec)',
    'Запись WAV-файла',
    'Выход: обработанный WAV'
], 'fig_2_10_dwt_flow.png')

gen_method_flowchart(2.11, 'mu_law', [
    'Вход: WAV-файл',
    'Чтение аудиоданных',
    'Нормализация\nк [-1, 1]',
    'Применение mu-law\nкомпандирования',
    'Обратное mu-law\n(расширение)',
    'Восстановление\nамплитуды',
    'Запись WAV-файла',
    'Выход: обработанный WAV'
], 'fig_2_11_mulaw_flow.png')

gen_method_flowchart(2.12, 'Rosenbrock', [
    'Вход: WAV-файл',
    'Чтение аудиоданных',
    'Разбиение на кадры',
    'Применение функции\nРозенброка к кадру',
    'Нелинейное сглаживание',
    'Overlap-Add кадров',
    'Запись WAV-файла',
    'Выход: обработанный WAV'
], 'fig_2_12_rosen_flow.png')

print("\nAll flowcharts generated!")
