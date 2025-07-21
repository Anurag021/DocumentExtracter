# Path to the file on the shared drive
#pytesseract.image_to_string(img, lang='hin')

import fitz  # PyMuPDF
import cv2
from pdf2image import convert_from_path
import pytesseract
import numpy as np
from pytesseract import Output
from PIL import Image
import os

file_path = '/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/03 Copy_250720_073911.pdf'
image_file_Path = "/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/ImageFIle.jpg"
extracted_text = '/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/extracted_text.txt'
all_text = ""

# def ReadFIleCOntents():
#    # Convert PDF pages to images
#     images = convert_from_path(file_path, dpi=300)  # dpi=300 gives better OCR accuracy

#     # Loop through pages and extract text
#     all_text = ""
#     for i, image in enumerate(images):
#         text = pytesseract.image_to_string(image, lang='hin')  # Use 'hin' for Hindi, etc.
#         all_text += f"\n\n--- Page {i + 1} ---\n{text}"

#     # Print or save the extracted text
#     print(all_text)


#     # Optional: save to a .txt file
#     with open(extracted_text, "w", encoding="utf-8") as f:
#      f.write(all_text)

def ReadFIleCOntents():
   # Convert PDF pages to images
    # images = convert_from_path(file_path, dpi=300, first_page=1, last_page=1)
    # image = images[0]
    image = cv2.imread(image_file_Path)

    # Convert to grayscale for better OCR
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Optional: Apply thresholding to enhance contrast
    thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # OCR with layout data
    ocr_data = pytesseract.image_to_data(thresh, lang='hin', output_type=Output.DICT)

    # Extract blocks (by detecting when block_num changes)
    n_boxes = len(ocr_data['text'])
    blocks = {}

    for i in range(n_boxes):
        block_num = ocr_data['block_num'][i]
        text = ocr_data['text'][i].strip()

        if text:
            if block_num not in blocks:
                blocks[block_num] = []
            blocks[block_num].append(text)
    globalText = ""
    # Display each block’s text content
    for i, texts in blocks.items():
        print(f"\n🧱 Block {i}:")
        extractText = " ".join(texts)
        globalText = globalText +"\n"+  extractText
        #all_text = "\n\n" +"\n🧱 Block {i}:" .join(extractedText) 

    # Optional: save to a .txt file
    with open(extracted_text, "w", encoding="utf-8") as f:
     f.write(globalText)

print ('Util.py Started Running')
ReadFIleCOntents()
