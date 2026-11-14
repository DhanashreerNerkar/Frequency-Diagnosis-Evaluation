from pydantic import BaseModel, Field
from typing import List, Optional, Any

class LookupEntryResponse(BaseModel):
    icd11_code: str
    standard_diagnoses: List[str]
    synonyms: List[Any]
    status: Optional[str]
    created_timestamp: Optional[str]
    updated_timestamp: Optional[str]

class DoctorReviewItemResponse(BaseModel):
    synonym_id: int
    icd11_code: str
    synonym_text: str
    who_code: str
    who_diagnosis: str
    nih_code: str
    nih_diagnosis: str
    source: str
    added_timestamp: Optional[str] = None

class PaginatedDoctorReviewResponse(BaseModel):
    items: List[DoctorReviewItemResponse]
    page: int
    limit: int
    total: int
    total_pages: int

class MessageResponse(BaseModel):
    message: str
