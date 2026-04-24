from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MedicineBase(BaseModel):
    name: str
    manufacturer: str
    batch_number: str
    expiry_date: str          # format: MM/YYYY
    barcode: str
    approved_packaging: Optional[str] = None
    active_ingredients: Optional[List[str]] = []
    dosage_form: Optional[str] = None   # tablet, syrup, etc.


class MedicineCreate(MedicineBase):
    pass


class MedicineOut(MedicineBase):
    id: str
    created_at: Optional[str] = None
    is_approved: bool = True


class MedicineUpdate(BaseModel):
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    approved_packaging: Optional[str] = None
    is_approved: Optional[bool] = None
