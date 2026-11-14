from fastapi import APIRouter
from schemas.accuracy_schema import AccuracyRequest
from controllers.accuracy_controller import calculate_detailed_metrics

router = APIRouter(
    tags=["Accuracy"]
)

@router.post("/calculate/accuracy", status_code=200, summary="Calculate Detailed Metrics")
async def calculate_accuracy(request: AccuracyRequest):
    return await calculate_detailed_metrics(request)
