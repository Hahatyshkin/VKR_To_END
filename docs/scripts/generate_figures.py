#!/usr/bin/env python3
"""Генерация иллюстраций для Главы 1 ВКР: матрицы Адамара, спектры, блок-схемы."""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib
from scipy.fftpack import dct as scipy_dct

matplotlib.font_manager.fontManager.addfont('/usr/share/fonts/truetype/chinese/SimHei.ttf')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

output_dir = '/home/z/my-project/VKR/docs/media/new_figures'

def generate_hadamard_matrices():
    """Рисунок: Матрицы Адамара порядков 1, 2, 4, 8."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Матрицы Адамара различных порядков', fontsize=14, fontweight='bold')
    
    orders = [1, 2, 4, 8]
    
    for ax, n in zip(axes.flatten(), orders):
        # Генерация матрицы Адамара
        H = np.ones((n, n))
        k = 1
        while k < n:
            H[:k, k:2*k] = H[:k, :k]
            H[k:2*k, :k] = H[:k, :k]
            H[k:2*k, k:2*k] = -H[:k, :k]
            k *= 2
        
        # Визуализация
        cmap = plt.cm.RdBu
        im = ax.imshow(H, cmap=cmap, vmin=-1, vmax=1)
        ax.set_title(f'H{n}', fontsize=12, fontweight='bold')
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(range(1, n+1))
        ax.set_yticklabels(range(1, n+1))
        ax.grid(True, which='both', color='black', linewidth=0.5, alpha=0.3)
        
        # Добавляем значения в ячейки
        if n <= 4:
            for i in range(n):
                for j in range(n):
                    ax.text(j, i, f'{int(H[i,j]):+d}', ha='center', va='center', 
                           fontsize=14 if n <= 2 else 10, fontweight='bold',
                           color='white' if H[i,j] < 0 else 'black')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig_hadamard_matrices.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'Создан: fig_hadamard_matrices.png')

def generate_walsh_functions():
    """Рисунок: Функции Уолша для N=8."""
    N = 8
    t = np.linspace(0, 1, 256)
    
    fig, axes = plt.subplots(4, 2, figsize=(12, 10))
    fig.suptitle('Функции Уолша (первые 8 функций)', fontsize=14, fontweight='bold')
    
    # Генерация матрицы Адамара
    H = np.ones((N, N))
    k = 1
    while k < N:
        H[:k, k:2*k] = H[:k, :k]
        H[k:2*k, :k] = H[:k, :k]
        H[k:2*k, k:2*k] = -H[:k, :k]
        k *= 2
    
    # Переупорядочение по sequency (Walsh ordering)
    def walsh_order(H):
        n = H.shape[0]
        seq = np.zeros(n, dtype=int)
        for i in range(n):
            changes = 0
            for j in range(n-1):
                if H[i,j] != H[i,j+1]:
                    changes += 1
            seq[i] = changes
        idx = np.argsort(seq)
        return H[idx], seq[idx]
    
    W, seqs = walsh_order(H)
    
    for idx, ax in enumerate(axes.flatten()):
        if idx < N:
            # Интерполяция функции Уолша
            walsh_func = np.zeros(256)
            block_size = 256 // N
            for i in range(N):
                walsh_func[i*block_size:(i+1)*block_size] = W[idx, i]
            
            ax.fill_between(t, 0, walsh_func, alpha=0.3, color='blue')
            ax.plot(t, walsh_func, 'b-', linewidth=2)
            ax.axhline(y=0, color='black', linewidth=0.5)
            ax.set_ylim(-1.3, 1.3)
            ax.set_xlim(0, 1)
            ax.set_ylabel(f'wal({seqs[idx]})', fontsize=10)
            ax.set_title(f'Функция Уолша wal({seqs[idx]}, t) - {seqs[idx]} пересечений нуля', fontsize=9)
            ax.grid(True, alpha=0.3)
            if idx >= 6:
                ax.set_xlabel('Нормализованное время t', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig_walsh_functions.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'Создан: fig_walsh_functions.png')

def generate_fwht_butterfly():
    """Рисунок: Диаграмма бабочки FWHT для N=8."""
    N = 8
    stages = int(np.log2(N))
    
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(-0.5, stages + 1.5)
    ax.set_ylim(-0.5, N + 0.5)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Диаграмма быстрого преобразования Уолша-Адамара (FWHT) для N=8', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Позиции узлов
    x_positions = list(range(stages + 2))
    y_positions = list(range(N))
    
    # Рисуем узлы
    for stage in range(stages + 2):
        for node in range(N):
            if stage == 0:
                label = f'x[{node}]'
            elif stage == stages + 1:
                label = f'X[{node}]'
            else:
                label = ''
            
            circle = plt.Circle((x_positions[stage], y_positions[node]), 0.2, 
                               fill=True, facecolor='lightblue', edgecolor='black', linewidth=1.5)
            ax.add_patch(circle)
            ax.text(x_positions[stage], y_positions[node], label, ha='center', va='center', fontsize=8)
    
    # Рисуем связи между стадиями
    for s in range(stages):
        step = 2**(stages - s - 1)
        for group in range(2**s):
            base = group * 2 * step
            for i in range(step):
                idx1 = base + i
                idx2 = base + step + i
                
                # Сложение (синий)
                ax.annotate('', xy=(x_positions[s+1], y_positions[idx1]), 
                           xytext=(x_positions[s], y_positions[idx1]),
                           arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
                ax.annotate('', xy=(x_positions[s+1], y_positions[idx1]), 
                           xytext=(x_positions[s], y_positions[idx2]),
                           arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
                
                # Вычитание (красный)
                ax.annotate('', xy=(x_positions[s+1], y_positions[idx2]), 
                           xytext=(x_positions[s], y_positions[idx1]),
                           arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
                ax.annotate('', xy=(x_positions[s+1], y_positions[idx2]), 
                           xytext=(x_positions[s], y_positions[idx2]),
                           arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
    
    # Легенда
    blue_patch = mpatches.Patch(color='blue', label='Сложение (+)')
    red_patch = mpatches.Patch(color='red', label='Вычитание (-)')
    ax.legend(handles=[blue_patch, red_patch], loc='upper right', fontsize=10)
    
    # Подписи стадий
    for s in range(stages + 1):
        ax.text(x_positions[s] + 0.5, N + 0.3, f'Стадия {s+1}' if s < stages else 'Результат', 
               ha='center', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig_fwht_butterfly.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'Создан: fig_fwht_butterfly.png')

def generate_fft_vs_fwht_comparison():
    """Рисунок: Сравнение спектров FFT и FWHT."""
    # Создаем тестовый сигнал
    fs = 1000
    t = np.linspace(0, 1, 512, endpoint=False)
    
    # Сигнал: сумма синусоид
    signal = np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 150 * t) + 0.3 * np.sin(2 * np.pi * 300 * t)
    
    # FFT
    fft_result = np.abs(np.fft.fft(signal))[:256]
    fft_freq = np.fft.fftfreq(512, 1/fs)[:256]
    
    # FWHT
    def fwht(x):
        """Быстрое преобразование Уолша-Адамара."""
        n = len(x)
        result = x.copy()
        step = 1
        while step < n:
            for i in range(0, n, 2*step):
                for j in range(i, i+step):
                    temp = result[j]
                    result[j] = result[j] + result[j+step]
                    result[j+step] = temp - result[j+step]
            step *= 2
        return result / np.sqrt(n)
    
    fwht_result = np.abs(fwht(signal))[:256]
    fwht_idx = np.arange(256)
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # Исходный сигнал
    axes[0].plot(t[:200], signal[:200], 'b-', linewidth=1)
    axes[0].set_xlabel('Время (с)')
    axes[0].set_ylabel('Амплитуда')
    axes[0].set_title('Исходный сигнал: сумма трёх синусоид (50, 150, 300 Гц)', fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    
    # Спектр FFT
    axes[1].plot(fft_freq, fft_result, 'g-', linewidth=1.5)
    axes[1].set_xlabel('Частота (Гц)')
    axes[1].set_ylabel('Амплитуда')
    axes[1].set_title('Спектр FFT (быстрое преобразование Фурье)', fontweight='bold')
    axes[1].set_xlim(0, 500)
    axes[1].grid(True, alpha=0.3)
    
    # Спектр FWHT
    axes[2].stem(fwht_idx[::4], fwht_result[::4], linefmt='r-', markerfmt='ro', basefmt=' ')
    axes[2].set_xlabel('Индекс коэффициента Уолша')
    axes[2].set_ylabel('Амплитуда')
    axes[2].set_title('Спектр FWHT (быстрое преобразование Уолша-Адамара)', fontweight='bold')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig_fft_vs_fwht.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'Создан: fig_fft_vs_fwht.png')

def generate_audio_processing_pipeline():
    """Рисунок: Общая схема обработки аудиосигнала."""
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('Общая схема обработки аудиосигнала в системе', fontsize=14, fontweight='bold', pad=20)
    
    # Блоки
    blocks = [
        (1, 4, 'WAV файл\n(PCM данные)', '#dae8fc', '#6c8ebf'),
        (4, 4, 'Загрузка и\nнормализация', '#fff2cc', '#d6b656'),
        (7, 4, 'Преобразование\n(FWHT/FFT/DCT/DWT)', '#d5e8d4', '#82b366'),
        (10, 4, 'Отбор\nкоэффициентов', '#f8cecc', '#b85450'),
        (13, 4, 'Обратное\nпреобразование', '#e1d5e7', '#9673a6'),
    ]
    
    for x, y, text, fc, ec in blocks:
        rect = FancyBboxPatch((x-1, y-1), 2, 2, boxstyle="round,pad=0.1", 
                              facecolor=fc, edgecolor=ec, linewidth=2)
        ax.add_patch(rect)
        ax.text(x, y, text, ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Стрелки
    arrow_style = dict(arrowstyle='->', color='black', lw=2, mutation_scale=20)
    for i in range(4):
        ax.annotate('', xy=(blocks[i+1][0]-1, 4), xytext=(blocks[i][0]+1, 4), arrowprops=arrow_style)
    
    # Метрики
    metrics_box = FancyBboxPatch((9.5, 1), 4, 1.5, boxstyle="round,pad=0.1", 
                                  facecolor='#f5f5f5', edgecolor='#666666', linewidth=1.5)
    ax.add_patch(metrics_box)
    ax.text(11.5, 1.75, 'Метрики качества:\nSNR, SI-SDR, LSD, STOI, PESQ', 
            ha='center', va='center', fontsize=9)
    
    # MP3
    mp3_box = FancyBboxPatch((1, 1), 2, 1.5, boxstyle="round,pad=0.1", 
                              facecolor='#ffe6cc', edgecolor='#d79b00', linewidth=2)
    ax.add_patch(mp3_box)
    ax.text(2, 1.75, 'MP3\nкодирование', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Стрелка к MP3
    ax.annotate('', xy=(2, 2.5), xytext=(4, 3), arrowprops=arrow_style)
    
    # Стрелка к метрикам
    ax.annotate('', xy=(9.5, 1.75), xytext=(12, 3), arrowprops=arrow_style)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig_audio_pipeline.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'Создан: fig_audio_pipeline.png')

def generate_energy_concentration():
    """Рисунок: Концентрация энергии в коэффициентах различных преобразований."""
    # Создаем тестовый сигнал
    N = 256
    t = np.linspace(0, 1, N, endpoint=False)
    signal = np.sin(2 * np.pi * 5 * t) + 0.5 * np.sin(2 * np.pi * 15 * t)
    signal = signal / np.max(np.abs(signal))
    
    # Преобразования
    fft_coef = np.abs(np.fft.fft(signal))
    fft_energy = np.cumsum(fft_coef**2) / np.sum(fft_coef**2)
    
    def fwht(x):
        n = len(x)
        result = x.copy()
        step = 1
        while step < n:
            for i in range(0, n, 2*step):
                for j in range(i, i+step):
                    temp = result[j]
                    result[j] = result[j] + result[j+step]
                    result[j+step] = temp - result[j+step]
            step *= 2
        return result / np.sqrt(n)
    
    fwht_coef = np.abs(fwht(signal))
    # Сортируем по убыванию
    fwht_sorted = np.sort(fwht_coef)[::-1]
    fwht_energy = np.cumsum(fwht_sorted**2) / np.sum(fwht_sorted**2)
    
    dct_coef = np.abs(scipy_dct(signal, type=2))
    dct_sorted = np.sort(dct_coef)[::-1]
    dct_energy = np.cumsum(dct_sorted**2) / np.sum(dct_sorted**2)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    ax.plot(np.arange(N)/N*100, fft_energy, 'b-', linewidth=2, label='FFT')
    ax.plot(np.arange(N)/N*100, fwht_energy, 'r-', linewidth=2, label='FWHT')
    ax.plot(np.arange(N)/N*100, dct_energy, 'g-', linewidth=2, label='DCT')
    
    ax.axhline(y=0.9, color='gray', linestyle='--', alpha=0.7, label='90% энергии')
    ax.axhline(y=0.95, color='gray', linestyle=':', alpha=0.7, label='95% энергии')
    
    ax.set_xlabel('Доля коэффициентов (%)', fontsize=12)
    ax.set_ylabel('Накопленная энергия', fontsize=12)
    ax.set_title('Концентрация энергии в коэффициентах преобразований', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 50)
    ax.set_ylim(0, 1.05)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig_energy_concentration.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'Создан: fig_energy_concentration.png')

def generate_dwt_decomposition():
    """Рисунок: Многоуровневое вейвлет-разложение сигнала."""
    from scipy import signal as sp_signal
    
    # Создаем тестовый сигнал
    N = 512
    t = np.linspace(0, 2, N)
    
    # Сигнал с изменяющейся частотой
    sig = np.zeros(N)
    sig[:N//2] = np.sin(2 * np.pi * 10 * t[:N//2])
    sig[N//2:] = np.sin(2 * np.pi * 50 * t[N//2:])
    sig += 0.2 * np.random.randn(N)
    
    # Вейвлет-разложение Хаара (3 уровня)
    def haar_dwt(x, levels=3):
        approx = [x.copy()]
        detail = []
        for _ in range(levels):
            a = approx[-1]
            n = len(a)
            if n < 2:
                break
            new_approx = (a[::2] + a[1::2]) / np.sqrt(2)
            new_detail = (a[::2] - a[1::2]) / np.sqrt(2)
            approx.append(new_approx)
            detail.append(new_detail)
        return approx, detail
    
    approx, detail = haar_dwt(sig, levels=3)
    
    fig, axes = plt.subplots(5, 1, figsize=(14, 10))
    fig.suptitle('Трёхуровневое вейвлет-разложение Хаара', fontsize=14, fontweight='bold')
    
    axes[0].plot(sig)
    axes[0].set_title('Исходный сигнал', fontsize=11)
    axes[0].set_ylabel('Амплитуда')
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(approx[1])
    axes[1].set_title('Уровень 1: Аппроксимация (A1)', fontsize=11)
    axes[1].set_ylabel('Амплитуда')
    axes[1].grid(True, alpha=0.3)
    
    axes[2].plot(detail[0])
    axes[2].set_title('Уровень 1: Детализация (D1)', fontsize=11)
    axes[2].set_ylabel('Амплитуда')
    axes[2].grid(True, alpha=0.3)
    
    axes[3].plot(approx[3])
    axes[3].set_title('Уровень 3: Аппроксимация (A3)', fontsize=11)
    axes[3].set_ylabel('Амплитуда')
    axes[3].grid(True, alpha=0.3)
    
    axes[4].plot(detail[2])
    axes[4].set_title('Уровень 3: Детализация (D3)', fontsize=11)
    axes[4].set_ylabel('Амплитуда')
    axes[4].set_xlabel('Отсчёты')
    axes[4].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig_dwt_decomposition.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'Создан: fig_dwt_decomposition.png')

def generate_psychoacoustic_masking():
    """Рисунок: Психоакустическое маскирование."""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    freq = np.logspace(1, 4, 1000)  # 10 Гц - 10 кГц
    
    # Порог слышимости (кривая равной громкости, упрощённая)
    threshold = 10 * np.log10(freq / 1000)**2 + 10
    
    # Маскирующий тон на 1 кГц, 80 дБ
    mask_freq = 1000
    mask_level = 80
    
    # Маскирующий порог (упрощённая модель)
    distance = np.abs(np.log10(freq / mask_freq))
    masking = mask_level - 20 * distance - 30 * distance**2
    masking = np.maximum(masking, -100)
    
    # Итоговый порог
    combined = np.maximum(threshold, masking)
    
    ax.semilogx(freq, threshold, 'b-', linewidth=2, label='Порог слышимости')
    ax.semilogx(freq, masking, 'r--', linewidth=2, label='Маскирующий порог (тон 1 кГц, 80 дБ)')
    ax.semilogx(freq, combined, 'g-', linewidth=2.5, label='Итоговый порог слышимости')
    
    # Маскирующий тон
    ax.axvline(x=mask_freq, color='orange', linestyle=':', linewidth=2, label=f'Маскирующий тон ({mask_freq} Гц)')
    
    ax.set_xlabel('Частота (Гц)', fontsize=12)
    ax.set_ylabel('Уровень звукового давления (дБ SPL)', fontsize=12)
    ax.set_title('Психоакустическое маскирование: эффект маскирующего тона', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xlim(10, 10000)
    ax.set_ylim(0, 100)
    
    # Закрашиваем область маскированных звуков
    ax.fill_between(freq, 0, combined, alpha=0.2, color='gray', label='Зона маскированных звуков')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig_psychoacoustic_masking.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'Создан: fig_psychoacoustic_masking.png')

if __name__ == '__main__':
    print('Генерация иллюстраций для ВКР...')
    
    generate_hadamard_matrices()
    generate_walsh_functions()
    generate_fwht_butterfly()
    generate_fft_vs_fwht_comparison()
    generate_audio_processing_pipeline()
    generate_energy_concentration()
    generate_dwt_decomposition()
    generate_psychoacoustic_masking()
    
    print('\nВсе иллюстрации успешно созданы!')
