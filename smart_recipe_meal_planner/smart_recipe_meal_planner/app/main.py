
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.v1 import api_v1_router # Import the router from app/api/v1/__init__.py

# Setup logging as per previous steps
setup_logging(log_level="DEBUG" if settings.DEBUG else "INFO")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json", # Ensure API_V1_STR is defined in config
    debug=settings.DEBUG
)

# Add CORS middleware if BACKEND_CORS_ORIGINS is set in config
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).strip() for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include the V1 API router
# This line connects the routes defined in app/api/v1/ (via recipes.router) to the main app.
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    # Basic welcome message
    return {"message": f"Welcome to {settings.PROJECT_NAME} API. Visit /docs for API documentation."}

# Placeholder for startup/shutdown events if needed later
# @app.on_event("startup")
# async def startup_event():
#     # Initialize DB, etc.
#     pass

# @app.on_event("shutdown")
# async def shutdown_event():
#     # Clean up resources
#     pass
