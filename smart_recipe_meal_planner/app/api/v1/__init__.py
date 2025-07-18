
from fastapi import APIRouter
# Assuming app.api.v1.endpoints.recipes will exist and have a router attribute
from .endpoints import recipes
from .endpoints import external_recipes # New router import

api_v1_router = APIRouter()

# This will work if recipes.py defines a router = APIRouter()
# If recipes.py is empty or recipes.router doesnt exist, FastAPI might complain at startup
# but the file itself can be written.
api_v1_router.include_router(recipes.router, prefix="/recipes", tags=["Recipes"])
api_v1_router.include_router(external_recipes.router, prefix="/external-recipes", tags=["External Recipes"]) # Added new router
