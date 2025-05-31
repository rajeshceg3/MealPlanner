from sqlalchemy import Column, String, Text, Integer, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Recipe(Base):
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    instructions = Column(JSONB, nullable=False)
    prep_time_minutes = Column(Integer)
    cook_time_minutes = Column(Integer)
    servings = Column(Integer, server_default='4', nullable=False)
    difficulty_level = Column(String(20), server_default='medium', nullable=False)
    cuisine_type = Column(String(50), index=True)
    dietary_tags = Column(JSONB, server_default='[]', nullable=False)
    image_url = Column(String(500))
    source_url = Column(String(500))
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    average_rating = Column(Numeric(3, 2), server_default='0.00', nullable=False)
    rating_count = Column(Integer, server_default='0', nullable=False)

    creator_user = relationship("User", back_populates="recipes_created")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    meal_plan_associations = relationship("MealPlanRecipe", back_populates="recipe", cascade="all, delete-orphan")
    user_save_associations = relationship("UserSavedRecipe", back_populates="recipe", cascade="all, delete-orphan")
