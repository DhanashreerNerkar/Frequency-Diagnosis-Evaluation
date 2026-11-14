from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from controllers.multi_model import MultiModel
from models.model_type import ModelType
from schemas.diagnosis_schema import UpdateDiagnosisSchema
from controllers.diagnosis_controller import DiagnosisController
from controllers.onspot_diagnosis_controller import (create_onspot_diagnosis, get_onspot_by_case, list_onspot_diagnoses)
from controllers.cases_controller import case_controller
from schemas.diagnosis_response_schema import (
    DiagnosisInferenceResponse,
    UpdateDiagnosisResponse,
    OnspotDiagnosisResponse,
    OnspotDiagnosisListResponse
)

from schemas.onspot_diagnosis_schema import OnspotDiagnosisCreate

router = APIRouter(
    prefix='/diagnosis',
    tags=['Diagnosis']
)

multiModel = MultiModel()
diagnosis_controller = DiagnosisController()
@router.get(
    '/',
    response_model=DiagnosisInferenceResponse
)
def get_diagnosis_for_condition(patient_condition: str, model_name: ModelType):
    diagnosis = multiModel.invoke_model(
        model_type=model_name,
        condition=patient_condition
    )
    return diagnosis



@router.put('/{case_id}',   response_model=UpdateDiagnosisResponse)
async def update_case_diagnosis(case_id: str, payload: UpdateDiagnosisSchema):

    if not isinstance(payload.confirmed_diagnosis, list):
        raise HTTPException(status_code=422, detail="confirmed_diagnosis must be a list of strings")

    await case_controller.validate_case_id(case_id)

    try:
        updated_case = await diagnosis_controller.update_confirmed_diagnosis(
            case_id, payload.confirmed_diagnosis
        )
        if not updated_case:
            raise HTTPException(status_code=500, detail="Update succeeded but no document was returned")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Diagnosis updated successfully",
                "data": updated_case
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update diagnosis: {e}")


@router.post("/onspot", response_model=OnspotDiagnosisResponse,
            summary="Create/Update on-spot diagnosis for a case")
async def post_onspot_diagnosis(payload: OnspotDiagnosisCreate):
    return await create_onspot_diagnosis(payload)

@router.get("/onspot/{case_id}", response_model=OnspotDiagnosisResponse, summary="Get on-spot diagnosis by case_id")
async def get_onspot(case_id: str):
    return await get_onspot_by_case(case_id)

@router.get("/onspot", response_model=OnspotDiagnosisListResponse, summary="List all on-spot diagnoses")
async def list_onspot(
        skip: int = Query(0, ge=0, description="Number of docs to skip"),
        limit: int = Query(100, ge=1, le=500, description="Max docs to return"),
):
    return await list_onspot_diagnoses(skip=skip, limit=limit)
