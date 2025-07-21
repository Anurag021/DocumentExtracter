import cv2
import pytesseract
import numpy as np

# Optional: Set path to tesseract if it's not in PATH
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # macOS/Linux
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows

# Load the image
image_path = "/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/ImageFIle.jpg"  # path to your uploaded image
output_file = '/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/extracted_text.txt'
image = cv2.imread(image_path)

# Convert to grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Threshold the image
_, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Define kernels to detect lines
kernel_rect = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 10))
dilated = cv2.dilate(thresh, kernel_rect, iterations=1)

# Find contours of potential blocks
contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Sort contours top to bottom, left to right
contours = sorted(contours, key=lambda c: (cv2.boundingRect(c)[1], cv2.boundingRect(c)[0]))

output_texts = []

for idx, cnt in enumerate(contours):
    x, y, w, h = cv2.boundingRect(cnt)
    if w > 100 and h > 50:  # Filter small/noisy boxes
        roi = image[y:y+h, x:x+w]

        # OCR
        text = pytesseract.image_to_string(roi, lang='hin+eng', config='--psm 6')
        output_texts.append(f"Block {idx+1}:\n{text.strip()}\n{'-'*40}\n")

# Save output to file
with open(output_file, "w", encoding="utf-8") as f:
    f.writelines(output_texts)

print("✅ Text extracted and saved to {output_file}")