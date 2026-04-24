"""
Medicine CRUD — add, list, get, update medicines in Firestore.
Admin-only for write operations.
"""
from fastapi import APIRouter, HTTPException, Depends
from app.models.medicine import MedicineCreate, MedicineOut, MedicineUpdate
from app.services.firebase import get_db
from app.dependencies import get_current_user, require_admin
from datetime import datetime
import uuid

router = APIRouter(prefix="/medicines", tags=["Medicines"])


@router.post("/", response_model=MedicineOut, status_code=201)
async def add_medicine(
    data: MedicineCreate,
    _: dict = Depends(require_admin)
):
    """Add a verified medicine to the database (admin only)."""
    db = get_db()
    mid = str(uuid.uuid4())
    doc = {
        "id": mid,
        **data.model_dump(),
        "is_approved": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    db.collection("medicines").document(mid).set(doc)
    return MedicineOut(**doc)


@router.get("/", response_model=list[MedicineOut])
async def list_medicines(_: dict = Depends(get_current_user)):
    """List all medicines in the database."""
    db = get_db()
    docs = db.collection("medicines").stream()
    return [MedicineOut(**d.to_dict()) for d in docs]


@router.get("/{medicine_id}", response_model=MedicineOut)
async def get_medicine(medicine_id: str, _: dict = Depends(get_current_user)):
    """Get a single medicine by ID."""
    db = get_db()
    doc = db.collection("medicines").document(medicine_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Medicine not found.")
    return MedicineOut(**doc.to_dict())


@router.patch("/{medicine_id}", response_model=MedicineOut)
async def update_medicine(
    medicine_id: str,
    data: MedicineUpdate,
    _: dict = Depends(require_admin)
):
    """Update medicine fields (admin only)."""
    db = get_db()
    ref = db.collection("medicines").document(medicine_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Medicine not found.")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    ref.update(updates)
    updated = ref.get().to_dict()
    return MedicineOut(**updated)


@router.delete("/{medicine_id}", status_code=204)
async def delete_medicine(medicine_id: str, _: dict = Depends(require_admin)):
    """Delete a medicine record (admin only)."""
    db = get_db()
    ref = db.collection("medicines").document(medicine_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Medicine not found.")
    ref.delete()
