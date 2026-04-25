"""
Risk scoring engine — assigns a fake medicine risk score (0.0 to 1.0).

Scoring breakdown:
  No DB match found          → +0.45
  Expiry date mismatch       → +0.25
  Manufacturer mismatch      → +0.20
  Medicine expired           → +0.15
  Medicine not approved      → +0.30
  Suspicious OCR keywords    → +0.20 each

Thresholds:
  0.00 – 0.29  → genuine
  0.30 – 0.59  → suspicious
  0.60 – 1.00  → fake
"""
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def calculate_risk_score(
    db_medicine: Optional[dict],
    input_fields: dict,         # fields submitted by user / extracted via OCR
    ocr_text: str = ""
) -> tuple[float, list[str]]:
    """
    Returns (risk_score, flags).
    input_fields keys: medicine_name, batch_number, expiry_date, manufacturer
    """
    score = 0.0
    flags = []

    # 1. No database match at all
    if db_medicine is None:
        score += 0.45
        flags.append("Medicine not found in the verified database.")
        # Still check expiry on the user-supplied date
        exp = input_fields.get("expiry_date", "")
        if exp:
            expired, msg = _check_expiry(exp)
            if expired:
                score += 0.15
                flags.append(msg)
    else:
        # 2. Expiry date mismatch between user input and DB record
        input_exp = _normalise(input_fields.get("expiry_date", ""))
        db_exp    = _normalise(db_medicine.get("expiry_date", ""))
        if input_exp and db_exp and input_exp != db_exp:
            score += 0.25
            flags.append(
                f"Expiry date mismatch: entered '{input_fields.get('expiry_date')}' "
                f"vs registered '{db_medicine.get('expiry_date')}'."
            )

        # 3. Manufacturer mismatch (if provided)
        input_mfr = input_fields.get("manufacturer", "").lower().strip()
        db_mfr    = db_medicine.get("manufacturer", "").lower().strip()
        if input_mfr and db_mfr:
            if input_mfr not in db_mfr and db_mfr not in input_mfr:
                score += 0.20
                flags.append(
                    f"Manufacturer mismatch: entered '{input_fields.get('manufacturer')}' "
                    f"vs registered '{db_medicine.get('manufacturer')}'."
                )

        # 4. Check if the DB expiry date itself is past
        if db_exp:
            expired, msg = _check_expiry(db_medicine.get("expiry_date", ""))
            if expired:
                score += 0.15
                flags.append(msg)

        # 5. Medicine explicitly marked not approved / recalled
        if not db_medicine.get("is_approved", True):
            score += 0.30
            flags.append("Medicine is marked as NOT approved in the database.")

        db_status = db_medicine.get("status", "approved").lower()
        if db_status in ("banned", "recalled"):
            score += 0.30
            flags.append(f"Medicine status in database: '{db_status.upper()}'.")

    # 6. Suspicious keywords in OCR text (image scan path)
    suspicious_keywords = ["replica", "copy", "imitation", "not for sale", "sample only"]
    for kw in suspicious_keywords:
        if kw in ocr_text.lower():
            score += 0.20
            flags.append(f"Suspicious keyword detected on label: '{kw}'.")

    return min(round(score, 2), 1.0), flags


def score_to_status(score: float) -> str:
    if score < 0.30:
        return "genuine"
    elif score < 0.60:
        return "suspicious"
    else:
        return "fake"


# ── Helpers ───────────────────────────────────────────────────

def _normalise(exp_str: str) -> str:
    """Normalise MM/YYYY or MM-YYYY to MM/YYYY for comparison."""
    return exp_str.strip().replace("-", "/")


def _check_expiry(exp_str: str) -> tuple[bool, str]:
    """Return (is_expired, message). Accepts MM/YYYY or MM-YYYY."""
    try:
        exp_str = _normalise(exp_str)
        parts = exp_str.split("/")
        if len(parts) == 2:
            month = int(parts[0])
            year  = int(parts[1])
            if year < 100:
                year += 2000
            if datetime(year, month, 1) < datetime.now():
                return True, f"Medicine has expired (expiry: {exp_str})."
    except Exception as e:
        logger.warning(f"Could not parse expiry date '{exp_str}': {e}")
    return False, ""
