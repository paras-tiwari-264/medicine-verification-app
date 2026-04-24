"""
FastAPI dependency injection — JWT token validation, role guards.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import get_settings
from app.services.firebase import get_db
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Validate JWT and return user payload."""
    payload = decode_token(token)
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Token missing subject.")

    db = get_db()
    doc = db.collection("users").document(uid).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found.")

    return {"uid": uid, **doc.to_dict()}


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Guard: only admin role allowed."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


async def require_pharmacy(current_user: dict = Depends(get_current_user)) -> dict:
    """Guard: pharmacy or admin role allowed."""
    if current_user.get("role") not in ("admin", "pharmacy"):
        raise HTTPException(status_code=403, detail="Pharmacy access required.")
    return current_user
