from pydantic import BaseModel
from typing import Optional, List


class MedicineBase(BaseModel):
    name: str
    manufacturer: str
    composition: Optional[str] = None        # active ingredients as string
    batch_number: str
    manufacturing_date: Optional[str] = None  # format: MM/YYYY
    expiry_date: str                           # format: MM/YYYY
    approved_packaging: Optional[str] = None
    dosage_form: Optional[str] = None         # tablet, syrup, capsule, etc.
    status: Optional[str] = "approved"        # approved | banned | recalled


class MedicineCreate(MedicineBase):
    pass


class MedicineOut(MedicineBase):
    id: str
    created_at: Optional[str] = None
    is_approved: bool = True


class MedicineUpdate(BaseModel):
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    composition: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    approved_packaging: Optional[str] = None
    dosage_form: Optional[str] = None
    status: Optional[str] = None
    is_approved: Optional[bool] = None
