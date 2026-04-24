"""
Reports router — users can report suspicious medicines.
"""
from fastapi import APIRouter, HTTPException, Depends
from app.models.verification import ReportCreate, ReportOut
from app.services.firebase import get_db
from app.dependencies import get_current_user, require_admin
from datetime import datetime
import uuid

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/", response_model=ReportOut, status_code=201)
async def submit_report(
    data: ReportCreate,
    current_user: dict = Depends(get_current_user)
):
    """Submit a suspicious medicine report."""
    db = get_db()
    rid = str(uuid.uuid4())
    doc = {
        "id": rid,
        "reporter_uid": current_user["uid"],
        "medicine_id": data.medicine_id,
        "barcode": data.barcode,
        "description": data.description,
        "location": data.location,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    db.collection("reports").document(rid).set(doc)
    return ReportOut(**doc)


@router.get("/", response_model=list[ReportOut])
async def list_reports(_: dict = Depends(require_admin)):
    """List all reports (admin only)."""
    db = get_db()
    docs = db.collection("reports").order_by("created_at", direction="DESCENDING").stream()
    return [ReportOut(**d.to_dict()) for d in docs]


@router.patch("/{report_id}/status")
async def update_report_status(
    report_id: str,
    new_status: str,
    _: dict = Depends(require_admin)
):
    """Update report status: pending → reviewed / resolved (admin only)."""
    valid_statuses = {"pending", "reviewed", "resolved", "dismissed"}
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")

    db = get_db()
    ref = db.collection("reports").document(report_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Report not found.")

    ref.update({"status": new_status})
    return {"message": f"Report status updated to '{new_status}'."}
