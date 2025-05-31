import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add project root to sys.path to find the 'app' module
# The project_dir should point to the outer 'smart_recipe_meal_planner' directory
# which contains 'app', 'pyproject.toml' etc.
# __file__ is smart_recipe_meal_planner/smart_recipe_meal_planner/migrations/env.py
# os.path.dirname(__file__) is s_r_m_p/s_r_m_p/migrations
# os.path.join(os.path.dirname(__file__), "..") is s_r_m_p/s_r_m_p
# os.path.join(os.path.dirname(__file__), "..", "..") is s_r_m_p (the correct project root)
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_dir)

from app.core.config import settings
from app.db.base_class import Base
# Ensure all models are imported for Alembic autogenerate
from app.db.models.user_model import User # noqa
from app.db.models.recipe_model import Recipe # noqa
from app.db.models.ingredient_model import Ingredient # noqa
from app.db.models.recipe_ingredient_model import RecipeIngredient # noqa
from app.db.models.meal_plan_model import MealPlan # noqa
from app.db.models.meal_plan_recipe_model import MealPlanRecipe # noqa
from app.db.models.user_saved_recipe_model import UserSavedRecipe # noqa
# The above explicit imports are generally better than `from app.db.models import *`
# but the original prompt used wildcard. Sticking to Base.metadata should be fine.

target_metadata = Base.metadata

def get_url():
    # Ensure DATABASE_URL is used, which should be correctly loaded by settings
    return str(settings.DATABASE_URL)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True, # Added for better comparison of types
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    db_url = get_url()

    # Use a dictionary for connectable_config_dict to avoid issues if section is missing
    connectable_config_dict = config.get_section(config.config_ini_section)
    if connectable_config_dict is None:
        connectable_config_dict = {} # Initialize if missing
    connectable_config_dict["sqlalchemy.url"] = db_url

    connectable = engine_from_config(
        connectable_config_dict, # Pass the dictionary directly
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True, # Added for better comparison of types
            # compare_server_default=True # Consider adding if needed for server defaults
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
