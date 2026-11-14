from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime

class DiagnosisSchema(BaseModel):
    diagnosis: str = Field(..., description="Diagnosis Name")
    icd11_code: str = Field(..., description="ICD-11 Code")
    probability: str = Field(..., description="Probability of Diagnosis")
    urgency: Literal["low", "medium", "high", "critical"] = Field(..., description="Urgency Level")
    rationale: str = Field(..., description="Reasoning for Diagnosis")
    treatment: List[str] = Field(..., description="Suggested Treatments")

    model_config = {
        "validate_by_name": True
    }

class UpdateDiagnosisSchema(BaseModel):
    confirmed_diagnosis: List[str]
    