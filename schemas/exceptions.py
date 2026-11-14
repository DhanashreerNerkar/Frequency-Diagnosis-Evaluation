from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .responses import GenericResponse
import logging

class ExceptionHandler:
    def __init__(self):
        logging.basicConfig(level=logging.ERROR)
        self.logger = logging.getLogger("ExceptionHandler")

    def handle_exception(self, exc: Exception):
        if isinstance(exc, HTTPException):
            self.logger.warning(f"HTTPException occurred: {exc.detail}")
            raise exc
        else:
            self.logger.error(f"An unexpected error occurred: {str(exc)}")
            raise HTTPException(status_code=500, detail="An unexpected server error occurred.")

async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=GenericResponse(
            success=False,
            message=exc.detail,
            error={"type": "InternalServerError" if exc.status_code == 500 else "HTTPException", "details": exc.detail},
        ).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content=GenericResponse(
            success=False,
            message="Validation Error",
            error={"type": "ValidationError", "details": exc.errors()},
        ).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=GenericResponse(
            success=False,
            message="An unexpected error occurred",
            error={"type": "InternalServerError", "details": str(exc)},
        ).model_dump(),
    )
