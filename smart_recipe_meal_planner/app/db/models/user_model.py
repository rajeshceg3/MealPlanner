from sqlalchemy import Column, String, Date, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class User(Base):
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False) # PRD uses password_hash
    first_name = Column(String(100))
    last_name = Column(String(100))
    date_of_birth = Column(Date)
    dietary_restrictions = Column(JSONB, server_default='[]', nullable=False)
    calorie_goal = Column(Integer, server_default='2000', nullable=False)
    email_verified = Column(Boolean, server_default='false', nullable=False)
    is_active = Column(Boolean, server_default='true', nullable=False)

    recipes_created = relationship("Recipe", back_populates="creator_user", foreign_keys="[Recipe.created_by_user_id]")
    meal_plans = relationship("MealPlan", back_populates="user", cascade="all, delete-orphan")
    saved_recipe_associations = relationship("UserSavedRecipe", back_populates="user", cascade="all, delete-orphan")
