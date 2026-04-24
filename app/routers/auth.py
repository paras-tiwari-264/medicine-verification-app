"""
Auth router — signup, login.
Uses bcrypt directly (not via passlib) to avoid the passlib>=1.7.4
+ bcrypt>=4.x incompatibility that throws:
  "password cannot be longer than 72 bytes"
even for short passwords.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from jose import jwt
import bcrypt
from app.models.user import UserCreate, UserLogin, UserOut, TokenResponse
from app.services.firebase import get_db
from app.config import get_settings
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Password helpers using bcrypt directly ────────────────────

def hash_password(password: str) -> str:
    """Hash password with bcrypt. Encodes to UTF-8 and truncates to 72 bytes."""
    password_bytes = password.strip().encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    plain_bytes = plain.strip().encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


# ── JWT ───────────────────────────────────────────────────────

def create_access_token(uid: str, role: str) -> str:
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": uid, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


# ── Routes ────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(data: UserCreate):
    # Validate password length before hashing
    password = data.password.strip()
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password too long (max 72 characters).")

    db = get_db()
    try:
        # Check duplicate email
        existing = db.collection("users").where("email", "==", data.email).get()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered.")

        uid = str(uuid.uuid4())
        user_doc = {
            "uid": uid,
            "email": data.email,
            "full_name": data.full_name.strip(),
            "role": data.role.value,
            "hashed_password": hash_password(password),
            "created_at": datetime.utcnow().isoformat(),
        }
        db.collection("users").document(uid).set(user_doc)

        token = create_access_token(uid, data.role.value)
        return TokenResponse(
            access_token=token,
            user=UserOut(uid=uid, email=data.email,
                         full_name=data.full_name, role=data.role)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Signup error")
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    db = get_db()
    try:
        docs = db.collection("users").where("email", "==", data.email).get()
        if not docs:
            raise HTTPException(status_code=401, detail="Invalid credentials.")

        user = docs[0].to_dict()
        if not verify_password(data.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials.")

        token = create_access_token(user["uid"], user["role"])
        return TokenResponse(
            access_token=token,
            user=UserOut(
                uid=user["uid"], email=user["email"],
                full_name=user["full_name"], role=user["role"]
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login error")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
