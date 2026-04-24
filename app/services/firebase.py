"""
Firebase Firestore service — initializes the Firebase Admin SDK
and exposes a single `db` client used across the app.
"""
import firebase_admin
from firebase_admin import credentials, firestore, auth
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

_app = None


def init_firebase():
    """Initialize Firebase app (called once at startup)."""
    global _app
    settings = get_settings()
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        _app = firebase_admin.initialize_app(cred, {
            "projectId": settings.firebase_project_id
        })
        logger.info("Firebase initialized successfully.")
    return firebase_admin.get_app()


def get_db() -> firestore.Client:
    """Return Firestore client."""
    return firestore.client()


def get_auth():
    """Return Firebase Auth client."""
    return auth
