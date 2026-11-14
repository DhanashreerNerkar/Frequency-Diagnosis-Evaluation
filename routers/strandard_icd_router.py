from controllers.strandard_icd_controller import icd_controller
from fastapi import APIRouter, Query, Path

router = APIRouter(
    prefix='/standardize_icd11',
    tags=['Standardize ICD-11']
)

@router.post("/build", status_code=201)
async def build_standard_icd_collection():
    return await icd_controller.build_standard_icd_collection()


@router.get("/", status_code=200)
async def fetch_standard_icd_codes(
        limit: int = Query(
            50,
            description="Number of standardized ICD-11 codes to retrieve from MongoDB."
        )
):

    return await icd_controller.fetch_standard_codes(limit=limit)


@router.get("/{code}", status_code=200)
async def fetch_standard_icd_code(
        code: str = Path(..., description="ICD-11 code to search in standardized collection.")
):
    return await icd_controller.search_code(code)
