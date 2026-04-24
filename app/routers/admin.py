"""
Admin router — dashboard stats, user management, verification history.
"""
from fastapi import APIRouter, HTTPException, Depends
from app.services.firebase import get_db
from app.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
async def get_dashboard_stats(_: dict = Depends(require_admin)):
    """
    Return aggregate counts for the admin dashboard:
    total medicines, users, verifications, reports.
    """
    db = get_db()

    def count_collection(name: str) -> int:
        return len(list(db.collection(name).stream()))

    return {
        "total_medicines": count_collection("medicines"),
        "total_users": count_collection("users"),
        "total_verifications": count_collection("verification_history"),
        "total_reports": count_collection("reports"),
        "pending_reports": len(
            db.collection("reports").where("status", "==", "pending").get()
        ),
    }


@router.get("/users")
async def list_users(_: dict = Depends(require_admin)):
    """List all registered users (admin only)."""
    db = get_db()
    docs = db.collection("users").stream()
    users = []
    for d in docs:
        u = d.to_dict()
        u.pop("hashed_password", None)   # never expose password hash
        users.append(u)
    return users


@router.delete("/users/{uid}", status_code=204)
async def delete_user(uid: str, _: dict = Depends(require_admin)):
    """Delete a user account (admin only)."""
    db = get_db()
    ref = db.collection("users").document(uid)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="User not found.")
    ref.delete()


@router.get("/verifications")
async def list_verification_history(
    limit: int = 50,
    _: dict = Depends(require_admin)
):
    """Get recent verification history (admin only)."""
    db = get_db()
    docs = (
        db.collection("verification_history")
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    return [d.to_dict() for d in docs]
