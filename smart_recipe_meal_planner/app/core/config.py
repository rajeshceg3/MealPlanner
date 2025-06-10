from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Smart Recipe Meal Planner"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://user:password@localhost/smart_recipe_db" # Example
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256" # Consider RS256 for production as per PRD
    SECRET_KEY: str = "a_very_secret_key_that_should_be_changed" # CHANGE THIS!

    # For external APIs (Phase 2)
    SPOONACULAR_API_KEY: str = "your_spoonacular_api_key"
    EDAMAM_APP_ID: str = "your_edamam_app_id"
    EDAMAM_APP_KEY: str = "your_edamam_app_key"

    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"] # Example for frontend dev

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
