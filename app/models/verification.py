from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class VerificationStatus(str, Enum):
    genuine = "genuine"
    suspicious = "suspicious"
    fake = "fake"
    unknown = "unknown"


class BatchVerifyRequest(BaseModel):
    medicine_name: str
    batch_number: str
    expiry_date: str                    # MM/YYYY
    manufacturer: Optional[str] = None  # optional extra check


class VerificationResult(BaseModel):
    status: VerificationStatus
    risk_score: float                   # 0.0 (safe) → 1.0 (fake)
    medicine_id: Optional[str] = None
    medicine_name: Optional[str] = None
    manufacturer: Optional[str] = None
    composition: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    approved_packaging: Optional[str] = None
    flags: List[str] = []               # detected anomalies
    ocr_text: Optional[str] = None
    message: str = ""


class ReportCreate(BaseModel):
    medicine_id: Optional[str] = None
    batch_number: Optional[str] = None
    description: str
    location: Optional[str] = None
    reporter_uid: Optional[str] = None


class ReportOut(ReportCreate):
    id: str
    created_at: str
    status: str = "pending"
