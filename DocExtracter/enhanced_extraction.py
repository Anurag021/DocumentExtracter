import re
import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from pdf2image import convert_from_path
import pytesseract
import pandas as pd

# Path to Tesseract executable
#pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text_pagewise(pdf_path):
    """Convert PDF pages to images"""
    images = convert_from_path(pdf_path, dpi=300)
    return images


def preprocess_image_for_ocr(image):
    """Preprocess image for better OCR"""
    # Convert to grayscale
    if image.mode != 'L':
        image = image.convert('L')

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)

    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.2)

    return image


def find_all_epic_ids_with_context(text):
    """Find all EPIC IDs and get their immediate context"""
    # Multiple EPIC patterns to handle various formats
    epic_patterns = [
        r'\b([A-Z]{3}[0-9]{7})\b',  # Standard format
        r'\b([A-Z]{3}[0-9]{6,8})\b',  # Variable length
        r'([A-Z]{2,4}[^A-Za-z0-9]?[0-9]{6,8})',  # Fuzzy pattern from first code
    ]

    found_epics = []
    lines = text.split('\n')

    for line_idx, line in enumerate(lines):
        for pattern in epic_patterns:
            matches = re.finditer(pattern, line, re.UNICODE)
            for match in matches:
                epic_id = match.group(1)

                # Clean and normalize EPIC ID
                cleaned_epic = re.sub(r'[^A-Z0-9]', '', epic_id.upper())

                # Validate EPIC format
                if (8 <= len(cleaned_epic) <= 12 and
                        cleaned_epic[0].isalpha() and
                        any(c.isdigit() for c in cleaned_epic)):

                    # Normalize to 10 characters if needed
                    if len(cleaned_epic) == 9:  # 3 letters + 6 digits
                        cleaned_epic = cleaned_epic[:3] + '0' + cleaned_epic[3:]
                    elif len(cleaned_epic) == 11:  # 3 letters + 8 digits
                        cleaned_epic = cleaned_epic[:10]

                    # Get context around this EPIC ID
                    context_start = max(0, line_idx - 5)
                    context_end = min(len(lines), line_idx + 15)
                    context_lines = lines[context_start:context_end]

                    found_epics.append({
                        'epic': cleaned_epic,
                        'line_idx': line_idx,
                        'char_pos': match.start(),
                        'line_text': line,
                        'context': '\n'.join(context_lines)
                    })

    # Remove duplicates
    unique_epics = []
    seen = set()
    for epic_info in found_epics:
        if epic_info['epic'] not in seen:
            unique_epics.append(epic_info)
            seen.add(epic_info['epic'])

    # Sort by line number then character position
    unique_epics.sort(key=lambda x: (x['line_idx'], x['char_pos']))
    return unique_epics


def extract_voter_info_from_corrupted_text(epic_info):
    """Extract voter information from corrupted OCR text"""
    epic_id = epic_info['epic']
    context = epic_info['context']

    voter_info = {'epic': epic_id}

    # Since OCR is corrupted, we'll use position-based extraction
    # The format appears to be roughly:
    # EPIC_ID
    # Name_pattern (starts with Praf...)
    # Relation_pattern (starts with Uf... or similar)
    # House/Age info

    lines = [line.strip() for line in context.split('\n') if line.strip()]
    epic_line_idx = -1

    # Find the line with our EPIC ID
    for i, line in enumerate(lines):
        if epic_id in line:
            epic_line_idx = i
            break

    if epic_line_idx == -1:
        return voter_info

    # Extract information from lines following the EPIC
    for i in range(epic_line_idx + 1, min(len(lines), epic_line_idx + 8)):
        line = lines[i]

        # Check if this line contains another EPIC (stop processing)
        if re.search(r'[A-Z]{3}[0-9]{6,8}', line) and epic_id not in line:
            break

        # Pattern matching for corrupted text
        # Name patterns (usually start with "Praf")
        if (line.startswith('Praf') or 'Praf' in line) and 'name' not in voter_info:
            # Extract potential name
            name_match = re.search(r'Praf[^:]*:([^:]+)', line)
            if name_match:
                raw_name = name_match.group(1).strip()
                # Clean up the name
                cleaned_name = re.sub(r'[^a-zA-Z\s]', '', raw_name)
                if len(cleaned_name) > 3:
                    voter_info['name'] = f"Name: {cleaned_name} (OCR corrupted)"

        # Relation patterns (usually start with "Uf")
        elif (line.startswith('Uf') or 'Uf' in line) and not any(
                x in voter_info for x in ['father_name', 'husband_name']):
            relation_match = re.search(r'Uf[^:]*:([^:]+)', line)
            if relation_match:
                raw_relation = relation_match.group(1).strip()
                cleaned_relation = re.sub(r'[^a-zA-Z\s]', '', raw_relation)
                if len(cleaned_relation) > 3:
                    voter_info['father_name'] = f"Father: {cleaned_relation} (OCR corrupted)"

        # Age pattern (look for age:gender pattern like "3a:30fem")
        age_match = re.search(r'(\d+)(?:fem|ferm|fer)[:]*([a-zA-Z]*)', line)
        if age_match and 'age' not in voter_info:
            age = age_match.group(1)
            gender_raw = age_match.group(2) if age_match.group(2) else 'Unknown'

            # Convert age if reasonable
            if 15 <= int(age) <= 120:
                voter_info['age'] = age
                voter_info['gender'] = gender_raw if gender_raw else 'Unknown'

        # House number pattern
        house_match = re.search(r'([A-Z][a-z]*[A-Z]*eaM?):([0-9I]+)', line)
        if house_match and 'house' not in voter_info:
            house_num = house_match.group(2)
            if house_num != '0':  # Ignore 0 values
                voter_info['house'] = house_num

    return voter_info


def extract_voter_info_from_context(epic_info):
    """Extract comprehensive voter information from context around EPIC ID"""
    epic_id = epic_info['epic']
    context = epic_info['context']

    voter_info = {'epic': epic_id}

    # Clean context text - more comprehensive cleaning
    context = context.replace('ः', ':').replace('::', ':').replace('लिंगः:', 'लिंग:')
    context = context.replace('पिता का नामः:', 'पिता का नाम:').replace('पति का नामः:', 'पति का नाम:')
    context = context.replace('निर्वाचक का नामः:', 'निर्वाचक का नाम:')

    # Initialize extended_search to avoid UnboundLocalError
    extended_search = context

    # Find our target EPIC position in context
    epic_pattern = re.escape(epic_id)
    epic_match = re.search(epic_pattern, context)

    if not epic_match:
        # Try to find partial matches
        partial_epic = epic_id[:6]  # First 6 characters
        partial_match = re.search(re.escape(partial_epic), context)
        if partial_match:
            epic_pos = partial_match.start()
            # Get text after our partial EPIC match
            remaining_text = context[epic_pos + len(partial_epic):]

            # Limit search to next EPIC or reasonable boundary
            next_epic_pattern = r'\b[A-Z]{3}[0-9]{6,8}\b'
            next_epic_match = re.search(next_epic_pattern, remaining_text)
            if next_epic_match:
                search_text = remaining_text[:next_epic_match.start()]
            else:
                search_text = remaining_text[:1000]  # Extended search area

            # Also search text before EPIC for some patterns
            before_text = context[:epic_pos]
            extended_search = before_text[-300:] + partial_epic + search_text
        else:
            # Still try to extract info from the entire context
            extended_search = context
    else:
        epic_pos = epic_match.start()
        # Get text after our EPIC ID
        remaining_text = context[epic_pos + len(epic_id):]

        # Limit search to next EPIC or reasonable boundary
        next_epic_pattern = r'\b[A-Z]{3}[0-9]{6,8}\b'
        next_epic_match = re.search(next_epic_pattern, remaining_text)
        if next_epic_match:
            search_text = remaining_text[:next_epic_match.start()]
        else:
            search_text = remaining_text[:1000]  # Extended search area

        # Also search text before EPIC for some patterns
        before_text = context[:epic_pos]
        extended_search = before_text[-300:] + epic_id + search_text

    # More flexible patterns for voter name
    name_patterns = [
        r'निर्वाचक का नाम[:\s]*([^\n\r]+?)(?=पति|पिता|माता|मकान|उम्र|आयु|फोटो|EPIC|[A-Z]{3}[0-9])',
        r'निर्वाचक[:\s]*([^\n\r]+?)(?=पति|पिता|माता|मकान|उम्र|आयु|फोटो|EPIC|[A-Z]{3}[0-9])',
        r'नाम[:\s]*([^\n\r]+?)(?=पति|पिता|माता|मकान|उम्र|आयु|फोटो|EPIC|[A-Z]{3}[0-9])',
        # Try to find any text that looks like a name after EPIC
        r'[A-Z]{3}[0-9]{6,8}[^\w]*([^0-9\n\r]+?)(?=पति|पिता|माता|मकान|उम्र|आयु|फोटो|EPIC|[A-Z]{3}[0-9])',
    ]

    for i, pattern in enumerate(name_patterns):
        match = re.search(pattern, extended_search, re.UNICODE | re.IGNORECASE)
        if match:
            name = match.group(1).strip()

            # Clean the name
            name = re.sub(r'[|\]\[\d:।]+', '', name)
            name = re.sub(r'फोटो उपलब्ध', '', name)
            name = re.sub(r'[A-Z]{3}[0-9]+', '', name)
            name = re.sub(r'[^\u0900-\u097F\s]', '', name)  # Keep only Devanagari and spaces
            name = ' '.join(name.split())

            if 2 <= len(name) <= 60 and name and not re.search(r'[A-Z]{3}[0-9]', name):
                voter_info['name'] = name
                break

    # More flexible relation patterns
    relation_patterns = [
        (r'पति का नाम[:\s]*([^\n\r]+?)(?=मकान|उम्र|आयु|निर्वाचक|फोटो|EPIC|[A-Z]{3}[0-9]|$)', 'husband_name'),
        (r'पिता का नाम[:\s]*([^\n\r]+?)(?=मकान|उम्र|आयु|निर्वाचक|फोटो|EPIC|[A-Z]{3}[0-9]|$)', 'father_name'),
        (r'माता का नाम[:\s]*([^\n\r]+?)(?=मकान|उम्र|आयु|निर्वाचक|फोटो|EPIC|[A-Z]{3}[0-9]|$)', 'mother_name'),
        (r'पति[:\s]*([^\n\r]+?)(?=मकान|उम्र|आयु|निर्वाचक|फोटो|EPIC|[A-Z]{3}[0-9]|$)', 'husband_name'),
        (r'पिता[:\s]*([^\n\r]+?)(?=मकान|उम्र|आयु|निर्वाचक|फोटो|EPIC|[A-Z]{3}[0-9]|$)', 'father_name'),
    ]

    for pattern, field_name in relation_patterns:
        match = re.search(pattern, extended_search, re.UNICODE | re.IGNORECASE)
        if match:
            relation_name = match.group(1).strip()

            # Clean the relation name
            relation_name = re.sub(r'[|\]\[\d:।]+', '', relation_name)
            relation_name = re.sub(r'[A-Z]{3}[0-9]+', '', relation_name)
            relation_name = re.sub(r'[^\u0900-\u097F\s]', '', relation_name)
            relation_name = ' '.join(relation_name.split())

            if 2 <= len(relation_name) <= 60 and relation_name:
                voter_info[field_name] = relation_name
                break

    # More flexible house patterns
    house_patterns = [
        r'मकान संख्या[:\s]*([^\n\r]+?)(?=फोटो|उम्र|आयु|निर्वाचक|EPIC|[A-Z]{3}[0-9]|$)',
        r'मकान[:\s]*([^\n\r]+?)(?=फोटो|उम्र|आयु|निर्वाचक|EPIC|[A-Z]{3}[0-9]|$)',
        r'घर संख्या[:\s]*([^\n\r]+?)(?=फोटो|उम्र|आयु|निर्वाचक|EPIC|[A-Z]{3}[0-9]|$)',
        r'घर[:\s]*([^\n\r]+?)(?=फोटो|उम्र|आयु|निर्वाचक|EPIC|[A-Z]{3}[0-9]|$)',
    ]

    for pattern in house_patterns:
        match = re.search(pattern, extended_search, re.UNICODE | re.IGNORECASE)
        if match:
            house = match.group(1).strip()
            house = re.sub(r'[|\]\[।]+', '', house)
            house = ' '.join(house.split())
            if house and len(house) < 50 and 'फोटो' not in house:
                voter_info['house'] = house
                break

    # More flexible age and gender patterns
    age_gender_patterns = [
        r'उम्र[:\s]*(\d+)[^\d]*लिंग[:\s]*([^\n\r]+?)(?=फोटो|निर्वाचक|EPIC|[A-Z]{3}[0-9]|$)',
        r'आयु[:\s]*(\d+)[^\d]*लिंग[:\s]*([^\n\r]+?)(?=फोटो|निर्वाचक|EPIC|[A-Z]{3}[0-9]|$)',
        r'उम्र[:\s]*(\d+)',
        r'आयु[:\s]*(\d+)',
        r'Age[:\s]*(\d+)',  # Sometimes English
    ]

    for pattern in age_gender_patterns:
        match = re.search(pattern, extended_search, re.UNICODE | re.IGNORECASE)
        if match:
            age = match.group(1)
            if 15 <= int(age) <= 125:  # More lenient age check
                voter_info['age'] = age

                if len(match.groups()) > 1:
                    gender = match.group(2).strip()
                    gender = re.sub(r'[|\]\[।]+', '', gender)
                    gender = ' '.join(gender.split())
                    if gender and len(gender) < 20 and 'फोटो' not in gender:
                        voter_info['gender'] = gender
                break

    # Check for photo availability - more patterns
    photo_patterns = [
        'फोटो उपलब्ध',
        'फोटो',
        'Photo Available',
        'Photo'
    ]

    for photo_pattern in photo_patterns:
        if photo_pattern in extended_search:
            voter_info['photo'] = 'फोटो उपलब्ध'
            break

    return voter_info

def extract_all_voters_from_text(text):
    """Main function to extract all voter information"""
    # Check if text is heavily corrupted (no proper Hindi characters)
    hindi_chars = len(re.findall(r'[\u0900-\u097F]', text))
    total_chars = len(text.replace(' ', '').replace('\n', ''))

    if total_chars > 0:
        hindi_ratio = hindi_chars / total_chars

        if hindi_ratio < 0.1:  # Less than 10% Hindi characters means heavily corrupted
            return extract_all_voters_from_corrupted_text(text)

    # Method 1: Context-based extraction around EPIC IDs (for good OCR)
    epic_positions = find_all_epic_ids_with_context(text)

    all_voters = []

    if epic_positions:
        # Extract information for each EPIC ID using context method
        for epic_info in epic_positions:
            voter_info = extract_voter_info_from_context(epic_info)
            all_voters.append(voter_info)

    # Method 2: Fallback - try simple line-by-line parsing if context method didn't get details
    incomplete_voters = [v for v in all_voters if len(v) <= 2]  # Only EPIC and maybe one other field

    if incomplete_voters or not all_voters:
        fallback_voters = parse_voter_blocks_simple(text)

        if fallback_voters:
            # Merge or replace with fallback results
            if len(fallback_voters) >= len(all_voters):
                all_voters = fallback_voters
            else:
                # Try to merge information
                for i, fallback_voter in enumerate(fallback_voters):
                    if i < len(all_voters):
                        # Merge information - prefer fallback if it has more details
                        for key, value in fallback_voter.items():
                            if key not in all_voters[i] or not all_voters[i][key]:
                                all_voters[i][key] = value

    return all_voters


def extract_all_voters_from_corrupted_text(text):
    """Extract voters from heavily corrupted OCR text"""
    # Find all EPIC IDs with context
    epic_positions = find_all_epic_ids_with_context(text)

    all_voters = []

    for epic_info in epic_positions:
        voter_info = extract_voter_info_from_corrupted_text(epic_info)
        all_voters.append(voter_info)

    return all_voters


def parse_voter_blocks_simple(text):
    """Simple line-by-line parsing approach - fallback method"""
    # Clean text
    text = text.replace('ः', ':').replace('::', ':').replace('लिंगः:', 'लिंग:')
    text = text.replace('पिता का नामः:', 'पिता का नाम:').replace('पति का नामः:', 'पति का नाम:')
    text = text.replace('निर्वाचक का नामः:', 'निर्वाचक का नाम:')

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    blocks = []
    current_block = {}

    # Regex patterns
    epic_pattern = re.compile(r'([A-Z]{3}[0-9]{6,8})', re.UNICODE)
    name_pattern = re.compile(r'निर्वाचक का नाम[:\s]*(.+)', re.UNICODE)
    relation_pattern = re.compile(r'(पति|पिता|माता) का नाम[:\s]*(.+)', re.UNICODE)
    house_pattern = re.compile(r'मकान संख्या[:\s]*(.+)', re.UNICODE)
    age_gender_pattern = re.compile(r'उम्र[:\s]*(\d+)\s*लिंग[:\s]*(.+)', re.UNICODE)
    photo_pattern = re.compile(r'फोटो उपलब्ध', re.UNICODE)

    for line_num, line in enumerate(lines):
        # Check for EPIC ID
        epic_match = epic_pattern.search(line)
        if epic_match:
            # Save previous block if exists
            if current_block:
                blocks.append(current_block)

            # Start new block
            epic_id = epic_match.group(1)
            # Normalize EPIC ID
            if len(epic_id) == 9:
                epic_id = epic_id[:3] + '0' + epic_id[3:]
            current_block = {'epic': epic_id}
            continue

        # Check for name
        name_match = name_pattern.search(line)
        if name_match:
            name = name_match.group(1).strip()
            name = re.sub(r'[|\]\[\d:।]+', '', name)
            name = ' '.join(name.split())
            if len(name) > 2:
                current_block['name'] = name
            continue

        # Check for relation
        relation_match = relation_pattern.search(line)
        if relation_match:
            relation_type = relation_match.group(1)
            relation_name = relation_match.group(2).strip()
            relation_name = re.sub(r'[|\]\[\d:।]+', '', relation_name)
            relation_name = ' '.join(relation_name.split())
            if len(relation_name) > 2:
                if relation_type == 'पति':
                    current_block['husband_name'] = relation_name
                elif relation_type == 'पिता':
                    current_block['father_name'] = relation_name
                elif relation_type == 'माता':
                    current_block['mother_name'] = relation_name
            continue

        # Check for house
        house_match = house_pattern.search(line)
        if house_match:
            house = house_match.group(1).strip()
            house = re.sub(r'[|\]\[।]+', '', house)
            house = ' '.join(house.split())
            if house and 'फोटो' not in house:
                current_block['house'] = house
            continue

        # Check for age and gender
        age_gender_match = age_gender_pattern.search(line)
        if age_gender_match:
            age = age_gender_match.group(1)
            gender = age_gender_match.group(2).strip()
            gender = re.sub(r'[|\]\[।]+', '', gender)
            gender = ' '.join(gender.split())

            if 15 <= int(age) <= 125:
                current_block['age'] = age

            if gender and len(gender) < 20:
                current_block['gender'] = gender
            continue

        # Check for photo
        if photo_pattern.search(line):
            current_block['photo'] = 'फोटो उपलब्ध'
            continue

        # If line contains age without gender
        age_only_match = re.search(r'उम्र[:\s]*(\d+)', line, re.UNICODE)
        if age_only_match:
            age = age_only_match.group(1)
            if 15 <= int(age) <= 125:
                current_block['age'] = age

    # Don't forget the last block
    if current_block:
        blocks.append(current_block)

    return blocks


def format_voters_for_output(voters):
    """Format voter information for clean display"""
    if not voters:
        return ["No voter information found."]

    formatted_blocks = []

    for i, voter in enumerate(voters):
        lines = []

        # Header
        lines.append(f"=== Voter {i + 1} ===")
        lines.append("")

        # EPIC ID (always present)
        lines.append(f"EPIC: {voter['epic']}")

        # Voter name
        if 'name' in voter:
            lines.append(f"निर्वाचक का नाम: {voter['name']}")

        # Relation name
        if 'father_name' in voter:
            lines.append(f"पिता का नाम: {voter['father_name']}")
        elif 'husband_name' in voter:
            lines.append(f"पति का नाम: {voter['husband_name']}")
        elif 'mother_name' in voter:
            lines.append(f"माता का नाम: {voter['mother_name']}")

        # House number
        if 'house' in voter:
            lines.append(f"मकान संख्या: {voter['house']}")

        # Age and Gender
        age_gender_line = ""
        if 'age' in voter:
            age_gender_line = f"उम्र: {voter['age']} वर्ष"
        if 'gender' in voter:
            if age_gender_line:
                age_gender_line += f", लिंग: {voter['gender']}"
            else:
                age_gender_line = f"लिंग: {voter['gender']}"
        if age_gender_line:
            lines.append(age_gender_line)

        # Photo
        if 'photo' in voter:
            lines.append(voter['photo'])

        # Add note if OCR was corrupted
        if any('OCR corrupted' in str(value) for value in voter.values()):
            lines.append("")
            lines.append("Note: OCR text was corrupted, information may be incomplete")

        # Add separator
        lines.append("")
        lines.append("-" * 50)
        lines.append("")

        formatted_blocks.append('\n'.join(lines))

    return formatted_blocks


def render_text_to_image(text_blocks, font_path, out_path):
    """Render formatted text blocks to image"""
    if not text_blocks:
        return

    font_size = 22
    line_height = font_size + 8
    img_width = 1800
    margin_x = 30
    margin_y = 30

    # Calculate required height
    total_lines = sum(len(block.split('\n')) for block in text_blocks)
    img_height = max(1200, line_height * total_lines + margin_y * 2)

    # Create image with light background
    img = Image.new('RGB', (img_width, img_height), color='#f8f9fa')
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        font = ImageFont.truetype(font_path, font_size)
        header_font = ImageFont.truetype(font_path, font_size + 6)
        epic_font = ImageFont.truetype(font_path, font_size + 2)
    except OSError:
        font = ImageFont.load_default()
        header_font = font
        epic_font = font

    # Single color for all text
    text_color = '#2c3e50'

    # Draw text
    y = margin_y
    for block in text_blocks:
        for line in block.split('\n'):
            line = line.strip()
            if not line:
                y += line_height // 2
                continue

            # Determine font based on content
            current_font = font

            if line.startswith('=== Voter'):
                current_font = header_font
            elif line.startswith('EPIC:'):
                current_font = epic_font

            # Draw the line with single color
            draw.text((margin_x, y), line, font=current_font, fill=text_color)
            y += line_height

    # Add a border
    draw.rectangle([10, 10, img_width - 10, y + margin_y - 10], outline='#34495e', width=2)

    # Crop to actual content
    final_height = min(img_height, y + margin_y)
    img = img.crop((0, 0, img_width, final_height))
    img.save(out_path, quality=95)


def main():
    # Configuration
    extracted_data = []
    pdf_path = r"/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/OCR 02.pdf"
    font_path = r"/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles\fonts\NotoSansDevanagari-VariableFont_wdth,wght.ttf"
    output_dir = "output_pages"
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 80)
    print("ENHANCED VOTER INFORMATION EXTRACTOR")
    print("Handles both clean and corrupted OCR text")
    print("=" * 80)

    # Extract pages from PDF
    images = extract_text_pagewise(pdf_path)
    total_voters = 0

    for page_num, img in enumerate(images, start=1):
        print(f"\n🔍 Processing page {page_num}...")

        # Preprocess image for better OCR
        processed_img = preprocess_image_for_ocr(img)

        # Try multiple OCR configurations
        print("Trying multiple OCR configurations...")

        # Config 1: Hindi+English with PSM 4
        text1 = pytesseract.image_to_string(processed_img, lang='hin+eng', config='--psm 4')

        # Config 2: English only with PSM 6 (for corrupted text)
        text2 = pytesseract.image_to_string(processed_img, lang='eng', config='--psm 6')

        # Config 3: Hindi only
        text3 = pytesseract.image_to_string(processed_img, lang='hin', config='--psm 4')

        # Choose the best text based on EPIC ID detection
        texts = [text1, text2, text3]
        epic_counts = []

        for text in texts:
            epic_count = len(re.findall(r'[A-Z]{3}[0-9]{6,8}', text))
            epic_counts.append(epic_count)

        # Use the text with most EPIC IDs detected
        best_idx = epic_counts.index(max(epic_counts))
        selected_text = texts[best_idx]

        print(f"Selected OCR config {best_idx + 1} with {epic_counts[best_idx]} EPIC IDs detected")

        # Extract all voters from the page
        voters = extract_all_voters_from_text(selected_text)

        if not voters:
            print(f"❌ No voters found on page {page_num}")
            continue

        # Format for output
        formatted_blocks = format_voters_for_output(voters)

        print(f"\n✅ Successfully extracted {len(voters)} voters from page {page_num}")
        total_voters += len(voters)

        # Render to image
        output_img_path = os.path.join(output_dir, f"enhanced_voters_page_{page_num}.png")
        #Added code----------
        extracted_data.append(formatted_blocks)
        df = pd.DataFrame(extracted_data)
        #Added code ends here--------
        render_text_to_image(formatted_blocks, font_path, output_img_path)
    
    df.to_excel("voter_info.xlsx", index=False, engine='openpyxl')

    print(f"\n🎉 Processing complete! Total voters extracted: {total_voters}")
    print(f"📁 Output images saved in: {output_dir}")

    # Additional summary
    if total_voters > 0:
        print(f"\n📊 Summary:")
        print(f"   • Successfully processed {len(images)} pages")
        print(f"   • Extracted {total_voters} voter records")
        print(f"   • Average: {total_voters / len(images):.1f} voters per page")


if __name__ == "__main__":
    main()