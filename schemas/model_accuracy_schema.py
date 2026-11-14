from pydantic import BaseModel, Field


class ModelAccuracySchema(BaseModel):
    model_name: str = Field(..., description="Name of the model (e.g., GPT, Claude)")
    confirmed: str = Field(..., description="Confirmed diagnosis used for evaluation")

    TP: float = Field(..., description="True Positive average probability")
    FP: float = Field(..., description="False Positive average probability")
    C: int = Field(..., description="Count of confirmed diagnosis predictions")
    M: int = Field(..., description="Count of relevant predictions (p > 0)")
    F: float = Field(..., description="Frequency of confirmed diagnosis (C / M)")
    one_over_F: float = Field(..., alias="1/F", description="Inverse of F")
    Pmean: float = Field(..., description="Mean of predicted probabilities")
    dPmTP: float = Field(..., description="Distance between Pmean and TP")
    dPmF: float = Field(..., description="Distance between Pmean and F")
    dTPF: float = Field(..., description="Distance between TP and F")
    sdTPF: float = Field(..., description="Sum of (abs(p - F)) for TP cases")
    dTPC: float = Field(..., description="Distance between TP and C (sdTPF / C)")
    A: float = Field(..., description="Final Accuracy score")

    model_config = {
        "validate_by_name": True
    }
