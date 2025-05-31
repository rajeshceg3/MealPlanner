from sqlalchemy import Column, String, Numeric
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Ingredient(Base):
    name = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(String(100))
    calories_per_unit = Column(Numeric(8, 2))

    recipe_associations = relationship("RecipeIngredient", back_populates="ingredient", cascade="all, delete-orphan")
