#!/usr/bin/env python3
"""
Финальное исправление нумерации рисунков Главы 2 через XML.
"""

import os
import re
import zipfile
import shutil
import subprocess

VKR_DIR = '/home/z/my-project/VKR/docs'
INPUT_DOCX = os.path.join(VKR_DIR, 'VKR_ГОТОВЫЙ_ДОКУМЕНТ.docx')
OUTPUT_DOCX = os.path.join(VKR_DIR, 'VKR_ФИНАЛЬНЫЙ_ДОКУМЕНТ.docx')
DOWNLOAD_DIR = '/home/z/my-project/download'
TEMP_DIR = '/tmp/vkr_xml_fix'

def main():
    print('Исправление нумерации рисунков Главы 2...\n')
    
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
    
    # Сначала найдем все рисунки Главы 2 и их текущие номера
    print('Поиск рисунков Главы 2...')
    
    # Ищем все "Рисунок 2.X"
    pattern = r'Рисунок\s+2\.\d+[а-я]?'
    matches = re.findall(pattern, content)
    print(f'Найдено: {matches}')
    
    # Правильные замены для подписей рисунков
    # Порядок: сначала исправляем конкретные проблемы
    
    fixes = [
        # (старый паттерн, новый номер)
        ('Рисунок 2.0', 'Рисунок 2.1'),
        ('рисунок 2.0', 'рисунок 2.1'),
        ('Рисунок 2.1а', 'Рисунок 2.2'),
        ('рисунок 2.1а', 'рисунок 2.2'),
        ('Рисунок 2.1 — Архитектура', 'Рисунок 2.3 — Архитектура'),
        ('Рисунок 2.2 — Алгоритм', 'Рисунок 2.4 — Алгоритм'),
        ('Рисунок 2.3 — Иерархия', 'Рисунок 2.5 — Иерархия'),
        ('Рисунок 2.3 --- Иерархия', 'Рисунок 2.5 --- Иерархия'),
    ]
    
    modified = content
    changes = 0
    
    for old, new in fixes:
        if old in modified:
            modified = modified.replace(old, new)
            print(f'  {old} -> {new}')
            changes += 1
    
    # Если стандартные замены не помогли, делаем принудительную перенумерацию
    # Находим все подписи рисунков (с "---" или "—") в Главе 2
    
    # Сначала найдем границы Главы 2
    ch2_start = modified.find('ГЛАВА 2')
    ch3_start = modified.find('ГЛАВА 3')
    
    if ch2_start > 0 and ch3_start > ch2_start:
        ch2_content = modified[ch2_start:ch3_start]
        
        # Ищем все подписи рисунков
        fig_pattern = r'Рисунок\s+2\.\d+[а-я]?\s*[—–-]'
        fig_matches = list(re.finditer(fig_pattern, ch2_content))
        
        print(f'\nНайдено подписей рисунков в Главе 2: {len(fig_matches)}')
        
        # Перенумеровываем в обратном порядке (чтобы не сбить позиции)
        for i, match in enumerate(reversed(fig_matches)):
            old_text = match.group()
            new_num = len(fig_matches) - i
            new_text = f'Рисунок 2.{new_num} —'
            
            if old_text != new_text:
                ch2_content = ch2_content[:match.start()] + new_text + ch2_content[match.end():]
                print(f'  {old_text.strip()} -> Рисунок 2.{new_num}')
        
        modified = modified[:ch2_start] + ch2_content + modified[ch3_start:]
    
    # Запись
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(modified)
    
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
    import shutil as sh
    sh.copy(OUTPUT_DOCX, os.path.join(DOWNLOAD_DIR, 'VKR_ФИНАЛ.docx'))
    
    # PDF
    print('\nКонвертация в PDF...')
    subprocess.run([
        'soffice', '--headless', '--convert-to', 'pdf',
        '--outdir', DOWNLOAD_DIR, OUTPUT_DOCX
    ], check=True, capture_output=True)
    
    # Проверка
    print('\n=== ПРОВЕРКА РЕЗУЛЬТАТА ===')
    
    import subprocess as sp
    result = sp.run(['pandoc', OUTPUT_DOCX, '-o', '/tmp/vkr_check.md'], capture_output=True)
    
    with open('/tmp/vkr_check.md', 'r') as f:
        check_content = f.read()
    
    # Ищем рисунки Главы 2
    fig_pattern = r'Рисунок\s+2\.\d+'
    figs = re.findall(fig_pattern, check_content)
    print(f'Рисунки Главы 2: {sorted(set(figs), key=lambda x: float(x.split(".")[-1]))}')
    
    print('\nГотово!')

if __name__ == '__main__':
    main()
