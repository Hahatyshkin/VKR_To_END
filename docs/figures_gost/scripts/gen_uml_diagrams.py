#!/usr/bin/env python3
"""Generate UML diagrams: Use Case (2.2), Architecture (2.3), Class Hierarchy (2.6)."""
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


# === РИСУНОК 2.2 — Диаграмма вариантов использования ===
def gen_fig_2_2():
    fig, ax = plt.subplots(1, 1, figsize=(7, 8))
    ax.set_xlim(-1, 9)
    ax.set_ylim(-0.5, 9)
    ax.axis('off')
    
    # System boundary
    sys_rect = FancyBboxPatch((2.0, 0.0), 5.5, 8.5,
                               boxstyle="round,pad=0.15", linewidth=1.5,
                               edgecolor='black', facecolor='white')
    ax.add_patch(sys_rect)
    ax.text(4.75, 8.2, 'Аудиопроцессор', fontsize=10, ha='center', va='center',
            fontfamily='DejaVu Sans', fontweight='bold')
    
    # Use cases (ellipses)
    use_cases = [
        (4.75, 7.2, 'Загрузить\nWAV-файл'),
        (4.75, 5.8, 'Выбрать метод\nобработки'),
        (4.75, 4.4, 'Выполнить\nпреобразование'),
        (4.75, 3.0, 'Просмотреть\nрезультаты'),
        (4.75, 1.6, 'Сравнить\nметрики'),
    ]
    
    for (x, y, text) in use_cases:
        ellipse = plt.Circle((x, y), 0.8, linewidth=1.0,
                              edgecolor='black', facecolor='white')
        ax.add_patch(ellipse)
        ax.text(x, y, text, fontsize=7, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    # Actor (User) - stick figure
    ax_x = 0.5
    # Head
    head = plt.Circle((ax_x, 5.5), 0.2, linewidth=1.0,
                       edgecolor='black', facecolor='white')
    ax.add_patch(head)
    # Body
    ax.plot([ax_x, ax_x], [5.3, 4.5], 'k-', lw=1.2)
    # Arms
    ax.plot([ax_x-0.3, ax_x+0.3], [5.1, 5.1], 'k-', lw=1.2)
    # Legs
    ax.plot([ax_x, ax_x-0.25], [4.5, 3.9], 'k-', lw=1.2)
    ax.plot([ax_x, ax_x+0.25], [4.5, 3.9], 'k-', lw=1.2)
    ax.text(ax_x, 3.5, 'Пользователь', fontsize=8, ha='center',
            fontfamily='DejaVu Sans')
    
    # Lines from actor to use cases
    for (x, y, _) in use_cases:
        ax.plot([ax_x + 0.3, x - 0.8], [5.0, y], 'k-', lw=0.8)
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_2_2_usecase.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_2_2_usecase.png done")


# === РИСУНОК 2.3 — Архитектура программного комплекса ===
def gen_fig_2_3():
    fig, ax = plt.subplots(1, 1, figsize=(6, 8))
    ax.set_xlim(-0.5, 7.5)
    ax.set_ylim(-0.5, 9)
    ax.axis('off')
    
    bw = 5.5
    bh = 0.9
    cx = 3.5
    
    # Layers
    layers = [
        (cx, 7.8, bw, bh, 'GUI (PyQt5)\nГлавное окно | Панель управления | Визуализация', '#F5F5F5'),
        (cx, 6.3, bw, bh, 'Сервисный слой\nОркестрация | Управление настройками', '#F0F0F0'),
        (cx, 4.4, bw, 1.4, 'Модули преобразований\nFFT | FWHT | DCT | DWT | mu-law | Rosenbrock', '#EBEBEB'),
        (cx, 2.5, bw, bh, 'Модуль метрик\nSNR | SI-SDR | LSD | PESQ | ODG', '#E5E5E5'),
        (cx, 1.0, bw, bh, 'Ввод/Вывод\nЧтение/запись WAV | Экспорт результатов', '#F0F0F0'),
    ]
    
    for (x, y, w, h, text, color) in layers:
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                             boxstyle="round,pad=0.08", linewidth=1.2,
                             edgecolor='black', facecolor=color)
        ax.add_patch(box)
        ax.text(x, y, text, fontsize=7.5, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    # Arrows between layers
    for i in range(len(layers)-1):
        y1 = layers[i][1] - layers[i][3]/2
        y2 = layers[i+1][1] + layers[i+1][3]/2
        ax.annotate('', xy=(cx, y2), xytext=(cx, y1),
                    arrowprops=dict(arrowstyle='<->', color='black', lw=1.0))
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_2_3_architecture.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_2_3_architecture.png done")


# === РИСУНОК 2.6 — Иерархия классов ===
def gen_fig_2_6():
    fig, ax = plt.subplots(1, 1, figsize=(7, 4.5))
    ax.set_xlim(-0.5, 8.5)
    ax.set_ylim(-0.5, 5)
    ax.axis('off')
    
    # Base class
    def draw_class_box(ax, x, y, w, h, name, attrs, methods):
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                             boxstyle="square,pad=0", linewidth=1.0,
                             edgecolor='black', facecolor='white')
        ax.add_patch(box)
        
        # Class name section
        name_h = 0.35
        ax.plot([x - w/2, x + w/2], [y + h/2 - name_h, y + h/2 - name_h], 'k-', lw=0.8)
        ax.text(x, y + h/2 - name_h/2, name, fontsize=8, ha='center', va='center',
                fontfamily='DejaVu Sans', fontweight='bold')
        
        # Attributes
        attr_y = y + h/2 - name_h
        for i, attr in enumerate(attrs):
            ax.text(x - w/2 + 0.1, attr_y - 0.2 - i*0.22, attr, fontsize=6,
                    ha='left', va='center', fontfamily='DejaVu Sans Mono')
        
        # Separator
        sep_y = y + h/2 - name_h - len(attrs)*0.22 - 0.1
        ax.plot([x - w/2, x + w/2], [sep_y, sep_y], 'k-', lw=0.5)
        
        # Methods
        for i, method in enumerate(methods):
            ax.text(x - w/2 + 0.1, sep_y - 0.2 - i*0.22, method, fontsize=6,
                    ha='left', va='center', fontfamily='DejaVu Sans Mono')
    
    # Base class
    draw_class_box(ax, 4.0, 4.0, 3.5, 1.0,
                   'BaseTransform (abstract)',
                   ['# threshold: float'],
                   ['+ process(inp, out)', '+ forward(signal)', '+ inverse(coeffs)'])
    
    # Child classes - spread horizontally
    children = [
        ('FFTTransform', 0.8),
        ('FWHTTransform', 2.3),
        ('DCTTransform', 3.8),
        ('DWTTransform', 5.3),
        ('MuLawTransform', 6.8),
        ('RosenbrockTransform', 8.0),
    ]
    
    # Inheritance arrows
    for name, x in children:
        ax.annotate('', xy=(x, 2.7), xytext=(4.0, 3.5),
                    arrowprops=dict(arrowstyle='-|>', color='black', lw=0.8))
    
    # Child class boxes
    cw, ch = 1.35, 0.65
    for name, x in children:
        box = FancyBboxPatch((x - cw/2, 2.0), cw, ch,
                             boxstyle="square,pad=0", linewidth=0.8,
                             edgecolor='black', facecolor='white')
        ax.add_patch(box)
        ax.text(x, 2.35, name, fontsize=6.5, ha='center', va='center',
                fontfamily='DejaVu Sans')
    
    plt.tight_layout()
    fig.savefig(f'{OUT}/fig_2_6_class_hierarchy.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("fig_2_6_class_hierarchy.png done")


gen_fig_2_2()
gen_fig_2_3()
gen_fig_2_6()
print("\nAll UML diagrams generated!")
