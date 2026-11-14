from fastapi import APIRouter
from controllers.lookup_controller import AuditLookupController
from schemas.lookup_schema import (
    LookupCreateSchema, LookupQuerySchema,
    SynonymAddSchema, SynonymStatusUpdate,
    DoctorReviewRequest, DoctorBatchReviewRequest
)
from schemas.lookup_response_schema import (
    LookupEntryResponse,
    PaginatedDoctorReviewResponse,
    MessageResponse
)
from typing import List


router = APIRouter(prefix="/api/v1/audit/lookup", tags=["Audit Lookup"])
controller = AuditLookupController()

@router.post("")
async def create_lookup(payload: LookupCreateSchema):
    return await controller.create_lookup(payload)

@router.get("",  response_model=List[LookupEntryResponse])
async def get_lookup(
        icd11_code: str | None = None,
        status: str | None = None,
        page: int = 1,
        limit: int = 100,
        updated_after: str | None = None
):
    q = LookupQuerySchema(
        icd11_code=icd11_code,
        status=status,
        page=page,
        limit=limit,
        updated_after=updated_after
    )
    return await controller.get_lookup_entries(q)

@router.post("/{icd11_code}/synonyms")
async def add_synonym(icd11_code: str, payload: SynonymAddSchema):
    return await controller.add_synonym(icd11_code, payload)

@router.put("/{icd11_code}/synonyms/{synonym_id}/status",  response_model=MessageResponse)
async def update_synonym_status(icd11_code: str, synonym_id: str, payload: SynonymStatusUpdate):
    return await controller.update_synonym_status(icd11_code, synonym_id, payload)

@router.get("/synonyms/pending-review")
async def get_pending_synonyms(page: int = 1, limit: int = 100):
    return await controller.get_pending_synonyms(page, limit)

@router.get("/doctor/synonyms")
async def get_synonyms_by_status(
        status: str = "all",
        page: int = 1,
        limit: int = 100,
        search: str | None = None
):
    """
    Doctor interface: View synonyms by status (new / cleared / wrong / all)
    Read-only endpoint
    """
    return await controller.get_synonyms_by_status(status, page, limit, search)


@router.post("/sync/to-cache")
async def sync_to_cache():
    return await controller.sync_to_cache()

@router.post("/sync/from-cache")
async def sync_from_cache():
    return await controller.sync_from_cache()

# Doctor Interface Endpoints
@router.get("/doctor/review",  response_model=PaginatedDoctorReviewResponse)
async def get_new_synonyms_for_review(
    page: int = 1, 
    limit: int = 100,
    search: str | None = None
):
    """
    Doctor interface: Fetch new synonyms from source (@src), tag them, and standardize diagnosis.
    Returns items ready for doctor review with standardized diagnosis information.
    Supports search by ICD-11 code or synonym text.
    """
    return await controller.get_new_synonyms_for_review(page, limit, search)

@router.post("/doctor/review")
async def doctor_review_synonym(payload: DoctorReviewRequest):
    """
    Doctor interface: Mark synonym as correct or wrong.
    Updates the lookup table with doctor's decision.
    """
    return await controller.doctor_review_synonym(payload)

@router.post("/doctor/review/batch")
async def doctor_review_synonyms_batch(payload: DoctorBatchReviewRequest):
    """
    Doctor interface: Batch review multiple synonyms.
    """
    return await controller.doctor_review_synonyms_batch(payload)