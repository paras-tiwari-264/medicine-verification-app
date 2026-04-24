from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class VerificationStatus(str, Enum):
    genuine = "genuine"
    suspicious = "suspicious"
    fake = "fake"
    unknown = "unknown"


class VerificationResult(BaseModel):
    status: VerificationStatus
    risk_score: float           # 0.0 (safe) to 1.0 (definitely fake)
    medicine_id: Optional[str] = None
    medicine_name: Optional[str] = None
    manufacturer: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    flags: List[str] = []       # list of detected anomalies
    ocr_text: Optional[str] = None
    barcode_value: Optional[str] = None
    message: str = ""


class ReportCreate(BaseModel):
    medicine_id: Optional[str] = None
    barcode: Optional[str] = None
    description: str
    location: Optional[str] = None
    reporter_uid: Optional[str] = None


class ReportOut(ReportCreate):
    id: str
    created_at: str
    status: str = "pending"
