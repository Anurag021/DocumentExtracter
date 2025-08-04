import re
import os
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path
import pytesseract
import pandas as pd

# Path to Tesseract executable
#pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_pagewise(pdf_path):
    print("Converting PDF pages to images...")
    images = convert_from_path(pdf_path, dpi=300)
    return images

def parse_voter_blocks(text):
    text = text.replace('ः', ':').replace('::', ':').replace('लिंगः:', 'लिंग:') \
        .replace('पिता का नामः:', 'पिता का नाम:').replace('पति का नामः:', 'पति का नाम:')

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    blocks = []
    block = {}

    # Flexible EPIC pattern to catch noisy OCR outputs
    epic_fuzzy = re.compile(r'([^\s]{2,4}[^A-Za-z0-9]?[0-9]{6,})', re.UNICODE)
    name_pattern = re.compile(r'^निर्वाचक का नाम[: ]*(.+)$')
    relation_pattern = re.compile(r'^(पति|पिता) का नाम[: ]*(.+)$')
    house_pattern = re.compile(r'^मकान संख्या[: ]*(.+)$')
    age_gender_pattern = re.compile(r'^उम्र[: ]*(\d+)\s*लिंग[: ]*(.+)$')
    photo_pattern = re.compile(r'फोटो उपलब्ध')
    serial_pattern = re.compile(r'^\d{1,3}$')

    for line in lines:
        # Start new block if a name line comes
        if name_pattern.match(line) and block:
            blocks.append(block)
            block = {}

        # EPIC matching (fuzzy and forgiving)
        match = epic_fuzzy.search(line)
        # print(match)
        if match:
            raw = match.group(1)
            cleaned = re.sub(r'[^A-Z0-9]', '', raw.upper())  # Normalize to uppercase, remove junk
            if 8 <= len(cleaned) <= 12 and cleaned[0].isalpha():
                # Valid EPIC format
                if block and 'epic' not in block:
                    block['epic'] = cleaned
                elif blocks and 'epic' not in blocks[-1]:
                    blocks[-1]['epic'] = cleaned
                continue  # Don't double-process line
            print(cleaned)

        # Other fields
        if name_pattern.match(line):
            block['name'] = name_pattern.match(line).group(1).strip()
        elif relation_pattern.match(line):
            block['relation_type'] = relation_pattern.match(line).group(1)
            block['relation_name'] = relation_pattern.match(line).group(2).strip()
        elif house_pattern.match(line):
            block['house'] = house_pattern.match(line).group(1).strip()
        elif age_gender_pattern.match(line):
            block['age'] = age_gender_pattern.match(line).group(1).strip()
            block['gender'] = age_gender_pattern.match(line).group(2).strip()
        elif photo_pattern.search(line):
            block['photo'] = 'फोटो उपलब्ध'
        elif serial_pattern.match(line) and block:
            blocks.append(block)
            block = {}

    if block:
        blocks.append(block)

    # Format blocks for rendering
    output_blocks = []
    for b in blocks:
        s = []
        if 'epic' in b:
            s.append(f"EPIC: {b['epic']}")
        if 'name' in b:
            s.append(f"निर्वाचक का नाम: {b['name']}")
        if 'relation_type' in b and 'relation_name' in b:
            s.append(f"{b['relation_type']} का नाम: {b['relation_name']}")
        if 'house' in b:
            s.append(f"मकान संख्या: {b['house']}")
        if 'photo' in b:
            s.append(f"{b['photo']}")
        if 'age' in b and 'gender' in b:
            s.append(f"उम्र {b['age']} लिंग {b['gender']}")
        if s:
            output_blocks.append('\n'.join(s))
    return output_blocks

def render_text_to_image(text_blocks, font_path, out_path):
    font_size = 28
    img_width = 1200
    lines = []
    for block in text_blocks:
        lines += block.split('\n') + ['']
    img_height = max(1200, (font_size + 12) * (len(lines) + 2))
    img = Image.new('RGB', (img_width, img_height), color='white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except OSError:
        print("ERROR: Font not found or not readable. Check your path.")
        return
    y = 16
    for block in text_blocks:
        for line in block.split('\n'):
            draw.text((36, y), line, font=font, fill='black')
            y += font_size + 9
        y += font_size // 2
    img = img.crop((0, 0, img_width, y + 20))
    img.save(out_path)
    print(f"✅ Image saved to {out_path}")

def main():
    extracted_data = []
    #OCR 02.pdf
    pdf_path = r"/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/OCR 02.pdf"
    #SampleFiles
    font_path = r"/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles\fonts\NotoSansDevanagari-VariableFont_wdth,wght.ttf"
    output_dir = "output_pages"
    os.makedirs(output_dir, exist_ok=True)

    print("Extracting pages from PDF...")
    images = extract_text_pagewise(pdf_path)

    for page_num, img in enumerate(images, start=1):
        print(f"🔍 OCR on page {page_num}...")
        text = pytesseract.image_to_string(img, lang='hin')
        blocks = parse_voter_blocks(text)

        if not blocks:
            print(f"❌ No blocks found on page {page_num}")
            continue

        print(f"✅ Parsed {len(blocks)} voter blocks from page {page_num}")

        output_img_path = os.path.join(output_dir, f"output_page_{page_num}.png")

        #Added code----------
        extracted_data.append(blocks)
        df = pd.DataFrame(extracted_data)
        #Added code ends here--------
        render_text_to_image(blocks, font_path, output_img_path)
    df.to_excel("voter_info.xlsx", index=False, engine='openpyxl')
if __name__ == "__main__":
    main()
