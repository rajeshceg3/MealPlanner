from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.recipe_service import RecipeService
from app.db.models.user_model import User as DBUser # For current_user type hint
import uuid # For dummy user ID

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_recipe_service(db: Session = Depends(get_db)) -> RecipeService:
    return RecipeService(db=db)

# Placeholder for current user dependency - Replace with actual authentication
async def get_current_active_user(db: Session = Depends(get_db)) -> DBUser:
    # In a real app, this would involve token validation etc.
    # For now, fetch a user or create/return a dummy one.
    # This is NOT secure and only for placeholder functionality.
    user_id_to_fetch = uuid.UUID("00000000-0000-0000-0000-000000000000") # Example fixed UUID
    # Assuming User model has an 'id' field of type UUID
    user = db.query(DBUser).filter(DBUser.id == user_id_to_fetch).first()
    if not user:
        # If you want to ensure a user always exists for this placeholder:
        # user = DBUser(id=user_id_to_fetch, email="testuser@example.com", hashed_password="dummy_password", is_active=True, is_superuser=False) # Add other required fields
        # db.add(user)
        # db.commit()
        # db.refresh(user)
        # For now, if fixed UUID user doesn't exist, raise error to indicate setup needed.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Test user not found. Placeholder auth needs setup or a real user with ID 00000000-0000-0000-0000-000000000000."
        )
    return user
