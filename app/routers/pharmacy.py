"""
Pharmacy router — pharmacy-specific endpoints.
Pharmacies can register themselves and look up medicines.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.services.firebase import get_db
from app.dependencies import get_current_user, require_pharmacy, require_admin
from datetime import datetime
import uuid

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])


class PharmacyCreate(BaseModel):
    name: str
    license_number: str
    address: str
    contact_email: str
    contact_phone: Optional[str] = None


class PharmacyOut(PharmacyCreate):
    id: str
    owner_uid: str
    is_verified: bool = False
    created_at: str


@router.post("/register", response_model=PharmacyOut, status_code=201)
async def register_pharmacy(
    data: PharmacyCreate,
    current_user: dict = Depends(get_current_user)
):
    """Register a pharmacy (any authenticated user can apply)."""
    db = get_db()

    # Check duplicate license
    existing = db.collection("pharmacies").where(
        "license_number", "==", data.license_number
    ).get()
    if existing:
        raise HTTPException(status_code=400, detail="License number already registered.")

    pid = str(uuid.uuid4())
    doc = {
        "id": pid,
        "owner_uid": current_user["uid"],
        "is_verified": False,
        "created_at": datetime.utcnow().isoformat(),
        **data.model_dump(),
    }
    db.collection("pharmacies").document(pid).set(doc)
    return PharmacyOut(**doc)


@router.get("/", response_model=list[PharmacyOut])
async def list_pharmacies(_: dict = Depends(require_admin)):
    """List all pharmacies (admin only)."""
    db = get_db()
    docs = db.collection("pharmacies").stream()
    return [PharmacyOut(**d.to_dict()) for d in docs]


@router.patch("/{pharmacy_id}/verify")
async def verify_pharmacy(
    pharmacy_id: str,
    _: dict = Depends(require_admin)
):
    """Mark a pharmacy as verified (admin only)."""
    db = get_db()
    ref = db.collection("pharmacies").document(pharmacy_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Pharmacy not found.")
    ref.update({"is_verified": True})
    return {"message": "Pharmacy verified successfully."}


@router.get("/my", response_model=list[PharmacyOut])
async def my_pharmacies(current_user: dict = Depends(get_current_user)):
    """Get pharmacies owned by the current user."""
    db = get_db()
    docs = db.collection("pharmacies").where(
        "owner_uid", "==", current_user["uid"]
    ).get()
    return [PharmacyOut(**d.to_dict()) for d in docs]
