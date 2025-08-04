import cv2
import pytesseract
import numpy as np
from PIL import Image, ImageEnhance
import os
import os
import re
import pandas as pd
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import requests

# Load the image
image_path = "/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/ImageFIle.jpg"  # path to your uploaded image
output_file = '/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/extracted_text.txt'
# enhancedImage_path = "/Users/anuragrawat/Documents/GitHub/FreeLance/DocumentExtracter/enhanced_with_pil.jpg"

# Load processor and model ---- only for microsoft OCR
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")

# Set tesseract path if needed (Windows users only)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


#Image processing using PIL
# img = Image.open(image_path).convert('L')  # Grayscale
# img = ImageEnhance.Contrast(img).enhance(2.0)    # Double contrast
# img = ImageEnhance.Sharpness(img).enhance(2.0)   # Double sharpness
# img.save("enhanced_with_pil.jpg")

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

# Regular expressions for different fields (allow Hindi/Unicode text)
patterns = {
    'निर्वाचक का नाम': r'निर्वाचक का नाम\s*[:：]?\s*(.+)',
    'पति का नाम': r'(?:पति|पत्ति|पिता) का नाम[:：]?\s*(.+)',
    'मकान संख्या': r'मकान संख्या\s*[:：]?\s*(\d+)',
    'उम्र': r'उम्र\s*[:：]\s*(\d+)',
    'लिंग': r'लिंग\s*[:：]\s*(\w+)',
}

# Output file
extracted_data = []
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

            #userID image coordinates
            ux1 = x2 - 240
            uy1 = y1
            ux2 = x2
            uy2 = y1 + 190
            userId_img = image[uy1:uy2, ux1:ux2]

            # # Preprocess for better OCR - cv2 extraction
            gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
            grayUSerId = cv2.cvtColor(userId_img, cv2.COLOR_BGR2GRAY)
            # # Extract text
            # #text = pytesseract.image_to_string(gray, lang='hin+eng')
            text = pytesseract.image_to_string(gray, lang='hin')

            # #denoised = cv2.fastNlMeansDenoising(grayUSerId, h=30)
            
            # # thresh = cv2.adaptiveThreshold(
            # # denoised, 255, 
            # # cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            # # cv2.THRESH_BINARY, 11, 2
            # #     )

            # # Sharpening
            # # kernel = np.array([[0, -1, 0],
            # #                 [-1, 5,-1],
            # #                 [0, -1, 0]])
            # # sharpened = cv2.filter2D(denoised, -1, kernel)
            # userId = pytesseract.image_to_string(grayUSerId, lang='eng')
            # userId = 
            #uidImage = Image.open(grayUSerId).convert("RGB")
            uidImage = Image.fromarray(grayUSerId).convert("RGB")
            pixel_values = processor(images=uidImage, return_tensors="pt").pixel_values
            generated_ids = model.generate(pixel_values)
            userId = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            # # Write block info and text
            # f_out.write(f"\n--- Block Row {row+1}, Column {col+1} xycordinates are {x1 , y1 , x2 , y2}, ---\n")
            # # lines = text.splitlines()
            # # count = 0
            # # for line in lines:
            # #     count = count+1      
            # #     if "2" in line[:2]:
            # #         name = line[line.find(":"):]
            # #     elif "3" in line[:2]:
            # #         FathersName = line[line.find(":"):]

            # #     f_out.write(f"{count} - {line.strip()}")
                
            # #     f_out.write("\n")

            #--------------Microsoft ocr extraction---------
            
            f_out.write(text.strip())
            f_out.write("\n")
            f_out.write((userId.strip()).split()[0])
            f_out.write("\n")

            #extract pattern and update it into excel sheet
            # 3. Extract each field
            data = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, text)
                data[key] = match.group(1).strip() if match else ''

            data["userid"] = (userId.strip()).split()[0]   
            extracted_data.append(data)
            print(f"✅ Block Row {row+1}, Column {col+1} ---- Data extracted and saved to 'voter_info.xlsx'")

        # 4. Create a DataFrame with one row
        df = pd.DataFrame(extracted_data)

        # 5. Save to Excel
        df.to_excel("voter_info.xlsx", index=False, engine='openpyxl')

        


print(f"[✓] All extracted text saved to '{output_file}'")

###---------copilot code-----------
# from transformers import TrOCRProcessor, VisionEncoderDecoderModel
# from PIL import Image
# import requests

# # Load image (can be local or from a URL)
# url = "https://fki.tic.heia-fr.ch/static/img/a01-122-02.jpg"
# image = Image.open(requests.get(url, stream=True).raw).convert("RGB")

# # Load processor and model
# processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
# model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")

# # Preprocess image
# pixel_values = processor(images=image, return_tensors="pt").pixel_values

# # Generate text
# generated_ids = model.generate(pixel_values)
# generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

# print("Extracted Text:", generated_text)

