import cv2
import pytesseract
import numpy as np
from PIL import Image
import os

# Load the image
image_path = "/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/ImageFIle.jpg"  # path to your uploaded image
output_file = '/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/extracted_text.txt'

# Set tesseract path if needed (Windows users only)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load image
image_path = image_path
image = cv2.imread(image_path)

# Dimensions
height, width, _ = image.shape

# Grid definition
rows = 10
cols = 3
cell_height = height // rows
cell_width = width // cols

# Output file
output_file = output_file
with open(output_file, "w", encoding="utf-8") as f_out:
    for row in range(rows):
        for col in range(cols):
            x1 = col * cell_width
            y1 = row * cell_height
            x2 = x1 + cell_width
            y2 = y1 + cell_height

            # Crop cell
            cell_img = image[y1:y2, x1:x2]

            # Preprocess for better OCR
            gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)

            # Extract text
            #text = pytesseract.image_to_string(gray, lang='hin+eng')
            text = pytesseract.image_to_string(gray, lang='hin')

            # Write block info and text
            f_out.write(f"\n--- Block Row {row+1}, Column {col+1} ---\n")
            f_out.write(text.strip())
            f_out.write("\n")

print(f"[✓] All extracted text saved to '{output_file}'")