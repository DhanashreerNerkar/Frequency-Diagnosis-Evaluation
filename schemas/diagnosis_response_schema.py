from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DiagnosisInferenceResponse(BaseModel):
    model: str = Field(..., description="Model used for diagnosis")
    condition: str = Field(..., description="Input patient condition")
    results: List[Dict[str, Any]] = Field(
        ..., description="Model-generated diagnosis results"
    )

class UpdateDiagnosisResponse(BaseModel):
    message: str
    data: Dict[str, Any]


class OnspotDiagnosisResponse(BaseModel):
    case_id: str
    diagnoses: List[Dict[str, Any]]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class OnspotDiagnosisListResponse(BaseModel):
    items: List[OnspotDiagnosisResponse]
    skip: int
    limit: int
    total: int
