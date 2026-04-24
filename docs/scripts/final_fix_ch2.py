#!/usr/bin/env python3
"""
Полное исправление нумерации рисунков Главы 2 - перенумерация по порядку.
"""

import os
import re
import zipfile
import shutil
import subprocess

VKR_DIR = '/home/z/my-project/VKR/docs'
INPUT_DOCX = os.path.join(VKR_DIR, 'VKR_ГОТОВЫЙ_ДОКУМЕНТ.docx')
OUTPUT_DOCX = os.path.join(VKR_DIR, 'VKR_ИТОГОВЫЙ.docx')
DOWNLOAD_DIR = '/home/z/my-project/download'
TEMP_DIR = '/tmp/vkr_final_fix'

def main():
    print('Полное исправление нумерации Главы 2...\n')
    
    # Распаковка
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)
    
    with zipfile.ZipFile(INPUT_DOCX, 'r') as zf:
        zf.extractall(TEMP_DIR)
    
    # Чтение document.xml
    doc_path = os.path.join(TEMP_DIR, 'word/document.xml')
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Находим все вхождения "Рисунок 2.X" с контекстом
    # Нужно перенумеровать по порядку появления
    
    # Сначала соберем все позиции и текущие номера
    pattern = r'Рисунок\s+2\.\d+[а-я]?'
    
    # Найдем границы Главы 2
    ch2_start = content.find('ГЛАВА 2')
    ch3_start = content.find('ГЛАВА 3')
    
    if ch2_start < 0 or ch3_start < ch2_start:
        print('Не найдены границы Главы 2')
        return
    
    ch2_content = content[ch2_start:ch3_start]
    
    # Найдем все подписи рисунков (с тире после номера)
    caption_pattern = r'(Рисунок\s+)(2\.\d+[а-я]?)(\s*[—–-])'
    
    captions = list(re.finditer(caption_pattern, ch2_content))
    print(f'Найдено подписей рисунков: {len(captions)}')
    
    # Перенумеруем в правильном порядке
    # Создаем список замен: (позиция, старый_номер, новый_номер)
    replacements = []
    for i, match in enumerate(captions):
        old_num = match.group(2)
        new_num = f'2.{i + 1}'
        if old_num != new_num:
            replacements.append((match.start(), old_num, new_num))
            print(f'  Позиция {match.start()}: {old_num} -> {new_num}')
    
    # Применяем замены в обратном порядке (чтобы не сбить позиции)
    modified = ch2_content
    for pos, old, new in reversed(replacements):
        # Находим позицию в модифицированном контенте
        old_pattern = f'Рисунок {old}'
        new_pattern = f'Рисунок {new}'
        modified = modified.replace(old_pattern, new_pattern, 1)
    
    # Собираем обратно
    final_content = content[:ch2_start] + modified + content[ch3_start:]
    
    # Дополнительные исправления ссылок в тексте
    # "рисунок 2.0" -> "рисунок 2.1"
    final_content = final_content.replace('рисунок 2.0', 'рисунок 2.1')
    final_content = final_content.replace('Рисунок 2.0', 'Рисунок 2.1')
    
    # Запись
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    # Запаковка
    with zipfile.ZipFile(OUTPUT_DOCX, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(TEMP_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, TEMP_DIR)
                zf.write(file_path, arc_name)
    
    shutil.rmtree(TEMP_DIR)
    
    # Копирование в download
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    shutil.copy(OUTPUT_DOCX, os.path.join(DOWNLOAD_DIR, 'VKR_ИТОГ.docx'))
    
    # PDF
    print('\nКонвертация в PDF...')
    subprocess.run([
        'soffice', '--headless', '--convert-to', 'pdf',
        '--outdir', DOWNLOAD_DIR, OUTPUT_DOCX
    ], check=True, capture_output=True)
    
    # Проверка
    print('\n=== ИТОГОВАЯ ПРОВЕРКА ===')
    
    subprocess.run(['pandoc', OUTPUT_DOCX, '-o', '/tmp/vkr_final.md'], capture_output=True)
    
    with open('/tmp/vkr_final.md', 'r') as f:
        check = f.read()
    
    # Рисунки
    ch2_figs = re.findall(r'Рисунок\s+2\.\d+', check)
    unique_figs = sorted(set(ch2_figs), key=lambda x: float(x.split('.')[-1]))
    print(f'Рисунки Главы 2: {unique_figs}')
    
    # Таблицы
    tables = re.findall(r'Таблица\s+[\d.]+', check)
    print(f'Всего таблиц: {len(tables)}')
    
    print('\nГотово!')

if __name__ == '__main__':
    main()
