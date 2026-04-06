#!/usr/bin/env python3
"""
Последнее исправление: Рисунок 2.53 -> 2.5
"""

from docx import Document
import os
import subprocess

VKR_DIR = '/home/z/my-project/VKR/docs'
INPUT_DOCX = os.path.join(VKR_DIR, 'VKR_COMPLETE_FINAL.docx')
OUTPUT_DOCX = os.path.join(VKR_DIR, 'VKR_FINAL.docx')
DOWNLOAD_DIR = '/home/z/my-project/download'

def main():
    print('Последнее исправление нумерации...\n')
    doc = Document(INPUT_DOCX)
    
    # Прямые замены
    replacements = [
        ('Рисунок 2.53', 'Рисунок 2.5'),
        ('Рисунок 2.52', 'Рисунок 2.5'),
        ('Рисунок 2.51', 'Рисунок 2.5'),
    ]
    
    for para in doc.paragraphs:
        for run in para.runs:
            text = run.text
            modified = text
            for old, new in replacements:
                if old in modified:
                    modified = modified.replace(old, new)
                    print(f'  {old} -> {new}')
            if modified != text:
                run.text = modified
    
    # Сохранение
    doc.save(OUTPUT_DOCX)
    
    import shutil
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    shutil.copy(OUTPUT_DOCX, os.path.join(DOWNLOAD_DIR, 'VKR_ФИНАЛ.docx'))
    
    # PDF
    subprocess.run([
        'soffice', '--headless', '--convert-to', 'pdf',
        '--outdir', DOWNLOAD_DIR, OUTPUT_DOCX
    ], check=True, capture_output=True)
    
    print('\nГотово!')

if __name__ == '__main__':
    main()
