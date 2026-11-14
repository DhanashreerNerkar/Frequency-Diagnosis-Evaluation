from pydantic import BaseModel, Field
from typing import List, Optional


class LookupCreateSchema(BaseModel):
    icd11_code: str = Field(..., description="ICD-11 code")
    standard_diagnoses: List[str] = Field(..., description="Official ICD names")
    source: str = Field(..., description="WHO/NIH/etc")
    created_timestamp: str = Field(..., description="ISO 8601 timestamp")

class LookupQuerySchema(BaseModel):
    icd11_code: Optional[str] = None
    status: Optional[str] = None      # new, cleared, wrong
    page: int = 1
    limit: int = 100
    updated_after: Optional[str] = None

class SynonymAddSchema(BaseModel):
    synonymous_diagnosis: str
    status: str               # "new"
    added_timestamp: str      # ISO 8601

class SynonymStatusUpdate(BaseModel):
    status: str               # cleared / wrong
    reviewed_by: str

class DoctorReviewItem(BaseModel):
    """Item for doctor review with standardized diagnosis"""
    synonym_id: int
    icd11_code: str
    synonym_text: str
    who_code: str = Field(..., description="WHO ICD-11 code")
    who_diagnosis: str = Field(..., description="WHO standardized diagnosis")
    nih_code: str = Field(..., description="NIH ICD-11 code")
    nih_diagnosis: str = Field(..., description="NIH standardized diagnosis")
    source: str = Field(default="cache", description="Source of the synonym")

class DoctorReviewRequest(BaseModel):
    """Request to review and confirm/reject a single synonym"""
    icd11_code: str
    synonym_id: int
    action: str = Field(..., description="'correct' or 'wrong'")
    reviewed_by: str = Field(..., description="Doctor/Reviewer identifier")
    notes: Optional[str] = Field(None, description="Optional notes from doctor")

class BatchReviewItem(BaseModel):
    """Single item in a batch review request"""
    icd11_code: str
    synonym_id: int
    action: str = Field(..., description="'correct' or 'wrong'")

class DoctorBatchReviewRequest(BaseModel):
    """Request to review multiple synonyms at once"""
    items: List[BatchReviewItem] = Field(..., description="List of review items")
    reviewed_by: str = Field(..., description="Doctor/Reviewer identifier")
    notes: Optional[str] = Field(None, description="Optional notes for all reviews")