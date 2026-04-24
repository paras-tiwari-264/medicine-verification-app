"""
Risk scoring engine — assigns a fake medicine risk score (0.0 to 1.0)
based on anomaly detection heuristics and database match results.

0.0 - 0.3  → genuine
0.3 - 0.6  → suspicious
0.6 - 1.0  → likely fake
"""
from datetime import datetime
from typing import Optional
import re
import logging

logger = logging.getLogger(__name__)


def calculate_risk_score(
    db_medicine: Optional[dict],
    ocr_fields: dict,
    barcode_value: Optional[str],
    ocr_text: str
) -> tuple[float, list[str]]:
    """
    Returns (risk_score, flags).
    flags = list of human-readable anomaly descriptions.
    """
    score = 0.0
    flags = []

    # --- 1. No database match ---
    if db_medicine is None:
        score += 0.4
        flags.append("Medicine not found in verified database.")

    else:
        # --- 2. Batch number mismatch ---
        ocr_batch = ocr_fields.get("batch_number", "").upper().strip()
        db_batch = db_medicine.get("batch_number", "").upper().strip()
        if ocr_batch and db_batch and ocr_batch != db_batch:
            score += 0.25
            flags.append(f"Batch number mismatch: scanned '{ocr_batch}' vs registered '{db_batch}'.")

        # --- 3. Manufacturer mismatch ---
        ocr_mfr = ocr_fields.get("manufacturer", "").lower().strip()
        db_mfr = db_medicine.get("manufacturer", "").lower().strip()
        if ocr_mfr and db_mfr and ocr_mfr not in db_mfr and db_mfr not in ocr_mfr:
            score += 0.2
            flags.append(f"Manufacturer mismatch: scanned '{ocr_mfr}' vs registered '{db_mfr}'.")

        # --- 4. Expiry date check ---
        exp_str = ocr_fields.get("expiry_date") or db_medicine.get("expiry_date", "")
        if exp_str:
            expired, msg = _check_expiry(exp_str)
            if expired:
                score += 0.15
                flags.append(msg)

        # --- 5. Medicine not approved ---
        if not db_medicine.get("is_approved", True):
            score += 0.3
            flags.append("Medicine is marked as NOT approved in the database.")

    # --- 6. OCR quality check — very short text is suspicious ---
    if len(ocr_text.strip()) < 20:
        score += 0.1
        flags.append("Very little text extracted from image — packaging may be tampered.")

    # --- 7. Suspicious keywords in OCR text ---
    suspicious_keywords = ["replica", "copy", "imitation", "not for sale", "sample only"]
    for kw in suspicious_keywords:
        if kw in ocr_text.lower():
            score += 0.2
            flags.append(f"Suspicious keyword detected in label: '{kw}'.")

    # Clamp to [0.0, 1.0]
    score = min(round(score, 2), 1.0)
    return score, flags


def score_to_status(score: float) -> str:
    if score < 0.3:
        return "genuine"
    elif score < 0.6:
        return "suspicious"
    else:
        return "fake"


def _check_expiry(exp_str: str) -> tuple[bool, str]:
    """Parse MM/YYYY or MM/YY and check if expired."""
    try:
        # Normalize separators
        exp_str = exp_str.replace("-", "/")
        parts = exp_str.split("/")
        if len(parts) == 2:
            month = int(parts[0])
            year = int(parts[1])
            if year < 100:
                year += 2000
            exp_date = datetime(year, month, 1)
            if exp_date < datetime.now():
                return True, f"Medicine expired: {exp_str}."
    except Exception as e:
        logger.warning(f"Could not parse expiry date '{exp_str}': {e}")
    return False, ""
