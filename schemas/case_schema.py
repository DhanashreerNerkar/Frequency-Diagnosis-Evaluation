from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime

class CaseSchema(BaseModel):
    case_id: str = Field(..., description="Case Identifier")
    date_time: datetime = Field(..., description="UTC Date and Time")
    channel: Literal["Desktop", "Mobile", "Web"] = Field(..., description="Channel")
    user_id: str = Field(..., description="User Identifier")
    patient_id: str = Field(..., description="Patient Identifier")
    patient_conditions: str = Field(..., description="Patient Conditions")
    confirmed_diagnosis: bool = Field(default=False, description="Diagnosis confirmation status")

    model_config = {
        "validate_by_name": True,
        "json_schema_extra": {
            "example": {
                "case_id": "12345",
                "date_time": "2025-03-31T15:00:00Z",
                "channel": "Desktop",
                "user_id": "user_001",
                "patient_id": "patient_001",
                "patient_conditions": "Diabetes, Hypertension",
                "confirmed_diagnosis": True
            }
        }
    }