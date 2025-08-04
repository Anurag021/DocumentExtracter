#Initial code
from PIL import Image

image_path = "/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/ImageFIle.jpg" 
# Load image
image = Image.open(image_path)

# Define crop box: (left, upper, right, lower)
crop_box = (56, 110, 2425, 3410)

# Crop
cropped_image = image.crop(crop_box)

# Save or show
cropped_image.save("cropped_image1.jpg")
cropped_image.show()



#--------------------------------#
#def Cropped Pages
#modified to work with all pdf pages

from PIL import Image
from pdf2image import convert_from_path
import os

# === CONFIGURATION ===

def pdfCropping(pdf_path, output_folder, crop_box=(56, 110, 2425, 3410), dpi=300):

    pdf_path = "/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/InputFile.pdf"
    output_folder = "/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/CroppedPages"
    #crop_box = (56, 110, 2425, 3410)  # (left, upper, right, lower)

    # Create output directory if not exists
    os.makedirs(output_folder, exist_ok=True)

    # Convert PDF pages to images
    pages = convert_from_path(pdf_path, dpi=300)  # Increase dpi if resolution is low

    # Loop through each page
    for i, page in enumerate(pages):
        cropped = page.crop(crop_box)
        output_path = os.path.join(output_folder, f"cropped_page_{i + 1}.jpg")
        cropped.save(output_path)
        print(f"✅ Saved: {output_path}")

    print("✅ All pages cropped and saved.")