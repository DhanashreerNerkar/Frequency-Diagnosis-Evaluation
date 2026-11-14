from pydantic import BaseModel, Field

class MedicalCondition(BaseModel):
    name: str = Field(..., description="The name of the medical condition")
    probability: float = Field(..., description="The likelihood of this condition being present probability (0-1).")
    urgency: str = Field(..., description="The level of urgency required for treatment or intervention (e.g., Low, Moderate, High).")
    rationale: str = Field(..., description="A detailed explanation of why this condition is suspected based on symptoms and other factors.")
    treatment: list[str] = Field(..., description="The recommended treatment plan for managing or curing the condition. This may include medications and lifestyle changes.", min_items=3)


class MedicalResponse(BaseModel):
    conditions: list[MedicalCondition] = Field(..., description="A list of potential medical conditions along with their associated details such as probability, urgency, rationale, and treatment.")
