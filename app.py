from fastapi import FastAPI, UploadFile, File
import fitz  # PyMuPDF
import easyocr
import io
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import numpy as np

app = FastAPI(title="High Accuracy Hindi + English PDF Text Extraction API")

# -------------------------------
# Initialize OCR readers
# -------------------------------
# EasyOCR (fast and handles Hindi + English)
easy_reader = easyocr.Reader(['en', 'hi'], gpu=False)

# Tesseract fallback for better Hindi accuracy on large pages
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # change if path differs

# -------------------------------
# Function 1: Text-based extraction
# -------------------------------
def extract_text_textbased(pdf_bytes):
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for page in pdf:
            text += page.get_text("text") + "\n\n"
    return text.strip()

# -------------------------------
# Function 2: OCR using EasyOCR (Fast)
# -------------------------------
def extract_text_easyocr(pdf_bytes):
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for i, page in enumerate(pdf):
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            results = easy_reader.readtext(img_bytes, detail=0, paragraph=True)
            page_text = " ".join(results)
            text += f"\n--- Page {i+1} (EasyOCR) ---\n{page_text}\n"
    return text.strip()

# -------------------------------
# Function 3: OCR using Tesseract (Accurate Hindi fallback)
# -------------------------------
def extract_text_tesseract(pdf_bytes):
    images = convert_from_bytes(pdf_bytes, dpi=300)
    full_text = ""
    for i, img in enumerate(images):
        img_np = np.array(img)
        text = pytesseract.image_to_string(img_np, lang="hin+eng")
        full_text += f"\n--- Page {i+1} (Tesseract) ---\n{text}\n"
    return full_text.strip()

# -------------------------------
# API Endpoint
# -------------------------------
@app.post("/extract_text")
async def extract_text(file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    try:
        # Step 1: Try text-based
        text = extract_text_textbased(pdf_bytes)
        if len(text.strip()) > 40:
            method = "Text-based (PyMuPDF)"
        else:
            # Step 2: Try EasyOCR (fast)
            text = extract_text_easyocr(pdf_bytes)
            if len(text.strip()) < 40:
                # Step 3: Fallback to Tesseract (accurate Hindi)
                text = extract_text_tesseract(pdf_bytes)
                method = "OCR (Tesseract - High Accuracy)"
            else:
                method = "OCR (EasyOCR - Fast)"
        return {
            "status": "success",
            "method_used": method,
            "text": text[:10000]  # return first 10k chars
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
