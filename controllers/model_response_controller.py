from fastapi import HTTPException
from config.db import mongodb
from schemas.case_schema import CaseSchema
from schemas.responses import GenericResponse
from fastapi.responses import JSONResponse
from schemas.exceptions import ExceptionHandler
from schemas.ai_response_schema import ModelResponseSchema

class ModelResponseController:

    def __init__(self):
        self.COLLECTION_NAME="ai_responses"
        self.exception_handler = ExceptionHandler()

    async def store_ai_responses(self, case_id: str, ai_responses: list[ModelResponseSchema]):
        ai_responses_dicts = [
            {**ai_response.model_dump(), "case_id": case_id} for ai_response in ai_responses
        ]

        try:
            result = await mongodb.database[self.COLLECTION_NAME].insert_many(ai_responses_dicts)
            return GenericResponse(
                success=True,
                message="AI responses stored successfully",
                data={"inserted_ids": [str(id) for id in result.inserted_ids]},
            )
        except Exception as e:
            self.exception_handler.handle_exception(e)


model_response_controller = ModelResponseController()