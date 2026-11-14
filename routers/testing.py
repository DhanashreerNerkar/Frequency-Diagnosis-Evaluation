from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from schemas.test_schedule_request import TestCaseRequestModel

router = APIRouter(
    prefix='/testing',
    tags=['Testing Scheduler']
)


@router.post('/schedule')
def get_diagnosis_for_condition(payload: TestCaseRequestModel):
    return JSONResponse(
        status_code=status.HTTP_200_OK,
    )