# text = "निर्वाचक का नाम : कुँती कुमारी"
# print (text.find("निर्वाचक का नाम :"))

# if "An" in text[:5]:

#     print("yes")
# else:
#     print ("no")


# #code to extract into Excel sheet
import pandas as pd
import re

# 1. Sample multiple blocks of text (you can replace this with dynamic OCR output)
blocks = [
    """
    निर्वाचक का नाम : कुँती कुमारी 
    पति का नाम: चंदन कुमार चौपाल
    मकान संख्या : 0 फोटो उपलब्ध
    उम्र : 24 लिंग: : महिला
    """,
    """
    निर्वाचक का नाम : रवीना देवी झाह
    पति का नाम: दीपेश साह
    मकान संख्या : 0 फोटों उपलब्ध
    उम्र : 30 लिंग: : महिला
    """,
    """
    निर्वाचक का नाम : श्रावण कुमार यादव
    पिता का नामः: दाणी यादव
    मकान संख्या : 0 फोटो उपलब्ध
    उम्र : 27 लिंग: : पुरुष
    """
]

# 2. Define regex patterns for all potential fields
patterns = {
    'निर्वाचक का नाम': r'निर्वाचक का नाम\s*[:：]\s*(.*)',
    'पति का नाम': r'पति का नाम\s*[:：]\s*(.*)',
    'पिता का नाम': r'पिता का नाम\s*[:：]\s*(.*)',
    'मकान संख्या': r'मकान संख्या\s*[:：]\s*(.*)',
    'उम्र': r'उम्र\s*[:：]\s*(\d+)',
    'लिंग': r'लिंग\s*[:：]\s*(\w+)',
}

# 3. Loop over each block and extract data
extracted_data = []

for block in blocks:
    row = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, block)
        row[key] = match.group(1).strip() if match else ''
    extracted_data.append(row)

# 4. Convert to DataFrame and write to Excel
df = pd.DataFrame(extracted_data)
df.to_excel("multiple_voter_blocks.xlsx", index=False, engine='openpyxl')

print("✅ All blocks processed and saved to 'multiple_voter_blocks.xlsx'")