#!/usr/bin/env python3
"""Replace images in DOCX: fix all problem figures, remove duplicate 2.1, add code captions."""
import zipfile
import shutil
import os
import copy
from lxml import etree

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
}

DOCX_PATH = "/home/z/my-project/download/repo/docs/VKR_ИТОГОВЫЙ_ОБРАБОТАННЫЙ.docx"
PNG_DIR = "/home/z/my-project/download/repo/docs/figures_gost/png"

# === MAPPING: rId -> new PNG file to replace ===
# Flowcharts
REPLACE_MAP = {
    # Рис. 1.3 — Процесс кодирования WAV → MP3
    'rId12': 'fig_1_3.png',
    # Рис. 2.2 — Use case diagram
    'rId22': 'fig_2_2_usecase.png',
    # Рис. 2.3 — Architecture
    'rId23': 'fig_2_3_architecture.png',
    # Рис. 2.4 — Sequence (rId24) — not mentioned as problem, skip
    # Рис. 2.5 — OLA algorithm
    'rId25': 'fig_2_5.png',
    # Рис. 2.6 — Class hierarchy
    'rId26': 'fig_2_6_class_hierarchy.png',
    # Рис. 2.7 FFT — first image is flowchart
    'rId27': 'fig_2_7_fft_flow.png',
    # Рис. 2.7 FFT — second image becomes CODE
    'rId52': 'fig_2_7_fft_code.png',
    # Рис. 2.8 FWHT — first = flowchart
    'rId41': 'fig_2_8_fwht_flow.png',
    # Рис. 2.8 FWHT — second = code
    'rId51': 'fig_2_8_fwht_code.png',
    # Рис. 2.9 DCT — first = flowchart
    'rId28': 'fig_2_9_dct_flow.png',
    # Рис. 2.9 DCT — second = code
    'rId50': 'fig_2_9_dct_code.png',
    # Рис. 2.10 DWT — first = flowchart
    'rId29': 'fig_2_10_dwt_flow.png',
    # Рис. 2.10 DWT — second = code
    'rId49': 'fig_2_10_dwt_code.png',
    # Рис. 2.11 mu-law — first = flowchart
    'rId30': 'fig_2_11_mulaw_flow.png',
    # Рис. 2.11 mu-law — second = code
    'rId48': 'fig_2_11_mulaw_code.png',
    # Рис. 2.12 Rosenbrock — first = flowchart
    'rId31': 'fig_2_12_rosen_flow.png',
    # Рис. 2.12 Rosenbrock — second = code
    'rId47': 'fig_2_12_rosen_code.png',
    # Appendix IDEF0
    'rId38': 'fig_a1_idef0_context.png',   # A.1
    'rId39': 'fig_a2_idef0_a0.png',       # A.2
    'rId40': 'fig_a3_idef0_a2.png',       # A.3 first
    'rId54': 'fig_a3_idef0_a2.png',       # A.3 second (reuse)
    # Appendix DFD
    'rId42': 'fig_a4_dfd.png',            # A.4
    'rId43': 'fig_a5_dfd_context.png',    # A.5
    'rId44': 'fig_a6_dfd_level1.png',     # A.6
    # Appendix UML
    'rId45': 'fig_a7_uml_components.png', # A.7
    'rId37': 'fig_a8_uml_system.png',     # A.8
    # Appendix A.9
    'rId36': 'fig_a9_dfd_detailed.png',   # A.9
}

# Duplicate to REMOVE (Рис. 2.1 second copy at para 184)
REMOVE_DUPLICATE_RIDS = ['rId53']

# Paragraph index of duplicate image (para 184)
DUPLICATE_PARA_INDEX = 184


def main():
    # Read DOCX
    tmp_dir = "/tmp/docx_fix"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    
    with zipfile.ZipFile(DOCX_PATH, 'r') as z:
        z.extractall(tmp_dir)
    
    # Parse relationships
    rels_path = os.path.join(tmp_dir, 'word', '_rels', 'document.xml.rels')
    rels_tree = etree.parse(rels_path)
    rels_root = rels_tree.getroot()
    
    # Build rId -> target mapping
    rid_to_target = {}
    for rel in rels_root:
        rid = rel.get('Id')
        target = rel.get('Target', '')
        rtype = rel.get('Type', '')
        if 'media/' in target:
            rid_to_target[rid] = target
    
    print("=== REPLACING IMAGES IN DOCX ===\n")
    
    # Replace image files in word/media/
    media_dir = os.path.join(tmp_dir, 'word', 'media')
    replaced_count = 0
    
    for rid, new_png in REPLACE_MAP.items():
        if rid not in rid_to_target:
            print(f"  WARNING: {rid} not found in rels")
            continue
        
        target = rid_to_target[rid]  # e.g. media/gost_55.png
        old_file = os.path.join(tmp_dir, 'word', target)
        new_file = os.path.join(PNG_DIR, new_png)
        
        if not os.path.exists(new_file):
            print(f"  ERROR: {new_file} not found!")
            continue
        
        if not os.path.exists(old_file):
            print(f"  WARNING: {old_file} not found in DOCX")
            continue
        
        shutil.copy2(new_file, old_file)
        replaced_count += 1
        print(f"  OK: {rid} ({target}) <- {new_png}")
    
    print(f"\nReplaced {replaced_count} images")
    
    # Now fix the document XML
    doc_path = os.path.join(tmp_dir, 'word', 'document.xml')
    doc_tree = etree.parse(doc_path)
    doc_root = doc_tree.getroot()
    
    body = doc_root.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body')
    paragraphs = body.findall('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
    
    # === 1. Remove duplicate image paragraph (para 184) ===
    if DUPLICATE_PARA_INDEX < len(paragraphs):
        dup_para = paragraphs[DUPLICATE_PARA_INDEX]
        # Verify it contains rId53
        blips = dup_para.findall('.//' + '{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
        has_dup = False
        for blip in blips:
            rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if rid in REMOVE_DUPLICATE_RIDS:
                has_dup = True
                break
        
        if has_dup:
            body.remove(dup_para)
            print(f"\nRemoved duplicate image at paragraph {DUPLICATE_PARA_INDEX}")
        else:
            print(f"\nWARNING: paragraph {DUPLICATE_PARA_INDEX} doesn't have duplicate rId")
    
    # Re-read paragraphs after removal
    paragraphs = body.findall('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
    
    # === 2. Add code figure captions after each method's second image ===
    # For each method (2.7-2.12), we need to find the second image and add a caption after it
    # Structure currently:
    # Para [IMG1 - flowchart]
    # Para "Схема обработки методом X на рисунке X.Y."
    # Para [IMG2 - code screenshot]  <-- we need to add caption AFTER this
    # Para "Рисунок X.Y — Схема обработки методом X"
    
    code_captions = {
        # rId of code image -> caption text to INSERT after it
        'rId52': 'Рисунок 2.7а — Реализация метода FFT',
        'rId51': 'Рисунок 2.8а — Реализация метода FWHT',
        'rId50': 'Рисунок 2.9а — Реализация метода DCT',
        'rId49': 'Рисунок 2.10а — Реализация метода DWT',
        'rId48': 'Рисунок 2.11а — Реализация метода \u03bc-law',
        'rId47': 'Рисунок 2.12а — Реализация метода Rosenbrock',
    }
    
    ns_w = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    ns_r = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    ns_a = 'http://schemas.openxmlformats.org/drawingml/2006/main'
    
    captions_added = 0
    # Find paragraphs containing code images and insert captions after them
    # We need to iterate carefully since we're modifying the tree
    paras_to_process = []
    for i, p in enumerate(paragraphs):
        blips = p.findall('.//' + '{%s}blip' % ns_a)
        for blip in blips:
            rid = blip.get('{%s}embed' % ns_r)
            if rid in code_captions:
                paras_to_process.append((i, p, code_captions[rid]))
                break
    
    for (idx, para, caption_text) in paras_to_process:
        # Check if a caption already exists right after (avoid duplicates)
        next_idx = list(body).index(para) + 1
        children = list(body)
        if next_idx < len(children):
            next_p = children[next_idx]
            next_text = ''.join(t.text or '' for t in next_p.iter('{%s}t' % ns_w))
            if 'а — Реализация' in next_text:
                print(f"  Caption already exists after code image for {caption_text[:15]}")
                continue
        
        # Create caption paragraph
        # Get style from existing figure captions
        cap_style = 'Рисунок'  # Will use a simple style
        new_para = etree.Element('{%s}p' % ns_w)
        
        # Add pPr
        ppr = etree.SubElement(new_para, '{%s}pPr' % ns_w)
        jc = etree.SubElement(ppr, '{%s}jc' % ns_w)
        jc.set('{%s}val' % ns_w, 'center')
        
        # Add run with text
        run = etree.SubElement(new_para, '{%s}r' % ns_w)
        rpr = etree.SubElement(run, '{%s}rPr' % ns_w)
        sz = etree.SubElement(rpr, '{%s}sz' % ns_w)
        sz.set('{%s}val' % ns_w, '22')  # 11pt
        szcs = etree.SubElement(rpr, '{%s}szCs' % ns_w)
        szcs.set('{%s}val' % ns_w, '22')
        rfont = etree.SubElement(rpr, '{%s}rFonts' % ns_w)
        rfont.set('{%s}ascii' % ns_w, 'Times New Roman')
        rfont.set('{%s}hAnsi' % ns_w, 'Times New Roman')
        rfont.set('{%s}cs' % ns_w, 'Times New Roman')
        
        t = etree.SubElement(run, '{%s}t' % ns_w)
        t.text = caption_text
        t.set('{%s}space' % ns_w, 'preserve')
        
        # Insert after the image paragraph
        para_idx = list(body).index(para)
        body.insert(para_idx + 1, new_para)
        captions_added += 1
        print(f"  Added caption: {caption_text}")
    
    print(f"\nAdded {captions_added} code figure captions")
    
    # Save modified document.xml
    doc_tree.write(doc_path, xml_declaration=True, encoding='UTF-8', standalone=True)
    
    # Repack DOCX
    out_path = DOCX_PATH  # Overwrite original
    tmp_docx = tmp_dir + '.docx'
    
    with zipfile.ZipFile(DOCX_PATH, 'r') as orig_zip:
        with zipfile.ZipFile(tmp_docx, 'w', zipfile.ZIP_DEFLATED) as new_zip:
            for item in orig_zip.infolist():
                extracted_path = os.path.join(tmp_dir, item.filename)
                if os.path.exists(extracted_path):
                    if item.filename == 'word/document.xml':
                        # Write modified document.xml
                        with open(extracted_path, 'rb') as f:
                            new_zip.writestr(item, f.read())
                    else:
                        with open(extracted_path, 'rb') as f:
                            new_zip.writestr(item, f.read())
                else:
                    # Keep original
                    new_zip.writestr(item, orig_zip.read(item.filename))
    
    shutil.move(tmp_docx, out_path)
    shutil.rmtree(tmp_dir)
    
    print(f"\nDOCX saved: {out_path}")
    print("DONE!")

if __name__ == '__main__':
    main()
