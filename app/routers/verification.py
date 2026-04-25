"""
Verification router — core feature.

Endpoints:
  POST /verify/batch  — verify by medicine name + batch number + expiry date
  POST /verify/image  — upload image, run OCR, auto-extract fields, then verify
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Optional
from app.models.verification import (
    BatchVerifyRequest, VerificationResult, VerificationStatus
)
from app.services.firebase import get_db
from app.services.ocr import extract_text_from_image, parse_medicine_fields
from app.services.risk_engine import calculate_risk_score, score_to_status
from app.dependencies import get_current_user
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/verify", tags=["Verification"])

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


# ── DB lookup helpers ─────────────────────────────────────────

def _lookup_by_batch(db, batch_number: str) -> Optional[dict]:
    """Primary lookup: exact batch number match."""
    docs = db.collection("medicines").where(
        "batch_number", "==", batch_number.strip().upper()
    ).get()
    return docs[0].to_dict() if docs else None


def _lookup_by_name_and_batch(db, name: str, batch_number: str) -> Optional[dict]:
    """Stricter lookup: name + batch number."""
    docs = db.collection("medicines") \
        .where("batch_number", "==", batch_number.strip().upper()) \
        .get()
    # Filter by name client-side (Firestore free tier has limited compound queries)
    name_lower = name.strip().lower()
    for d in docs:
        rec = d.to_dict()
        if name_lower in rec.get("name", "").lower():
            return rec
    return None


def _save_history(db, result: dict, user_uid: str):
    """Persist verification event for audit trail."""
    vid = str(uuid.uuid4())
    db.collection("verification_history").document(vid).set({
        "id": vid,
        "user_uid": user_uid,
        "timestamp": datetime.utcnow().isoformat(),
        **result,
    })


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/batch", response_model=VerificationResult,
             summary="Verify medicine by batch number")
async def verify_by_batch(
    data: BatchVerifyRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify a medicine using:
    - medicine_name  (required)
    - batch_number   (required)
    - expiry_date    (required, MM/YYYY)
    - manufacturer   (optional — adds extra confidence check)

    Returns genuine / suspicious / fake with a risk score and flags.
    """
    db = get_db()

    # Normalise batch number to uppercase for consistent matching
    batch = data.batch_number.strip().upper()

    # Try name+batch first, fall back to batch-only
    db_medicine = _lookup_by_name_and_batch(db, data.medicine_name, batch)
    if db_medicine is None:
        db_medicine = _lookup_by_batch(db, batch)

    input_fields = {
        "medicine_name": data.medicine_name.strip(),
        "batch_number":  batch,
        "expiry_date":   data.expiry_date.strip(),
        "manufacturer":  (data.manufacturer or "").strip(),
    }

    risk_score, flags = calculate_risk_score(db_medicine, input_fields)
    status = score_to_status(risk_score)

    result = VerificationResult(
        status=VerificationStatus(status),
        risk_score=risk_score,
        medicine_id=db_medicine.get("id") if db_medicine else None,
        medicine_name=db_medicine.get("name") if db_medicine else data.medicine_name,
        manufacturer=db_medicine.get("manufacturer") if db_medicine else data.manufacturer,
        composition=db_medicine.get("composition") if db_medicine else None,
        batch_number=batch,
        manufacturing_date=db_medicine.get("manufacturing_date") if db_medicine else None,
        expiry_date=db_medicine.get("expiry_date") if db_medicine else data.expiry_date,
        approved_packaging=db_medicine.get("approved_packaging") if db_medicine else None,
        flags=flags,
        message=_status_message(status),
    )

    _save_history(db, result.model_dump(), current_user["uid"])
    return result


@router.post("/image", response_model=VerificationResult,
             summary="Verify medicine by uploading a strip image")
async def verify_by_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a medicine strip image (JPEG/PNG/WEBP).
    Pipeline: OCR text extraction → field parsing → DB lookup → risk scoring.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPEG/PNG/WEBP images accepted.")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image too large (max 10MB).")

    db = get_db()

    # Step 1: OCR
    ocr_text = extract_text_from_image(image_bytes)
    ocr_fields = parse_medicine_fields(ocr_text)
    logger.info(f"OCR extracted fields: {ocr_fields}")

    # Step 2: DB lookup using extracted batch number
    db_medicine = None
    batch = (ocr_fields.get("batch_number") or "").strip().upper()
    if batch:
        db_medicine = _lookup_by_batch(db, batch)

    # Step 3: Risk scoring
    risk_score, flags = calculate_risk_score(db_medicine, ocr_fields, ocr_text)
    status = score_to_status(risk_score)

    result = VerificationResult(
        status=VerificationStatus(status),
        risk_score=risk_score,
        medicine_id=db_medicine.get("id") if db_medicine else None,
        medicine_name=db_medicine.get("name") if db_medicine else None,
        manufacturer=db_medicine.get("manufacturer") if db_medicine else ocr_fields.get("manufacturer"),
        composition=db_medicine.get("composition") if db_medicine else None,
        batch_number=batch or None,
        manufacturing_date=db_medicine.get("manufacturing_date") if db_medicine else None,
        expiry_date=ocr_fields.get("expiry_date") or (db_medicine.get("expiry_date") if db_medicine else None),
        approved_packaging=db_medicine.get("approved_packaging") if db_medicine else None,
        flags=flags,
        ocr_text=ocr_text,
        message=_status_message(status),
    )

    _save_history(db, result.model_dump(), current_user["uid"])
    return result


def _status_message(status: str) -> str:
    return {
        "genuine":    "✓ This medicine is verified as genuine.",
        "suspicious": "⚠ This medicine has suspicious characteristics. Please verify with a licensed pharmacist.",
        "fake":       "✗ WARNING: This medicine is likely counterfeit. Do not consume it.",
        "unknown":    "Could not determine medicine authenticity.",
    }.get(status, "")
