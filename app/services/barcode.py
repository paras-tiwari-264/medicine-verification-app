"""
Barcode / QR code scanning service.

Strategy (Windows-friendly):
  1. Try OpenCV QRCodeDetector (built-in, no extra DLLs needed)
  2. Try OpenCV WeChatQRCode (better accuracy for QR)
  3. Try pyzbar if available (best for 1D barcodes like EAN-13)
     — pyzbar requires ZBar DLLs on Windows; we import it lazily
       so the app still starts even if the DLLs are missing.
"""
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


def decode_barcode_from_bytes(image_bytes: bytes) -> list[str]:
    """
    Decode all barcodes/QR codes found in an image.
    Returns a list of decoded string values.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image for barcode scanning.")

    results = []

    # --- 1. OpenCV built-in QR detector ---
    results += _opencv_qr(img)

    # --- 2. Try grayscale if nothing found yet ---
    if not results:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        results += _opencv_qr(gray)

    # --- 3. pyzbar for 1D barcodes (EAN, UPC, Code128, etc.) ---
    if not results:
        results += _pyzbar_scan(img)

    return results


def _opencv_qr(img: np.ndarray) -> list[str]:
    """Use OpenCV's QRCodeDetector — works for QR codes, no DLLs needed."""
    found = []
    try:
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)
        if data:
            found.append(data)
            logger.info(f"OpenCV QR decoded: {data}")
    except Exception as e:
        logger.debug(f"OpenCV QR scan failed: {e}")
    return found


def _pyzbar_scan(img: np.ndarray) -> list[str]:
    """
    Try pyzbar for 1D barcodes.
    Imported lazily — if ZBar DLLs are missing on Windows,
    we log a warning and return empty instead of crashing.
    """
    try:
        from pyzbar import pyzbar
        decoded = pyzbar.decode(img)
        results = []
        for obj in decoded:
            try:
                value = obj.data.decode("utf-8")
                results.append(value)
                logger.info(f"pyzbar decoded: type={obj.type}, value={value}")
            except Exception:
                pass
        return results
    except (ImportError, OSError) as e:
        # ZBar DLLs not installed — non-fatal, QR still works via OpenCV
        logger.warning(
            f"pyzbar unavailable (ZBar DLLs missing on Windows?): {e}. "
            "QR codes still work via OpenCV. For 1D barcode support, "
            "see README for ZBar DLL installation."
        )
        return []
