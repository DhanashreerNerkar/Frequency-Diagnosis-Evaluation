from controllers.cases_controller import case_controller
from controllers.model_response_controller import model_response_controller
from schemas.case_schema import CaseSchema
from schemas.ai_response_schema import ModelResponseSchema
from fastapi import APIRouter, Query, Path
from typing import Optional


router = APIRouter(
    prefix='/cases',
    tags=['Cases']
)

@router.post("/create", status_code=201)
async def create_case(case: CaseSchema):
    return await case_controller.create_case(case)

@router.put("/{case_id}/ai/responses", status_code=200)
async def update_case_ai_response(case_id: str, ai_responses: list[ModelResponseSchema]):
    
    await case_controller.validate_case_id(case_id)

    return await model_response_controller.store_ai_responses(case_id, ai_responses)


@router.get("/", status_code=200)
async def fetch_cases(
        confirmed_diagnosis: Optional[bool] = Query(None, description="Filter by confirmed diagnosis"),
        include_flag: bool = Query(False, description="If true, adds has_confirmed_diagnosis flag")
):
    return await case_controller.fetch_cases(
        confirmed_diagnosis=confirmed_diagnosis,
        include_flag=include_flag
    )


@router.get("/{case_id}", status_code=200)
async def fetch_case(
        case_id: str = Path(..., description="Case ID to fetch"),
        include_flag: bool = Query(False, description="If true, adds has_confirmed_diagnosis flag")
):
    return await case_controller.fetch_case(case_id=case_id, include_flag=include_flag)