from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class UserSavedRecipe(Base):
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)

    user = relationship("User", back_populates="saved_recipe_associations")
    recipe = relationship("Recipe", back_populates="user_save_associations")

    __table_args__ = (UniqueConstraint('user_id', 'recipe_id', name='uq_user_saved_recipe'),)
