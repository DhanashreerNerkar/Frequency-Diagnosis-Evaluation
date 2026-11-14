from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from utils.alias_generator import to_camel

class TestCaseRequestModel(BaseModel):
    selected_models: List[str] = Field(..., description="List of selected model names")
    prompt: Optional[str] = Field(None, description="Custom prompt entered by the user")
    is_default_prompt: bool = Field(..., description="Whether the default prompt is used")
    test_cases: List[str] = Field(..., description="List of selected test case names")
    frequency: int = Field(..., description="Single test in how many minute")
    terminate_after: int = Field(..., description="Number of times to terminate after")


    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

