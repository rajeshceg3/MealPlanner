from sqlalchemy import Column, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class RecipeIngredient(Base):
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(50), nullable=False)
    preparation_note = Column(String(255))

    recipe = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_associations")

    __table_args__ = (UniqueConstraint('recipe_id', 'ingredient_id', name='uq_recipe_ingredient'),)
