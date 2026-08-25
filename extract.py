import zipfile, xml.etree.ElementTree as ET
with zipfile.ZipFile('Laporan/Laporan-Web-SMK.docx') as z:
    xml_content = z.read('word/document.xml')
    root = ET.fromstring(xml_content)
    
    with open('Laporan_with_images.txt', 'w', encoding='utf-8') as f:
        for p in root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
            texts = [node.text for node in p.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
            text = ''.join(texts).strip()
            
            images = p.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing')
            
            if text or images:
                img_str = f'[IMAGE(s) FOUND: {len(images)}]' if images else ''
                f.write(f'{img_str} {text}'.strip() + '\n')
