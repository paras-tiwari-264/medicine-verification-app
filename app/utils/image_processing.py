"""
OpenCV-based image preprocessing to improve OCR accuracy.
"""
import cv2
import numpy as np
from PIL import Image
import io


def preprocess_for_ocr(image_bytes: bytes) -> np.ndarray:
    """
    Convert raw image bytes → grayscale + denoised + thresholded image
    ready for Tesseract OCR.
    """
    # Decode bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image.")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Adaptive threshold — handles uneven lighting on medicine strips
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # Slight sharpening kernel
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(thresh, -1, kernel)

    return sharpened


def numpy_to_pil(img: np.ndarray) -> Image.Image:
    """Convert OpenCV numpy array to PIL Image for Tesseract."""
    return Image.fromarray(img)


def resize_for_ocr(img: np.ndarray, scale: float = 2.0) -> np.ndarray:
    """Upscale small images so Tesseract reads them better."""
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * scale), int(h * scale)),
                      interpolation=cv2.INTER_CUBIC)
