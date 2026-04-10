import fitz  # PyMuPDF
import sys
import os

files = [
    "PBL_PPT Sapmle Template.pdf",
    "PBL_REVIEW-01-fnl (1).pdf",
    "PBL_Sample Report.pdf"
]

for file in files:
    try:
        doc = fitz.open(file)
        text = f"# Extracted from {file}\n\n"
        for i, page in enumerate(doc):
            text += f"## Page {i+1}\n\n{page.get_text()}\n\n"
        
        out_name = file.replace('.pdf', '_extracted.txt')
        with open(out_name, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Extracted {file} to {out_name}")
    except Exception as e:
        print(f"Error extracting {file}: {e}")
