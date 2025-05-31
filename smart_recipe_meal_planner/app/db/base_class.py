from sqlalchemy import Column, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
import uuid

@as_declarative()
class Base:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    __name__: str

    @declared_attr
    def __tablename__(cls) -> str:
        name = cls.__name__
        if name == "RecipeIngredient": return "recipe_ingredients"
        if name == "UserSavedRecipe": return "user_saved_recipes"
        if name == "MealPlanRecipe": return "meal_plan_recipes"
        # Basic pluralization
        if name.endswith("y") and name[-2] not in "aeiou": # e.g. Category -> categories
            return name[:-1].lower() + "ies"
        return name.lower() + ("" if name.endswith("s") else "s")
