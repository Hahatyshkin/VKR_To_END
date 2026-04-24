#!/usr/bin/env python3
"""Generate appendix diagrams: IDEF0 (A.1-A.3), DFD (A.4-A.6, A.9), UML (A.7-A.8)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

matplotlib.font_manager.fontManager.addfont('/usr/share/fonts/truetype/chinese/SimHei.ttf')
matplotlib.font_manager.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = "/home/z/my-project/download/repo/docs/figures_gost/png"
DPI = 200

def draw_idef0_block(ax, x, y, w, h, text, label=''):
    """Draw IDEF0 activity block."""
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="square,pad=0", linewidth=1.2,
                         edgecolor='black', facecolor='white')
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, text, fontsize=7, ha='center', va='center',
            fontfamily='DejaVu Sans')
    if label:
        ax.text(x + 0.05, y + h - 0.05, label, fontsize=6, ha='left', va='top',
                fontfamily='DejaVu Sans')

def draw_arrow_line(ax, x1, y1, x2, y2, label='', label_pos='mid'):
    """Draw a straight arrow with optional label."""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='black', lw=0.8))
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        offset_x = 0.15 if x2 >= x1 else -0.15
        offset_y = 0.15 if y2 >= y1 else -0.15
        ax.text(mx + offset_x, my + offset_y, label, fontsize=6,
                ha='left', va='bottom', fontfamily='DejaVu Sans')


# === A.1 — IDEF0: Контекстная диаграмма A-0 ===
def gen_a_1():
    fig, ax = plt.subplots(1, 1, figsize=(7, 5))
    ax.set_xlim(-0.5, 8)
    ax.set_ylim(-0.5, 5.5)
    ax.axis('off')
    
    # Title
    ax.text(4.0, 5.2, 'Контекстная диаграмма A-0', fontsize=10,
            ha='center', fontfamily='DejaVu Sans', fontweight='bold')
    
    # Main block
    bx, by, bw, bh = 2.5, 1.5, 3.0, 2.0
    draw_idef0_block(ax, bx, by, bw, bh, 'Система\nаудиопроцессинга', 'A-0')
    
    # Input arrow (left)
    draw_arrow_line(ax, 0.3, 2.5, 2.5, 2.5, 'Аудиоданные\n(WAV)')
    
    # Output arrow (right)
    draw_arrow_line(ax, 5.5, 2.5, 7.5, 2.5, 'Обработанные\nданные')
    
    # Control arrow (top)
    draw_arrow_line(ax, 4.0, 5.0, 4.0, 3.5, 'Параметры\nконфигурации')
    
    # Mechanism arrow (bottom)
    draw_arrow_line(ax, 4.0, 1.5, 4.0, 0.3, 'Python,\nбиблиотеки')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_a1_idef0_context.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_a1_idef0_context.png done")


# === A.2 — IDEF0: Декомпозиция A0 ===
def gen_a_2():
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    ax.set_xlim(-0.5, 9)
    ax.set_ylim(-0.5, 6.5)
    ax.axis('off')
    
    ax.text(4.5, 6.2, 'Декомпозиция уровня A0', fontsize=10,
            ha='center', fontfamily='DejaVu Sans', fontweight='bold')
    
    # Three main blocks horizontally
    bw, bh = 2.0, 1.2
    gap = 0.8
    start_x = 1.0
    by = 2.5
    
    # A1: Input processing
    draw_idef0_block(ax, start_x, by, bw, bh, 'Ввод данных\nи разбиение', 'A1')
    # A2: Signal transformation
    draw_idef0_block(ax, start_x + bw + gap, by, bw, bh, 'Преобразование\nсигнала', 'A2')
    # A3: Output and metrics
    draw_idef0_block(ax, start_x + 2*(bw + gap), by, bw, bh, 'Вывод и\nметрики', 'A3')
    
    # Input to A1
    draw_arrow_line(ax, 0.0, 3.1, start_x, 3.1, 'WAV-файл')
    
    # A1 -> A2
    draw_arrow_line(ax, start_x + bw, 3.1, start_x + bw + gap, 3.1, 'Кадры')
    
    # A2 -> A3
    draw_arrow_line(ax, start_x + bw + gap + bw, 3.1, start_x + 2*(bw + gap), 3.1, 'Результат')
    
    # A3 -> Output
    draw_arrow_line(ax, start_x + 2*(bw + gap) + bw, 3.1, 8.5, 3.1, 'Обработанный\nWAV')
    
    # Control arrows from top
    mid_a2 = start_x + bw + gap + bw/2
    draw_arrow_line(ax, mid_a2, 5.8, mid_a2, by + bh, 'Метод\nобработки')
    
    # Mechanism arrows from bottom
    draw_arrow_line(ax, start_x + bw/2, by, start_x + bw/2, 0.5, 'Файловая\nсистема')
    draw_arrow_line(ax, mid_a2, by, mid_a2, 0.5, 'NumPy,\nSciPy')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_a2_idef0_a0.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_a2_idef0_a0.png done")


# === A.3 — IDEF0: Декомпозиция A2 ===
def gen_a_3():
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    ax.set_xlim(-0.5, 9)
    ax.set_ylim(-0.5, 6.5)
    ax.axis('off')
    
    ax.text(4.5, 6.2, 'Декомпозиция A2: Преобразование сигнала', fontsize=10,
            ha='center', fontfamily='DejaVu Sans', fontweight='bold')
    
    # Blocks in 2x2 grid
    bw, bh = 2.2, 1.0
    positions = [
        (0.8, 3.8, 'Прямое\nпреобразование', 'A21'),
        (4.0, 3.8, 'Пороговая\nобработка', 'A22'),
        (0.8, 1.8, 'Обратное\nпреобразование', 'A23'),
        (4.0, 1.8, 'Overlap-Add\nи нормализация', 'A24'),
    ]
    
    for (x, y, text, label) in positions:
        draw_idef0_block(ax, x, y, bw, bh, text, label)
    
    # Arrows
    draw_arrow_line(ax, 0.0, 4.3, 0.8, 4.3, 'Кадры')
    draw_arrow_line(ax, 3.0, 4.3, 4.0, 4.3, 'Коэффициенты')
    draw_arrow_line(ax, 3.0, 2.3, 4.0, 2.3, 'Обработанные\nкоэффициенты')
    draw_arrow_line(ax, 6.2, 2.3, 8.5, 2.3, 'Результат')
    
    # Vertical arrows
    draw_arrow_line(ax, 1.9, 3.8, 1.9, 2.8, 'Порог')
    draw_arrow_line(ax, 5.1, 3.8, 5.1, 2.8, 'Коэффициенты')
    
    # Control
    draw_arrow_line(ax, 3.0, 5.8, 3.0, 4.8, 'Тип\nпреобразования')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_a3_idef0_a2.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_a3_idef0_a2.png done")


# === A.4 — DFD: Диаграмма потоков данных ===
def gen_a_4():
    fig, ax = plt.subplots(1, 1, figsize=(8, 5.5))
    ax.set_xlim(-0.5, 9)
    ax.set_ylim(-0.5, 6)
    ax.axis('off')
    
    ax.text(4.5, 5.7, 'DFD: Диаграмма потоков данных', fontsize=10,
            ha='center', fontfamily='DejaVu Sans', fontweight='bold')
    
    # Processes (circles)
    processes = [
        (1.5, 3.0, 'P1', 'Чтение\nWAV'),
        (4.0, 3.0, 'P2', 'Обработка\nсигнала'),
        (6.5, 3.0, 'P3', 'Вычисление\nметрик'),
        (4.0, 0.8, 'P4', 'Запись\nрезультата'),
    ]
    
    for (x, y, label, text) in processes:
        circle = plt.Circle((x, y), 0.9, linewidth=1.0,
                             edgecolor='black', facecolor='white')
        ax.add_patch(circle)
        ax.text(x, y + 0.15, label, fontsize=7, ha='center', va='center',
                fontfamily='DejaVu Sans', fontweight='bold')
        ax.text(x, y - 0.25, text, fontsize=6, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    # External entities (rectangles)
    for (x, y, text) in [(0.0, 0.8, 'Пользователь'), (8.0, 0.8, 'Файловая\nсистема')]:
        box = FancyBboxPatch((x - 0.7, y - 0.35), 1.4, 0.7,
                             boxstyle="square,pad=0", linewidth=1.0,
                             edgecolor='black', facecolor='white')
        ax.add_patch(box)
        ax.text(x, y, text, fontsize=7, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    # Data flows
    draw_arrow_line(ax, 0.7, 0.8, 1.5, 2.1, 'WAV')
    draw_arrow_line(ax, 2.4, 3.0, 3.1, 3.0, 'Сигнал')
    draw_arrow_line(ax, 4.9, 3.0, 5.6, 3.0, 'Результат')
    draw_arrow_line(ax, 4.0, 2.1, 4.0, 1.7, 'Обработ.\nданные')
    draw_arrow_line(ax, 4.8, 0.8, 7.3, 0.8, 'WAV-файл')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_a4_dfd.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_a4_dfd.png done")


# === A.5 — DFD: Контекстная диаграмма (Уровень 0) ===
def gen_a_5():
    fig, ax = plt.subplots(1, 1, figsize=(7, 5))
    ax.set_xlim(-0.5, 8.5)
    ax.set_ylim(-0.5, 5.5)
    ax.axis('off')
    
    ax.text(4.0, 5.2, 'DFD: Контекстная диаграмма (Уровень 0)', fontsize=10,
            ha='center', fontfamily='DejaVu Sans', fontweight='bold')
    
    # Central process
    circle = plt.Circle((4.0, 2.5), 1.2, linewidth=1.2,
                         edgecolor='black', facecolor='white')
    ax.add_patch(circle)
    ax.text(4.0, 2.7, '0', fontsize=10, ha='center', va='center',
            fontfamily='DejaVu Sans', fontweight='bold')
    ax.text(4.0, 2.2, 'Аудиопроцессор', fontsize=8, ha='center', va='center',
            fontfamily='DejaVu Sans')
    
    # External entities
    entities = [
        (0.5, 2.5, 'Пользователь'),
        (0.5, 0.5, 'Библиотеки\n(Numpy/SciPy)'),
        (7.5, 2.5, 'Файловая\nсистема'),
        (7.5, 0.5, 'Отчёт\n(метрики)'),
    ]
    
    for (x, y, text) in entities:
        box = FancyBboxPatch((x - 0.8, y - 0.4), 1.6, 0.8,
                             boxstyle="square,pad=0", linewidth=1.0,
                             edgecolor='black', facecolor='white')
        ax.add_patch(box)
        ax.text(x, y, text, fontsize=7, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    # Data flows
    draw_arrow_line(ax, 1.3, 2.5, 2.8, 2.5, 'WAV-файл\n+ настройки')
    draw_arrow_line(ax, 5.2, 2.5, 6.7, 2.5, 'Обработанный\nWAV')
    draw_arrow_line(ax, 1.3, 0.5, 2.8, 1.8, 'Алгоритмы')
    draw_arrow_line(ax, 5.2, 1.8, 6.7, 0.5, 'Метрики')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_a5_dfd_context.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_a5_dfd_context.png done")


# === A.6 — DFD: Декомпозиция уровня 1 ===
def gen_a_6():
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    ax.set_xlim(-0.5, 9.5)
    ax.set_ylim(-0.5, 6.5)
    ax.axis('off')
    
    ax.text(4.5, 6.2, 'DFD: Декомпозиция уровня 1', fontsize=10,
            ha='center', fontfamily='DejaVu Sans', fontweight='bold')
    
    # Processes
    processes = [
        (1.5, 4.0, '1.0', 'Загрузка\nфайла'),
        (4.5, 4.0, '2.0', 'Выбор метода'),
        (7.5, 4.0, '3.0', 'Преобразование'),
        (1.5, 1.5, '4.0', 'Метрики'),
        (4.5, 1.5, '5.0', 'Сохранение'),
        (7.5, 1.5, '6.0', 'Визуализация'),
    ]
    
    for (x, y, label, text) in processes:
        circle = plt.Circle((x, y), 0.85, linewidth=1.0,
                             edgecolor='black', facecolor='white')
        ax.add_patch(circle)
        ax.text(x, y + 0.15, label, fontsize=7, ha='center', va='center',
                fontfamily='DejaVu Sans', fontweight='bold')
        ax.text(x, y - 0.2, text, fontsize=6.5, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    # Data flows
    draw_arrow_line(ax, 2.35, 4.0, 3.65, 4.0, 'Аудиоданные')
    draw_arrow_line(ax, 5.35, 4.0, 6.65, 4.0, 'Настройки')
    draw_arrow_line(ax, 7.5, 3.15, 7.5, 2.35, 'Результат')
    draw_arrow_line(ax, 6.65, 1.5, 5.35, 1.5, 'Данные')
    draw_arrow_line(ax, 3.65, 1.5, 2.35, 1.5, 'Пара\nметрик')
    draw_arrow_line(ax, 4.5, 3.15, 4.5, 2.35, 'Результат')
    
    # Data stores
    for (x, y, text) in [(0.0, 1.5, 'D1\nРезультаты'), (8.5, 1.5, 'D2\nОтчёты')]:
        # Double rectangle (data store)
        box1 = FancyBboxPatch((x - 0.4, y - 0.3), 1.1, 0.6,
                              boxstyle="square,pad=0", linewidth=0.8,
                              edgecolor='black', facecolor='white')
        ax.add_patch(box1)
        ax.text(x + 0.1, y, text, fontsize=6, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_a6_dfd_level1.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_a6_dfd_level1.png done")


# === A.7 — UML: Диаграмма компонентов ===
def gen_a_7():
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    ax.set_xlim(-0.5, 9)
    ax.set_ylim(-0.5, 6.5)
    ax.axis('off')
    
    ax.text(4.5, 6.2, 'UML: Диаграмма компонентов', fontsize=10,
            ha='center', fontfamily='DejaVu Sans', fontweight='bold')
    
    # Components as rectangles with tabs
    components = [
        (0.5, 3.5, 2.2, 2.0, 'GUI\n(PyQt5)'),
        (3.2, 3.5, 2.2, 2.0, 'Service\nLayer'),
        (5.9, 3.5, 2.5, 2.0, 'Transform\nEngine'),
        (0.5, 0.5, 2.2, 2.0, 'Metrics\nModule'),
        (3.2, 0.5, 2.2, 2.0, 'File I/O'),
        (5.9, 0.5, 2.5, 2.0, 'Config\nManager'),
    ]
    
    for (x, y, w, h, text) in components:
        box = FancyBboxPatch((x, y), w, h,
                             boxstyle="square,pad=0", linewidth=1.0,
                             edgecolor='black', facecolor='white')
        ax.add_patch(box)
        # Component tab
        tab = FancyBboxPatch((x + 0.3, y + h - 0.05), w * 0.4, 0.3,
                             boxstyle="square,pad=0", linewidth=0.8,
                             edgecolor='black', facecolor='white')
        ax.add_patch(tab)
        ax.text(x + w/2, y + h/2, text, fontsize=7, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    # Connections
    draw_arrow_line(ax, 2.7, 4.5, 3.2, 4.5, '')
    draw_arrow_line(ax, 5.4, 4.5, 5.9, 4.5, '')
    draw_arrow_line(ax, 2.7, 1.5, 3.2, 1.5, '')
    draw_arrow_line(ax, 5.4, 1.5, 5.9, 1.5, '')
    draw_arrow_line(ax, 1.6, 3.5, 1.6, 2.5, '')
    draw_arrow_line(ax, 4.3, 3.5, 4.3, 2.5, '')
    draw_arrow_line(ax, 7.15, 3.5, 7.15, 2.5, '')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_a7_uml_components.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_a7_uml_components.png done")


# === A.8 — UML: Диаграмма компонентов системы ===
def gen_a_8():
    fig, ax = plt.subplots(1, 1, figsize=(8, 7))
    ax.set_xlim(-0.5, 9)
    ax.set_ylim(-0.5, 7.5)
    ax.axis('off')
    
    ax.text(4.5, 7.2, 'UML: Диаграмма компонентов системы', fontsize=10,
            ha='center', fontfamily='DejaVu Sans', fontweight='bold')
    
    # Main system boundary
    sys_box = FancyBboxPatch((0.5, 0.5), 7.5, 6.0,
                              boxstyle="round,pad=0.15", linewidth=1.5,
                              edgecolor='black', facecolor='none', linestyle='--')
    ax.add_patch(sys_box)
    ax.text(4.25, 6.2, 'Аудиопроцессор v1.0', fontsize=9,
            ha='center', fontfamily='DejaVu Sans', fontstyle='italic')
    
    # Inner components
    components = [
        (1.0, 4.0, 2.0, 1.5, 'MainWindow\n(Графический\nинтерфейс)'),
        (3.5, 4.0, 2.0, 1.5, 'AudioProcessor\n(Ядро\nобработки)'),
        (6.0, 4.0, 1.8, 1.5, 'MetricEngine\n(Вычисление\nметрик)'),
        (1.0, 1.2, 2.0, 1.5, 'TransformPlugin\n(FFT, FWHT,\nDCT, DWT...)'),
        (3.5, 1.2, 2.0, 1.5, 'FileHandler\n(Чтение/запись\nWAV/MP3)'),
        (6.0, 1.2, 1.8, 1.5, 'ReportGen\n(Генерация\nотчётов)'),
    ]
    
    for (x, y, w, h, text) in components:
        box = FancyBboxPatch((x, y), w, h,
                             boxstyle="square,pad=0", linewidth=1.0,
                             edgecolor='black', facecolor='white')
        ax.add_patch(box)
        # Tab
        tab = FancyBboxPatch((x + 0.2, y + h - 0.05), w * 0.35, 0.25,
                             boxstyle="square,pad=0", linewidth=0.8,
                             edgecolor='black', facecolor='white')
        ax.add_patch(tab)
        ax.text(x + w/2, y + h/2 - 0.1, text, fontsize=6, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    # Connections
    draw_arrow_line(ax, 3.0, 4.75, 3.5, 4.75, '')
    draw_arrow_line(ax, 5.5, 4.75, 6.0, 4.75, '')
    draw_arrow_line(ax, 3.0, 1.95, 3.5, 1.95, '')
    draw_arrow_line(ax, 5.5, 1.95, 6.0, 1.95, '')
    draw_arrow_line(ax, 2.0, 4.0, 2.0, 2.7, '')
    draw_arrow_line(ax, 4.5, 4.0, 4.5, 2.7, '')
    draw_arrow_line(ax, 6.9, 4.0, 6.9, 2.7, '')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_a8_uml_system.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_a8_uml_system.png done")


# === A.9 — Диаграмма потоков данных (детальная) ===
def gen_a_9():
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    ax.set_xlim(-0.5, 9.5)
    ax.set_ylim(-0.5, 6.5)
    ax.axis('off')
    
    ax.text(4.5, 6.2, 'DFD: Детальная диаграмма потоков данных', fontsize=10,
            ha='center', fontfamily='DejaVu Sans', fontweight='bold')
    
    # Processes
    processes = [
        (1.5, 4.0, 'P1', 'Чтение\nWAV-файла'),
        (4.0, 4.0, 'P2', 'Нормализация\nамплитуды'),
        (6.5, 4.0, 'P3', 'Прямое\nпреобразование'),
        (2.5, 1.5, 'P4', 'Обработка\nкоэффициентов'),
        (5.5, 1.5, 'P5', 'Обратное\nпреобразование'),
        (8.0, 1.5, 'P6', 'Запись\nWAV-файла'),
    ]
    
    for (x, y, label, text) in processes:
        circle = plt.Circle((x, y), 0.8, linewidth=1.0,
                             edgecolor='black', facecolor='white')
        ax.add_patch(circle)
        ax.text(x, y + 0.15, label, fontsize=7, ha='center', va='center',
                fontfamily='DejaVu Sans', fontweight='bold')
        ax.text(x, y - 0.2, text, fontsize=6, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    # Flows
    draw_arrow_line(ax, 2.3, 4.0, 3.2, 4.0, 'Сырые\nданные')
    draw_arrow_line(ax, 4.8, 4.0, 5.7, 4.0, 'Нормализ.\nсигнал')
    draw_arrow_line(ax, 6.5, 3.2, 5.5, 2.3, 'Коэффициенты')
    draw_arrow_line(ax, 3.3, 1.5, 4.7, 1.5, 'Обработ.\nкоэффициенты')
    draw_arrow_line(ax, 6.3, 1.5, 7.2, 1.5, 'Восстанов.\nсигнал')
    
    # Data stores
    for (x, y, text) in [(0.0, 4.0, 'D1\nWAV-файл'), (0.0, 1.5, 'D2\nНастройки'), (8.8, 4.0, 'D3\nПараметры')]:
        box = FancyBboxPatch((x - 0.3, y - 0.25), 0.9, 0.5,
                             boxstyle="square,pad=0", linewidth=0.8,
                             edgecolor='black', facecolor='white')
        ax.add_patch(box)
        ax.text(x + 0.15, y, text, fontsize=5.5, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    draw_arrow_line(ax, 0.6, 4.0, 0.7, 4.0, '')
    draw_arrow_line(ax, 0.6, 1.5, 1.7, 1.5, 'Параметры')
    draw_arrow_line(ax, 8.3, 4.0, 7.3, 4.3, 'Метод')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_a9_dfd_detailed.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_a9_dfd_detailed.png done")


# Generate all
gen_a_1()
gen_a_2()
gen_a_3()
gen_a_4()
gen_a_5()
gen_a_6()
gen_a_7()
gen_a_8()
gen_a_9()
print("\nAll appendix diagrams generated!")
