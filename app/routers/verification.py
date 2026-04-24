"""
Verification router — the core feature.
Supports:
  - POST /verify/barcode   : verify by barcode string
  - POST /verify/image     : upload image, run OCR + barcode scan, return risk score
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional
from app.models.verification import VerificationResult, VerificationStatus
from app.services.firebase import get_db
from app.services.ocr import extract_text_from_image, parse_medicine_fields
from app.services.barcode import decode_barcode_from_bytes
from app.services.risk_engine import calculate_risk_score, score_to_status
from app.dependencies import get_current_user
from datetime import datetime
import uuid

router = APIRouter(prefix="/verify", tags=["Verification"])

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


def _lookup_by_barcode(db, barcode: str) -> Optional[dict]:
    """Query Firestore for a medicine matching the barcode."""
    docs = db.collection("medicines").where("barcode", "==", barcode).get()
    return docs[0].to_dict() if docs else None


def _save_verification_history(db, result: dict, user_uid: str):
    """Persist verification event to Firestore for audit trail."""
    vid = str(uuid.uuid4())
    db.collection("verification_history").document(vid).set({
        "id": vid,
        "user_uid": user_uid,
        "timestamp": datetime.utcnow().isoformat(),
        **result,
    })


@router.post("/barcode", response_model=VerificationResult)
async def verify_by_barcode(
    barcode: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Verify a medicine by its barcode/QR code string value.
    The client decodes the barcode on-device and sends the string here.
    """
    db = get_db()
    db_medicine = _lookup_by_barcode(db, barcode)

    # No OCR fields when only barcode is provided
    ocr_fields = {}
    ocr_text = ""

    risk_score, flags = calculate_risk_score(db_medicine, ocr_fields, barcode, ocr_text)
    status = score_to_status(risk_score)

    result = VerificationResult(
        status=VerificationStatus(status),
        risk_score=risk_score,
        medicine_id=db_medicine.get("id") if db_medicine else None,
        medicine_name=db_medicine.get("name") if db_medicine else None,
        manufacturer=db_medicine.get("manufacturer") if db_medicine else None,
        batch_number=db_medicine.get("batch_number") if db_medicine else None,
        expiry_date=db_medicine.get("expiry_date") if db_medicine else None,
        flags=flags,
        barcode_value=barcode,
        message=_status_message(status),
    )

    _save_verification_history(db, result.model_dump(), current_user["uid"])
    return result


@router.post("/image", response_model=VerificationResult)
async def verify_by_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a medicine strip image.
    Pipeline: barcode scan → OCR text extraction → DB lookup → risk scoring.
    """
    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPEG/PNG/WEBP images accepted.")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image too large (max 10MB).")

    db = get_db()

    # Step 1: Try barcode/QR scan
    barcodes = decode_barcode_from_bytes(image_bytes)
    barcode_value = barcodes[0] if barcodes else None

    # Step 2: OCR text extraction
    ocr_text = extract_text_from_image(image_bytes)
    ocr_fields = parse_medicine_fields(ocr_text)

    # Step 3: DB lookup — prefer barcode, fall back to batch number
    db_medicine = None
    if barcode_value:
        db_medicine = _lookup_by_barcode(db, barcode_value)

    if db_medicine is None and ocr_fields.get("batch_number"):
        docs = db.collection("medicines").where(
            "batch_number", "==", ocr_fields["batch_number"]
        ).get()
        db_medicine = docs[0].to_dict() if docs else None

    # Step 4: Risk scoring
    risk_score, flags = calculate_risk_score(db_medicine, ocr_fields, barcode_value, ocr_text)
    status = score_to_status(risk_score)

    result = VerificationResult(
        status=VerificationStatus(status),
        risk_score=risk_score,
        medicine_id=db_medicine.get("id") if db_medicine else None,
        medicine_name=db_medicine.get("name") if db_medicine else None,
        manufacturer=db_medicine.get("manufacturer") if db_medicine else None,
        batch_number=ocr_fields.get("batch_number") or (db_medicine.get("batch_number") if db_medicine else None),
        expiry_date=ocr_fields.get("expiry_date") or (db_medicine.get("expiry_date") if db_medicine else None),
        flags=flags,
        ocr_text=ocr_text,
        barcode_value=barcode_value,
        message=_status_message(status),
    )

    _save_verification_history(db, result.model_dump(), current_user["uid"])
    return result


def _status_message(status: str) -> str:
    messages = {
        "genuine": "This medicine appears to be genuine.",
        "suspicious": "This medicine has suspicious characteristics. Verify with a pharmacist.",
        "fake": "WARNING: This medicine is likely counterfeit. Do not consume.",
        "unknown": "Could not determine medicine authenticity.",
    }
    return messages.get(status, "")
