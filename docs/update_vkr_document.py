#!/usr/bin/env python3
"""
Обновление VKR_Complete.docx:
- Добавление рисунков в Главу 1
- Добавление таблиц сравнения методов
- Исправление нумерации рисунков в Главе 2
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Добавляем путь к skill для импорта
skill_path = '/home/z/my-project/skills/docx'
sys.path.insert(0, skill_path)

from scripts.document import Document
from PIL import Image
import xml.etree.ElementTree as ET
import re

# Пути
VKR_DIR = '/home/z/my-project/VKR/docs'
UNPACKED_DIR = os.path.join(VKR_DIR, 'unpacked_vkr')
NEW_FIGURES_DIR = os.path.join(VKR_DIR, 'media/new_figures')
OUTPUT_DOCX = os.path.join(VKR_DIR, 'VKR_Updated.docx')

def get_next_image_id(media_dir):
    """Получить следующий ID для изображения."""
    existing = [f for f in os.listdir(media_dir) if f.startswith('image') and f.endswith('.png')]
    if not existing:
        return 28  # Начинаем с 28 (после image27.png)
    max_id = max(int(re.search(r'image(\d+)', f).group(1)) for f in existing)
    return max_id + 1

def copy_new_figures(doc):
    """Копирование новых изображений в media директорию."""
    media_dir = os.path.join(doc.unpacked_path, 'word/media')
    os.makedirs(media_dir, exist_ok=True)
    
    figures = [
        ('fig_hadamard_matrices.png', 'Матрицы Адамара'),
        ('fig_walsh_functions.png', 'Функции Уолша'),
        ('fig_fwht_butterfly.png', 'Диаграмма FWHT'),
        ('fig_fft_vs_fwht.png', 'Сравнение FFT и FWHT'),
        ('fig_audio_pipeline.png', 'Схема обработки'),
        ('fig_energy_concentration.png', 'Концентрация энергии'),
        ('fig_dwt_decomposition.png', 'Вейвлет-разложение'),
        ('fig_psychoacoustic_masking.png', 'Психоакустическое маскирование'),
    ]
    
    next_id = get_next_image_id(media_dir)
    figure_mapping = {}
    
    for src_name, desc in figures:
        src_path = os.path.join(NEW_FIGURES_DIR, src_name)
        if os.path.exists(src_path):
            dst_name = f'image{next_id}.png'
            dst_path = os.path.join(media_dir, dst_name)
            shutil.copy(src_path, dst_path)
            figure_mapping[src_name] = {
                'id': next_id,
                'filename': dst_name,
                'description': desc
            }
            print(f'Скопирован: {src_name} -> {dst_name}')
            next_id += 1
    
    return figure_mapping

def add_image_relationships(doc, figure_mapping):
    """Добавление связей для изображений."""
    rels_editor = doc['word/_rels/document.xml.rels']
    
    for src_name, info in figure_mapping.items():
        next_rid = rels_editor.get_next_rid()
        info['rid'] = next_rid
        rels_editor.append_to(rels_editor.dom.documentElement,
            f'<Relationship Id="{next_rid}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="media/{info["filename"]}"/>')
        print(f'Добавлена связь: {next_rid} -> {info["filename"]}')

def create_figure_xml(rid, width_inches=5.5, height_inches=None, img_path=None):
    """Создание XML для вставки изображения."""
    if img_path and height_inches is None:
        img = Image.open(img_path)
        aspect = img.size[1] / img.size[0]
        height_inches = width_inches * aspect
    elif height_inches is None:
        height_inches = width_inches * 0.75
    
    width_emus = int(width_inches * 914400)
    height_emus = int(height_inches * 914400)
    
    return f'''<w:p>
  <w:r>
    <w:drawing>
      <wp:inline distT="0" distB="0" distL="0" distR="0">
        <wp:extent cx="{width_emus}" cy="{height_emus}"/>
        <wp:docPr id="1" name="Picture"/>
        <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
          <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <pic:nvPicPr><pic:cNvPr id="1" name="Picture"/><pic:cNvPicPr/></pic:nvPicPr>
              <pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
              <pic:spPr><a:xfrm><a:ext cx="{width_emus}" cy="{height_emus}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
            </pic:pic>
          </a:graphicData>
        </a:graphic>
      </wp:inline>
    </w:drawing>
  </w:r>
</w:p>'''

def create_caption_xml(caption_text):
    """Создание подписи к рисунку."""
    return f'''<w:p>
  <w:pPr>
    <w:jc w:val="center"/>
    <w:spacing w:before="120" w:after="240"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:i/>
    </w:rPr>
    <w:t>{caption_text}</w:t>
  </w:r>
</w:p>'''

def create_table_xml(headers, rows, caption=None):
    """Создание XML для таблицы."""
    num_cols = len(headers)
    col_width = 9360 // num_cols  # Примерная ширина столбца
    
    # Заголовок таблицы
    caption_xml = ''
    if caption:
        caption_xml = f'''<w:p>
  <w:pPr><w:jc w:val="center"/></w:pPr>
  <w:r><w:rPr><w:b/></w:rPr><w:t>{caption}</w:t></w:r>
</w:p>'''
    
    # Заголовки
    header_cells = ''
    for h in headers:
        header_cells += f'''<w:tc>
  <w:tcPr><w:tcW w:w="{col_width}" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/></w:tcPr>
  <w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>{h}</w:t></w:r></w:p>
</w:tc>'''
    
    header_row = f'<w:tr>{header_cells}</w:tr>'
    
    # Строки данных
    data_rows = ''
    for row in rows:
        cells = ''
        for cell in row:
            cells += f'''<w:tc>
  <w:tcPr><w:tcW w:w="{col_width}" w:type="dxa"/></w:tcPr>
  <w:p><w:r><w:t>{cell}</w:t></w:r></w:p>
</w:tc>'''
        data_rows += f'<w:tr>{cells}</w:tr>'
    
    return f'''{caption_xml}
<w:tbl>
  <w:tblPr>
    <w:tblStyle w:val="TableGrid"/>
    <w:tblW w:w="9360" w:type="dxa"/>
    <w:jc w:val="center"/>
  </w:tblPr>
  <w:tblGrid>{"".join([f'<w:gridCol w:w="{col_width}"/>' for _ in range(num_cols)])}</w:tblGrid>
  {header_row}
  {data_rows}
</w:tbl>'''

def update_document(doc, figure_mapping):
    """Основное обновление документа."""
    editor = doc['word/document.xml']
    
    # ===== ГЛАВА 1: Добавление рисунков и таблиц =====
    
    # 1. Находим раздел 1.3.2 (FWHT) для добавления рисунка матриц Адамара
    try:
        node = editor.get_node(tag="w:p", contains="Матрицы Адамара строятся рекурсивно")
        if node and 'fig_hadamard_matrices.png' in figure_mapping:
            info = figure_mapping['fig_hadamard_matrices.png']
            img_path = os.path.join(doc.unpacked_path, 'word/media', info['filename'])
            fig_xml = create_figure_xml(info['rid'], width_inches=5.5, img_path=img_path)
            caption = create_caption_xml('Рисунок 1.4 — Матрицы Адамара порядков 1, 2, 4, 8')
            editor.insert_after(node, fig_xml + caption)
            print('Добавлен рисунок 1.4 (матрицы Адамара)')
    except Exception as e:
        print(f'Не удалось добавить рисунок матриц Адамара: {e}')
    
    # 2. Добавляем рисунок функций Уолша после описания FWHT
    try:
        node = editor.get_node(tag="w:p", contains="FWHT вычислительно эффективно")
        if node and 'fig_walsh_functions.png' in figure_mapping:
            info = figure_mapping['fig_walsh_functions.png']
            img_path = os.path.join(doc.unpacked_path, 'word/media', info['filename'])
            fig_xml = create_figure_xml(info['rid'], width_inches=5.5, img_path=img_path)
            caption = create_caption_xml('Рисунок 1.5 — Функции Уолша (первые 8 функций)')
            editor.insert_after(node, fig_xml + caption)
            print('Добавлен рисунок 1.5 (функции Уолша)')
    except Exception as e:
        print(f'Не удалось добавить рисунок функций Уолша: {e}')
    
    # 3. Добавляем таблицу сравнения вычислительной сложности методов
    try:
        node = editor.get_node(tag="w:p", contains="### 1.3.6. Нелинейное сглаживание")
        if node:
            headers = ['Метод', 'Операции', 'Сложность', 'Умножения']
            rows = [
                ['FFT', 'N·log₂(N)', 'O(N log N)', 'Комплексные'],
                ['FWHT', 'N·log₂(N)', 'O(N log N)', 'Нет'],
                ['DCT', 'N·log₂(N)', 'O(N log N)', 'Вещественные'],
                ['DWT (Хаар)', 'N', 'O(N)', 'Нет'],
                ['μ-law', 'N', 'O(N)', 'Нет'],
            ]
            table_xml = create_table_xml(headers, rows, 'Таблица 1.1 — Сравнение вычислительной сложности методов')
            editor.insert_before(node, table_xml)
            print('Добавлена таблица 1.1 (вычислительная сложность)')
    except Exception as e:
        print(f'Не удалось добавить таблицу сложности: {e}')
    
    # 4. Добавляем рисунок сравнения спектров FFT и FWHT
    try:
        node = editor.get_node(tag="w:p", contains="Ограниченная применимость для сигналов")
        if node and 'fig_fft_vs_fwht.png' in figure_mapping:
            info = figure_mapping['fig_fft_vs_fwht.png']
            img_path = os.path.join(doc.unpacked_path, 'word/media', info['filename'])
            fig_xml = create_figure_xml(info['rid'], width_inches=5.5, img_path=img_path)
            caption = create_caption_xml('Рисунок 1.6 — Сравнение спектров FFT и FWHT')
            editor.insert_after(node, fig_xml + caption)
            print('Добавлен рисунок 1.6 (сравнение спектров)')
    except Exception as e:
        print(f'Не удалось добавить рисунок сравнения спектров: {e}')
    
    # 5. Добавляем таблицу сравнения метрик качества
    try:
        node = editor.get_node(tag="w:p", contains="### 1.5.4. Характеристики сигнала")
        if node:
            headers = ['Метрика', 'Область', 'Диапазон', 'Описание']
            rows = [
                ['SNR', 'Временная', '0-∞ дБ', 'Отношение сигнал/шум'],
                ['SI-SDR', 'Временная', '-∞-∞ дБ', 'Масштабно-инвариантное'],
                ['LSD', 'Спектральная', '0-∞ дБ', 'Спектральное расстояние'],
                ['STOI', 'Психоакуст.', '0-1', 'Разборчивость речи'],
                ['PESQ', 'Психоакуст.', '-0.5-4.5', 'Качество речи'],
            ]
            table_xml = create_table_xml(headers, rows, 'Таблица 1.2 — Характеристики метрик качества аудиосигналов')
            editor.insert_before(node, table_xml)
            print('Добавлена таблица 1.2 (метрики качества)')
    except Exception as e:
        print(f'Не удалось добавить таблицу метрик: {e}')
    
    # 6. Добавляем рисунок концентрации энергии
    try:
        node = editor.get_node(tag="w:p", contains="## 1.4. Интеграция методов")
        if node and 'fig_energy_concentration.png' in figure_mapping:
            info = figure_mapping['fig_energy_concentration.png']
            img_path = os.path.join(doc.unpacked_path, 'word/media', info['filename'])
            fig_xml = create_figure_xml(info['rid'], width_inches=5.5, img_path=img_path)
            caption = create_caption_xml('Рисунок 1.7 — Концентрация энергии в коэффициентах преобразований')
            editor.insert_before(node, fig_xml + caption)
            print('Добавлен рисунок 1.7 (концентрация энергии)')
    except Exception as e:
        print(f'Не удалось добавить рисунок концентрации энергии: {e}')
    
    # 7. Добавляем рисунок схемы обработки аудиосигнала
    try:
        node = editor.get_node(tag="w:p", contains="## 1.6. Выводы по главе 1")
        if node and 'fig_audio_pipeline.png' in figure_mapping:
            info = figure_mapping['fig_audio_pipeline.png']
            img_path = os.path.join(doc.unpacked_path, 'word/media', info['filename'])
            fig_xml = create_figure_xml(info['rid'], width_inches=5.5, img_path=img_path)
            caption = create_caption_xml('Рисунок 1.8 — Общая схема обработки аудиосигнала в системе')
            editor.insert_before(node, fig_xml + caption)
            print('Добавлен рисунок 1.8 (схема обработки)')
    except Exception as e:
        print(f'Не удалось добавить рисунок схемы обработки: {e}')
    
    # ===== ГЛАВА 2: Исправление нумерации рисунков =====
    # Исправляем "Рисунок 2.0" на "Рисунок 2.1"
    try:
        node = editor.get_node(tag="w:t", contains="Рисунок 2.0")
        if node:
            # Заменяем текст
            parent = node.parentNode
            new_text = node.firstChild.nodeValue.replace('Рисунок 2.0', 'Рисунок 2.1')
            node.firstChild.replaceWholeText(new_text)
            print('Исправлена нумерация: Рисунок 2.0 -> 2.1')
    except Exception as e:
        print(f'Не удалось исправить нумерацию 2.0: {e}')
    
    # Исправляем "Рисунок 2.1а" на "Рисунок 2.2"
    try:
        node = editor.get_node(tag="w:t", contains="Рисунок 2.1а")
        if node:
            parent = node.parentNode
            new_text = node.firstChild.nodeValue.replace('Рисунок 2.1а', 'Рисунок 2.2')
            node.firstChild.replaceWholeText(new_text)
            print('Исправлена нумерация: Рисунок 2.1а -> 2.2')
    except Exception as e:
        print(f'Не удалось исправить нумерацию 2.1а: {e}')
    
    # Последующие рисунки в Главе 2 нужно перенумеровать
    # 2.1 -> 2.3, 2.2 -> 2.4, 2.3 -> 2.5
    renames = [
        ('Рисунок 2.1 —', 'Рисунок 2.3 —'),
        ('Рисунок 2.2 —', 'Рисунок 2.4 —'),
        ('Рисунок 2.3 —', 'Рисунок 2.5 —'),
    ]
    
    for old_text, new_text in renames:
        try:
            node = editor.get_node(tag="w:t", contains=old_text)
            if node:
                text = node.firstChild.nodeValue
                updated = text.replace(old_text, new_text)
                node.firstChild.replaceWholeText(updated)
                print(f'Исправлена нумерация: {old_text[:15]} -> {new_text[:15]}')
        except Exception as e:
            print(f'Не удалось исправить {old_text[:15]}: {e}')

def main():
    print('Обновление VKR_Complete.docx...')
    
    # Инициализация документа
    doc = Document(UNPACKED_DIR)
    
    # Копирование новых изображений
    figure_mapping = copy_new_figures(doc)
    print(f'\nСкопировано изображений: {len(figure_mapping)}')
    
    # Добавление связей для изображений
    add_image_relationships(doc, figure_mapping)
    
    # Обновление содержимого документа
    update_document(doc, figure_mapping)
    
    # Сохранение
    doc.save()
    print('\nДокумент сохранен в распакованном виде')
    
    # Упаковка
    print(f'\nУпаковка документа в {OUTPUT_DOCX}...')
    pack_script = os.path.join(skill_path, 'scripts/pack.py')
    subprocess.run(['python3', pack_script, doc.unpacked_path, OUTPUT_DOCX], check=True)
    
    print(f'\nГотово! Документ сохранен: {OUTPUT_DOCX}')
    
    # Проверка размера
    size = os.path.getsize(OUTPUT_DOCX)
    print(f'Размер файла: {size / 1024 / 1024:.2f} MB')

if __name__ == '__main__':
    main()
