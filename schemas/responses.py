from pydantic import BaseModel
from typing import Any, Optional


class GenericResponse(BaseModel):
    success: bool = True  
    message: str          
    data: Optional[Any] = None 
    error: Optional[Any] = None 

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": "12345"},
                "error": None,
            }
        }
    }
