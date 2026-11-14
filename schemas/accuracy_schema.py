from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AccuracyRequest(BaseModel):
    model_name: Optional[str] = Field(None, description="Name of the AI model")
    disease: Optional[str] = Field(None, description="Filter by disease name")
    icd11_code: Optional[str] = Field(None, description="Filter by ICD-11 code")
    start_date: Optional[datetime] = Field(None, description="Start of date range")
    end_date: Optional[datetime] = Field(None, description="End of date range")

    model_config = {
        "json_schema_extra": {
            "example": {
                "model_name": "GPT",
                "disease": "Diabetes",
                "icd11_code": "5A11",
                "start_date": "2021-01-01T00:00:00Z",
                "end_date": "2021-12-31T00:00:00Z"
            }
        }
    }
