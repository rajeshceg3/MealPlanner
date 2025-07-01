from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Any
import uuid
from datetime import datetime
from .common_schemas import OrmBaseModel, IngredientUsagePublic, InstructionStepPublic

class IngredientBase(OrmBaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    calories_per_unit: Optional[float] = Field(None, gt=0)

class IngredientCreate(IngredientBase):
    pass

class IngredientPublic(IngredientBase):
    id: uuid.UUID
    created_at: datetime

class IngredientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    calories_per_unit: Optional[float] = Field(None, gt=0)

class RecipeIngredientLinkCreate(BaseModel):
    ingredient_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=50)
    preparation_note: Optional[str] = Field(None, max_length=255)

class InstructionStepCreate(BaseModel):
    step_number: int = Field(..., ge=1)
    instruction: str = Field(..., min_length=5)
    estimated_time_minutes: Optional[int] = Field(None, ge=0)

class RecipeBase(OrmBaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(4, ge=1)
    difficulty_level: Optional[str] = Field("medium", max_length=20)
    cuisine_type: Optional[str] = Field(None, max_length=50)
    dietary_tags: Optional[List[str]] = []
    image_url: Optional[HttpUrl] = None
    source_url: Optional[HttpUrl] = None
    spoonacular_id: Optional[int] = Field(None, description="Spoonacular recipe ID, if imported from Spoonacular.")
    calories: Optional[float] = Field(None, ge=0, description="Calories per serving")
    protein: Optional[float] = Field(None, ge=0, description="Protein per serving in grams")
    carbohydrates: Optional[float] = Field(None, ge=0, description="Carbohydrates per serving in grams")
    fat: Optional[float] = Field(None, ge=0, description="Fat per serving in grams")

class RecipeCreate(RecipeBase):
    instructions: List[InstructionStepCreate] = Field(..., min_length=1)
    ingredients: List[RecipeIngredientLinkCreate] = Field(..., min_length=1)

class RecipeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1)
    difficulty_level: Optional[str] = Field(None, max_length=20)
    cuisine_type: Optional[str] = Field(None, max_length=50)
    dietary_tags: Optional[List[str]] = None
    image_url: Optional[HttpUrl] = None
    source_url: Optional[HttpUrl] = None
    instructions: Optional[List[InstructionStepCreate]] = Field(None, min_length=1)
    ingredients: Optional[List[RecipeIngredientLinkCreate]] = Field(None, min_length=1)
    calories: Optional[float] = Field(None, ge=0, description="Calories per serving")
    protein: Optional[float] = Field(None, ge=0, description="Protein per serving in grams")
    carbohydrates: Optional[float] = Field(None, ge=0, description="Carbohydrates per serving in grams")
    fat: Optional[float] = Field(None, ge=0, description="Fat per serving in grams")

class RecipePublic(RecipeBase):
    id: uuid.UUID
    created_by_user_id: Optional[uuid.UUID] = None
    average_rating: float = 0.0
    rating_count: int = 0
    created_at: datetime
    updated_at: datetime
    instructions: List[InstructionStepPublic]
    recipe_ingredients: List[IngredientUsagePublic] = []
    user_has_saved: Optional[bool] = None
    user_rating: Optional[int] = None

class PaginatedRecipeResponse(OrmBaseModel):
    success: bool = True
    data: List[RecipePublic]
    pagination: dict # E.g. {"currentPage": 1, "totalPages": 10, "totalItems": 100, "hasNext": true, "hasPrevious": false}

class ExternalRecipeSearchResultItem(BaseModel):
    spoonacular_id: int
    title: str
    image_url: Optional[HttpUrl] = None
    source_url: Optional[HttpUrl] = None
    ready_in_minutes: Optional[int] = None
    servings: Optional[int] = None

class PaginatedExternalRecipeSearchResponse(BaseModel):
    success: bool = True
    data: List[ExternalRecipeSearchResultItem]
    pagination: dict # E.g. {"currentPage": 1, "totalPages": 10, "totalItems": 100, "hasNext": true, "hasPrevious": false}

class RecipeDetailResponse(OrmBaseModel):
    success: bool = True
    data: RecipePublic

class RecipeRatingCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = None

class RecipeRatingPublic(OrmBaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    recipe_id: uuid.UUID
    rating: int
    review_text: Optional[str] = None
    created_at: datetime
