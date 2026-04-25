"""
Medicine Verification API — main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.services.firebase import init_firebase
from app.routers import auth, medicines, verification, reports, admin, pharmacy
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Firebase on startup."""
    logger.info("Starting Medicine Verify API...")
    init_firebase()
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Medicine Verification API",
    description=(
        "Verify medicine authenticity via barcode scanning and OCR image analysis. "
        "Detects genuine, suspicious, and fake medicines using risk scoring."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — adjust origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(auth.router)
app.include_router(medicines.router)
app.include_router(verification.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(pharmacy.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Medicine Verification API is running."}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


# Serve the frontend UI
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/ui", tags=["UI"])
async def serve_ui():
    return FileResponse("static/index.html")


@app.get("/admin", tags=["UI"])
async def serve_admin():
    return FileResponse("static/admin.html")
