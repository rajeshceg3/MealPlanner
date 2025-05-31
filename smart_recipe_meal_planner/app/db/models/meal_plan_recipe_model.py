from sqlalchemy import Column, String, Date, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class MealPlanRecipe(Base):
    meal_plan_id = Column(UUID(as_uuid=True), ForeignKey('meal_plans.id', ondelete='CASCADE'), nullable=False)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    meal_date = Column(Date, nullable=False)
    meal_type = Column(String(20), nullable=False)
    servings = Column(Integer, server_default='1', nullable=False)
    position_order = Column(Integer, server_default='0', nullable=False)

    meal_plan = relationship("MealPlan", back_populates="meal_plan_recipes")
    recipe = relationship("Recipe", back_populates="meal_plan_associations")
