from fastapi import HTTPException
from config.db import mongodb
from schemas.case_schema import CaseSchema
from schemas.responses import GenericResponse
from fastapi.responses import JSONResponse
from schemas.exceptions import ExceptionHandler

class CaseController:

    def __init__(self):
        self.CASES_COLLECTION="cases"
        self.DIAGNOSIS_COLLECTION="diagnoses"
        self.exception_handler = ExceptionHandler()

    async def validate_case_id(self, case_id: str):
        case = await mongodb.database[self.CASES_COLLECTION].find_one({"case_id": case_id})
        if not case:
            raise HTTPException(status_code=404, detail=f"case with ID {case_id} not found, try creating the case first")


    async def create_case(self, case: CaseSchema):
        try:
            case_dict = case.model_dump()

            case_dict["confirmed_diagnosis"] = False

            existing_case = await mongodb.database[self.CASES_COLLECTION].find_one({"case_id": case.case_id})
            
            if existing_case:
                raise HTTPException(status_code=400, detail="Case with this ID already exists")

            result = await mongodb.database[self.CASES_COLLECTION].insert_one(case_dict)
            return GenericResponse(
                success=True,
                message="Case inserted successfully",
                data={"id": str(result.inserted_id)},
            )
        except Exception as e:
            self.exception_handler.handle_exception(e)

    async def fetch_cases(self, confirmed_diagnosis: bool = None, include_flag: bool = False):
        try:
            query = {}
            if confirmed_diagnosis is not None:
                query["confirmed_diagnosis"] = confirmed_diagnosis

            cursor = mongodb.database[self.CASES_COLLECTION].find(query, {"_id": 0})
            cases = await cursor.to_list(length=None)

            if include_flag:
                for c in cases:
                    c["has_confirmed_diagnosis"] = bool(c.get("confirmed_diagnosis", False))

            return GenericResponse(
                success=True,
                message="Cases fetched successfully",
                data=cases
            )
        except Exception as e:
            self.exception_handler.handle_exception(e)

    async def fetch_case(self, case_id: str, include_flag: bool = False):
        try:
            doc = await mongodb.database[self.CASES_COLLECTION].find_one({"case_id": case_id}, {"_id": 0})
            if not doc:
                raise HTTPException(status_code=404, detail="Case not found")

            if include_flag:
                doc["has_confirmed_diagnosis"] = bool(doc.get("confirmed_diagnosis", False))

            return GenericResponse(
                success=True,
                message="Case fetched successfully",
                data=doc
            )
        except Exception as e:
            self.exception_handler.handle_exception(e)

case_controller = CaseController()