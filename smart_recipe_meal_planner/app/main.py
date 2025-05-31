from fastapi import FastAPI
from app.core.config import settings
from app.core.logging_config import setup_logging
# from app.api.v1 import api_router as api_v1_router # Will be created later

# Setup logging
setup_logging(log_level="DEBUG" if settings.DEBUG else "INFO")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG
)

# TODO: Add CORS middleware if needed
# from fastapi.middleware.cors import CORSMiddleware
# if settings.BACKEND_CORS_ORIGINS:
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )

# TODO: Include API routers
# app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

# Placeholder for future startup/shutdown events
# @app.on_event("startup")
# async def startup_event():
#     pass

# @app.on_event("shutdown")
# async def shutdown_event():
#     pass
