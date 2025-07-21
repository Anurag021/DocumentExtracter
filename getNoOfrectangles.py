import cv2

# Load the image
image_path = "/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/ImageFIle.jpg"  # path to your uploaded image
output_file = '/Users/anuragrawat/Documents/GitHub/FreeLance/SampleFiles/extracted_text.txt'
img = cv2.imread(image_path)

# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Apply binary thresholding with inversion
_, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Morphological operations to highlight rectangular blocks
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 10))  # Adjust based on block size
dilated = cv2.dilate(thresh, kernel, iterations=1)

# Find contours
contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Filter valid rectangles by size
block_count = 0
min_width, min_height = 100, 50  # Filter out small noise

for cnt in contours:
    x, y, w, h = cv2.boundingRect(cnt)
    if w > min_width and h > min_height:
        block_count += 1
        # Optional: Draw rectangles for visualization
        # cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)

print(f"🧮 Total rectangle blocks detected: {block_count}")