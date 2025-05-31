from sqlalchemy import Column, String, Date, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class MealPlan(Base):
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    target_calories = Column(Integer)

    user = relationship("User", back_populates="meal_plans")
    meal_plan_recipes = relationship("MealPlanRecipe", back_populates="meal_plan", cascade="all, delete-orphan")
