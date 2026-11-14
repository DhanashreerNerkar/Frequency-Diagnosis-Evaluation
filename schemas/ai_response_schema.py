from pydantic import BaseModel, Field
from typing import List
from .diagnosis_schema import DiagnosisSchema


class ModelResponseSchema(BaseModel):
    model_name: str = Field(..., description="Name of the Model (e.g., GPT)")
    temperature: float = Field(..., description="Temperature for the model")
    response_time: float = Field(..., description="Response time in seconds")
    user_role: str = Field(..., description="Role of the user (e.g., doctor, nurse)")
    diagnoses: List[DiagnosisSchema] = Field(..., description="List of Diagnoses")

    model_config = {
        "validate_by_name": True
    }