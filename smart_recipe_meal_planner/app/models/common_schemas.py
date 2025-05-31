from pydantic import BaseModel, ConfigDict
from typing import Optional, List
import uuid
from datetime import datetime

class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class RecipeIngredientLink(OrmBaseModel):
    id: uuid.UUID
    name: str
    category: Optional[str] = None

class IngredientUsagePublic(OrmBaseModel):
    ingredient: RecipeIngredientLink
    quantity: float
    unit: str
    preparation_note: Optional[str] = None

class InstructionStepPublic(OrmBaseModel):
    step_number: int
    instruction: str
    estimated_time_minutes: Optional[int] = None
