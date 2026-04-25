"""
Admin router — dashboard stats, user management, verification history.
All routes require admin role JWT.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from app.services.firebase import get_db
from app.dependencies import require_admin
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
async def get_dashboard_stats(_: dict = Depends(require_admin)):
    """Aggregate counts for the admin dashboard."""
    db = get_db()

    def count(col: str) -> int:
        return len(list(db.collection(col).stream()))

    pending = len(db.collection("reports").where("status", "==", "pending").get())
    pharmacies = count("pharmacies")

    return {
        "total_medicines":     count("medicines"),
        "total_users":         count("users"),
        "total_verifications": count("verification_history"),
        "total_reports":       count("reports"),
        "pending_reports":     pending,
        "total_pharmacies":    pharmacies,
    }


@router.get("/users")
async def list_users(_: dict = Depends(require_admin)):
    """List all registered users — password hashes stripped."""
    db = get_db()
    users = []
    for d in db.collection("users").stream():
        u = d.to_dict()
        u.pop("hashed_password", None)
        users.append(u)
    return users


@router.delete("/users/{uid}", status_code=204)
async def delete_user(uid: str, current_admin: dict = Depends(require_admin)):
    """Delete a user account. Admins cannot delete themselves."""
    if uid == current_admin["uid"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
    db = get_db()
    ref = db.collection("users").document(uid)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="User not found.")
    ref.delete()


@router.get("/verifications")
async def list_verification_history(
    limit: int = Query(default=50, le=200),
    _: dict = Depends(require_admin)
):
    """Recent verification history, newest first."""
    db = get_db()
    docs = (
        db.collection("verification_history")
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    return [d.to_dict() for d in docs]
