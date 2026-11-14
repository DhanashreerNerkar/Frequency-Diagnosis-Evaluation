from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DiagnosisProb(BaseModel):
    diagnosis: str = Field(..., min_length=1, description="Diagnosis label/name")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability in [0,1]")

class OnspotDiagnosisCreate(BaseModel):
    case_id: str = Field(..., min_length=1)
    diagnoses: List[DiagnosisProb] = Field(..., min_items=1)

class OnspotDiagnosisDB(OnspotDiagnosisCreate):
    id: Optional[str] = Field(None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
