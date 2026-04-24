"""
OCR service using Tesseract to extract text from medicine strip images.
"""
import pytesseract
import re
from app.config import get_settings
from app.utils.image_processing import preprocess_for_ocr, numpy_to_pil, resize_for_ocr
import logging

logger = logging.getLogger(__name__)


def configure_tesseract():
    """Point pytesseract to the Tesseract binary from .env."""
    settings = get_settings()
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Full pipeline: preprocess image → run OCR → return raw text.
    """
    configure_tesseract()
    try:
        processed = preprocess_for_ocr(image_bytes)
        scaled = resize_for_ocr(processed)
        pil_img = numpy_to_pil(scaled)

        # PSM 6 = assume a uniform block of text (good for medicine labels)
        config = "--psm 6 --oem 3"
        text = pytesseract.image_to_string(pil_img, config=config)
        return text.strip()
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""


def parse_medicine_fields(ocr_text: str) -> dict:
    """
    Attempt to extract structured fields from raw OCR text using regex.
    Returns a dict with whatever could be found.
    """
    fields = {}

    # Batch number patterns: Batch No., B.No, Lot No.
    batch_match = re.search(
        r"(?:batch\s*(?:no\.?|number)?|b\.?\s*no\.?|lot\s*no\.?)[:\s]*([A-Z0-9\-]+)",
        ocr_text, re.IGNORECASE
    )
    if batch_match:
        fields["batch_number"] = batch_match.group(1).strip()

    # Expiry date: Exp, Expiry, EXP DATE
    exp_match = re.search(
        r"(?:exp(?:iry)?\.?\s*(?:date)?)[:\s]*(\d{2}[\/\-]\d{4}|\d{2}[\/\-]\d{2})",
        ocr_text, re.IGNORECASE
    )
    if exp_match:
        fields["expiry_date"] = exp_match.group(1).strip()

    # Manufacturer
    mfr_match = re.search(
        r"(?:mfg\.?\s*by|manufactured\s*by|mfr\.?)[:\s]*([A-Za-z\s&\.]+)",
        ocr_text, re.IGNORECASE
    )
    if mfr_match:
        fields["manufacturer"] = mfr_match.group(1).strip()[:60]

    return fields
