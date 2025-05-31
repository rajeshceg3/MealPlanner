from .common_schemas import OrmBaseModel, IngredientUsagePublic, InstructionStepPublic
from .recipe_schemas import (
    RecipeBase, RecipeCreate, RecipeUpdate, RecipePublic,
    PaginatedRecipeResponse, RecipeDetailResponse,
    RecipeIngredientLinkCreate, InstructionStepCreate,
    RecipeRatingCreate, RecipeRatingPublic,
    IngredientBase, IngredientCreate, IngredientPublic, IngredientUpdate
)
import uuid # Ensure uuid is imported
from typing import Optional # Ensure Optional is imported

# Placeholder for user schemas, will be in user_schemas.py
class UserPublic(OrmBaseModel): # Ensure UserPublic is defined if imported elsewhere implicitly
    id: uuid.UUID
    email: str
    first_name: Optional[str] = None
    # Add other fields as needed, avoid exposing sensitive data
