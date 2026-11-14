from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class StandardizedICDSchema(BaseModel):
    code: str = Field(..., description="ICD-11 diagnosis code")
    names: List[str] = Field(..., description="List of diagnosis names combined from NIH and WHO sources")
    source: List[str] = ["NIH"]
    last_updated: datetime = Field(..., description="UTC timestamp when this record was last standardized")

    model_config = {
        "validate_by_name": True,
        "json_schema_extra": {
            "example": {
                "code": "1A24",
                "names": ["Severe Malaria", "Malaria due to Plasmodium falciparum"],
                "source": ["NIH"],
                "last_updated": "2025-03-31T15:00:00Z"
            }
        }
    }
