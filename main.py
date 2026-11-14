import os

from fastapi import FastAPI, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from routers import diagnosis, testing, cases_router
from routers.lookup_router import router as lookup_router
from routers.accuracy_router import router as accuracy_router
from routers.strandard_icd_router import router as strandard_icd_router
from routers.db_viewer_router import router as db_viewer_router

import uvicorn
from dotenv import load_dotenv
from fastapi.exceptions import HTTPException
from config.db import mongodb
from contextlib import asynccontextmanager
from schemas.exceptions import custom_http_exception_handler

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Application is starting up...")
    app.include_router(cases_router.router)
    app.include_router(diagnosis.router)
    app.include_router(accuracy_router)
    app.include_router(testing.router)
    app.include_router(strandard_icd_router)
    app.include_router(lookup_router)
    app.include_router(db_viewer_router)

    await mongodb.connect()
    yield
    # Shutdown logic
    print("Application is shutting down...")
    await mongodb.close()

app = FastAPI(lifespan=lifespan)

# Mount static files - must be before other routes
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
if os.path.exists(static_dir):
    try:
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        print(f"[OK] Static files mounted from: {static_dir}")
    except Exception as e:
        print(f"[WARN] Could not mount static files: {e}")
else:
    print(f"[WARN] Static directory not found: {static_dir}")

app.add_exception_handler(HTTPException, custom_http_exception_handler)
# app.add_exception_handler(RequestValidationError, validation_exception_handler)
# app.add_exception_handler(Exception, generic_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @app.on_event("startup")
# async def startup():
#     app.include_router(diagnosis.router)
#     app.include_router(testing.router)
#     await mongodb.connect()

# @app.on_event("shutdown")
# async def shutdown():
#     await mongodb.close()

@app.get("/", include_in_schema=False)
def root():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return RedirectResponse(url='/docs')


@app.get("/healthz", include_in_schema=False)
async def health_check():
    return Response(status_code=status.HTTP_200_OK)

if __name__ == '__main__':
    _port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host='127.0.0.1', port=_port)