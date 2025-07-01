
import math
import logging # New
from uuid import UUID # Changed
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import or_, func # or_ added
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.future import select
from pydantic import parse_obj_as

from app.db.models.recipe_model import Recipe as DBRecipe
from app.db.models.ingredient_model import Ingredient as DBIngredient
from app.db.models.recipe_ingredient_model import RecipeIngredient as DBRecipeIngredient
from app.models.recipe_schemas import RecipeCreate, RecipeUpdate, RecipePublic, InstructionStepPublic, InstructionStepCreate, RecipeIngredientLinkCreate # RecipeIngredientLinkCreate added
from app.models.common_schemas import IngredientUsagePublic, RecipeIngredientLink

# Added Spoonacular client and mapper imports
from app.clients.spoonacular_client import SpoonacularClient, SpoonacularException, SpoonacularRateLimitException
from app.services.recipe_mapper import map_spoonacular_data_to_dict

logger = logging.getLogger(__name__) # Added logger

class RecipeService:
    def __init__(self, db: Session):
        self.db = db

    async def create_recipe(self, recipe_in: RecipeCreate, user_id: UUID) -> RecipePublic:
        # Convert instructions to list of dicts for JSONB storage
        instructions_data = [instr.model_dump() for instr in recipe_in.instructions]

        # Create DBRecipe object
        db_recipe_obj = DBRecipe(
            title=recipe_in.title,
            description=recipe_in.description,
            instructions=instructions_data,
            prep_time_minutes=recipe_in.prep_time_minutes,
            cook_time_minutes=recipe_in.cook_time_minutes,
            servings=recipe_in.servings,
            difficulty_level=recipe_in.difficulty_level,
            cuisine_type=recipe_in.cuisine_type,
            dietary_tags=recipe_in.dietary_tags,
            image_url=str(recipe_in.image_url) if recipe_in.image_url else None,
            source_url=str(recipe_in.source_url) if recipe_in.source_url else None,
            created_by_user_id=user_id,
            spoonacular_id=recipe_in.spoonacular_id, # Added spoonacular_id
            # Add new nutritional fields
            calories=recipe_in.calories,
            protein=recipe_in.protein,
            carbohydrates=recipe_in.carbohydrates,
            fat=recipe_in.fat
        )

        # Handle ingredients
        for ingredient_link_in in recipe_in.ingredients:
            # Assuming ingredient_id refers to an existing ingredient.
            # A robust implementation might fetch DBIngredient here to ensure it exists.
            db_recipe_ingredient = DBRecipeIngredient(
                ingredient_id=ingredient_link_in.ingredient_id,
                quantity=ingredient_link_in.quantity,
                unit=ingredient_link_in.unit,
                preparation_note=ingredient_link_in.preparation_note
            )
            db_recipe_obj.recipe_ingredients.append(db_recipe_ingredient)

        self.db.add(db_recipe_obj)
        self.db.commit()
        self.db.refresh(db_recipe_obj)

        # Construct RecipePublic response
        # Parse instructions from JSONB
        parsed_instructions = parse_obj_as(List[InstructionStepPublic], db_recipe_obj.instructions)

        # Map recipe ingredients to IngredientUsagePublic
        recipe_ingredients_public = []
        for ri in db_recipe_obj.recipe_ingredients:
            # We need to fetch the ingredient details from the DBIngredient table
            # This assumes the ingredient object is loaded/available via the relationship
            # If not, a query might be needed: self.db.query(DBIngredient).get(ri.ingredient_id)
            ingredient_db = self.db.query(DBIngredient).get(ri.ingredient_id)
            if not ingredient_db:
                # This case should ideally not happen if FK constraints are in place
                # and ingredients are validated. Handling defensively.
                # Or, raise an error. For now, skipping if ingredient not found.
                continue

            ingredient_link = RecipeIngredientLink(
                id=ingredient_db.id,
                name=ingredient_db.name,
                category=ingredient_db.category
            )
            recipe_ingredients_public.append(
                IngredientUsagePublic(
                    ingredient=ingredient_link,
                    quantity=float(ri.quantity), # Ensure conversion from Decimal
                    unit=ri.unit,
                    preparation_note=ri.preparation_note
                )
            )

        return RecipePublic(
            id=db_recipe_obj.id,
            title=db_recipe_obj.title,
            description=db_recipe_obj.description,
            prep_time_minutes=db_recipe_obj.prep_time_minutes,
            cook_time_minutes=db_recipe_obj.cook_time_minutes,
            servings=db_recipe_obj.servings,
            difficulty_level=db_recipe_obj.difficulty_level,
            cuisine_type=db_recipe_obj.cuisine_type,
            dietary_tags=db_recipe_obj.dietary_tags, # Assumes JSONB from DB is compatible
            image_url=db_recipe_obj.image_url,
            source_url=db_recipe_obj.source_url,
            created_by_user_id=db_recipe_obj.created_by_user_id,
            average_rating=float(db_recipe_obj.average_rating), # Ensure conversion
            rating_count=db_recipe_obj.rating_count,
            created_at=db_recipe_obj.created_at,
            updated_at=db_recipe_obj.updated_at,
            instructions=parsed_instructions,
            recipe_ingredients=recipe_ingredients_public,
            user_has_saved=None, # Not handled in this method
            user_rating=None,    # Not handled in this method
            spoonacular_id=db_recipe_obj.spoonacular_id, # Added spoonacular_id
            # Add new nutritional fields to the response
            calories=db_recipe_obj.calories,
            protein=db_recipe_obj.protein,
            carbohydrates=db_recipe_obj.carbohydrates,
            fat=db_recipe_obj.fat
        )

    async def get_recipes_list(
        self, page: int, limit: int, cuisine: Optional[str] = None,
        dietary_tags: Optional[List[str]] = None, max_cook_time: Optional[int] = None,
        search_query: Optional[str] = None
    ) -> Tuple[List[RecipePublic], Dict[str, Any]]:
        offset = (page - 1) * limit # type: ignore

        # Base query for fetching recipes
        stmt = (
            select(DBRecipe)
            .options(
                joinedload(DBRecipe.recipe_ingredients).joinedload(DBRecipeIngredient.ingredient)
            )
            .order_by(DBRecipe.created_at.desc()) # Consistent ordering
        )

        # Base count query
        count_stmt = select(func.count()).select_from(DBRecipe)

        # TODO: Apply filters to both stmt and count_stmt based on cuisine, dietary_tags, etc.
        # Example for cuisine (if it's a direct match):
        # if cuisine:
        #     stmt = stmt.where(DBRecipe.cuisine_type == cuisine)
        #     count_stmt = count_stmt.where(DBRecipe.cuisine_type == cuisine)
        # For dietary_tags (assuming JSONB contains a list of strings):
        # if dietary_tags:
        #     stmt = stmt.where(DBRecipe.dietary_tags.contains(dietary_tags)) # Adjust based on actual JSON structure
        #     count_stmt = count_stmt.where(DBRecipe.dietary_tags.contains(dietary_tags))
        # For max_cook_time:
        # if max_cook_time is not None:
        #     stmt = stmt.where(DBRecipe.cook_time_minutes <= max_cook_time)
        #     count_stmt = count_stmt.where(DBRecipe.cook_time_minutes <= max_cook_time)
        # For search_query (e.g., search in title and description):
        # if search_query:
        #     search_filter = or_(
        #         DBRecipe.title.ilike(f"%{search_query}%"),
        #         DBRecipe.description.ilike(f"%{search_query}%")
        #     )
        #     stmt = stmt.where(search_filter)
        #     count_stmt = count_stmt.where(search_filter)

        # Apply pagination to the main query
        stmt = stmt.offset(offset).limit(limit)

        # Execute queries
        # Note: For async, ensure your DB driver supports async operations.
        # Here, self.db.execute is assumed to be handled by FastAPI's async session management.
        db_recipes_result = self.db.execute(stmt)
        db_recipes = db_recipes_result.scalars().all()

        total_items_result = self.db.execute(count_stmt)
        total_items = total_items_result.scalar_one()

        # Convert DBRecipe objects to RecipePublic
        recipes_public_list: List[RecipePublic] = []
        for db_recipe in db_recipes:
            parsed_instructions = parse_obj_as(List[InstructionStepPublic], db_recipe.instructions)
            recipe_ingredients_public = []
            for ri in db_recipe.recipe_ingredients:
                if ri.ingredient:
                    ingredient_link = RecipeIngredientLink(
                        id=ri.ingredient.id,
                        name=ri.ingredient.name,
                        category=ri.ingredient.category
                    )
                    recipe_ingredients_public.append(
                        IngredientUsagePublic(
                            ingredient=ingredient_link,
                            quantity=float(ri.quantity),
                            unit=ri.unit,
                            preparation_note=ri.preparation_note
                        )
                    )

            recipes_public_list.append(
                RecipePublic(
                    id=db_recipe.id,
                    title=db_recipe.title,
                    description=db_recipe.description,
                    prep_time_minutes=db_recipe.prep_time_minutes,
                    cook_time_minutes=db_recipe.cook_time_minutes,
                    servings=db_recipe.servings,
                    difficulty_level=db_recipe.difficulty_level,
                    cuisine_type=db_recipe.cuisine_type,
                    dietary_tags=db_recipe.dietary_tags,
                    image_url=db_recipe.image_url,
                    source_url=db_recipe.source_url,
                    created_by_user_id=db_recipe.created_by_user_id,
                    average_rating=float(db_recipe.average_rating),
                    rating_count=db_recipe.rating_count,
                    created_at=db_recipe.created_at,
                    updated_at=db_recipe.updated_at,
                    instructions=parsed_instructions,
                    recipe_ingredients=recipe_ingredients_public,
                    user_has_saved=None, # Not determined in this list view
                    user_rating=None,    # Not determined in this list view
                    spoonacular_id=db_recipe.spoonacular_id, # Added spoonacular_id
                    # Add new nutritional fields to the response
                    calories=db_recipe.calories,
                    protein=db_recipe.protein,
                    carbohydrates=db_recipe.carbohydrates,
                    fat=db_recipe.fat
                )
            )

        # Pagination metadata
        total_pages = math.ceil(total_items / limit) if limit > 0 else 0
        pagination_meta = {
            "currentPage": page,
            "totalPages": total_pages,
            "totalItems": total_items,
            "hasNext": page < total_pages,
            "hasPrevious": page > 1,
            "itemsPerPage": limit
        }

        return recipes_public_list, pagination_meta

    async def get_recipe_by_id(self, recipe_id: UUID, user_id: Optional[UUID] = None) -> Optional[RecipePublic]:
        # Construct query with eager loading
        stmt = (
            select(DBRecipe)
            .where(DBRecipe.id == recipe_id)
            .options(
                joinedload(DBRecipe.recipe_ingredients).joinedload(DBRecipeIngredient.ingredient),
                # joinedload(DBRecipe.creator_user) # Uncomment if full user object needed
            )
        )
        db_recipe = self.db.execute(stmt).scalar_one_or_none()

        if db_recipe is None:
            return None

        # Parse instructions from JSONB
        parsed_instructions = parse_obj_as(List[InstructionStepPublic], db_recipe.instructions)

        # Map recipe ingredients to IngredientUsagePublic
        recipe_ingredients_public = []
        for ri in db_recipe.recipe_ingredients:
            if ri.ingredient: # Check if ingredient was successfully loaded
                ingredient_link = RecipeIngredientLink(
                    id=ri.ingredient.id,
                    name=ri.ingredient.name,
                    category=ri.ingredient.category
                )
                recipe_ingredients_public.append(
                    IngredientUsagePublic(
                        ingredient=ingredient_link,
                        quantity=float(ri.quantity), # Ensure conversion from Decimal
                        unit=ri.unit,
                        preparation_note=ri.preparation_note
                    )
                )
            else:
                # Handle cases where an ingredient might be missing, though FK constraints should prevent this
                # Log this situation if it occurs
                pass


        # TODO: Implement logic for user_has_saved and user_rating based on user_id if provided
        # For now, defaulting to None as per current scope
        user_has_saved_status = None
        user_specific_rating = None

        # if user_id:
        #     # Example: Check if user saved this recipe
        #     # saved_link = self.db.query(UserSavedRecipe).filter_by(user_id=user_id, recipe_id=recipe_id).first()
        #     # user_has_saved_status = saved_link is not None
        #     # Example: Get user's rating for this recipe
        #     # rating_obj = self.db.query(RecipeRating).filter_by(user_id=user_id, recipe_id=recipe_id).first()
        #     # user_specific_rating = rating_obj.rating if rating_obj else None
        #     pass


        return RecipePublic(
            id=db_recipe.id,
            title=db_recipe.title,
            description=db_recipe.description,
            prep_time_minutes=db_recipe.prep_time_minutes,
            cook_time_minutes=db_recipe.cook_time_minutes,
            servings=db_recipe.servings,
            difficulty_level=db_recipe.difficulty_level,
            cuisine_type=db_recipe.cuisine_type,
            dietary_tags=db_recipe.dietary_tags,
            image_url=db_recipe.image_url,
            source_url=db_recipe.source_url,
            created_by_user_id=db_recipe.created_by_user_id,
            average_rating=float(db_recipe.average_rating),
            rating_count=db_recipe.rating_count,
            created_at=db_recipe.created_at,
            updated_at=db_recipe.updated_at,
            instructions=parsed_instructions,
            recipe_ingredients=recipe_ingredients_public,
            user_has_saved=user_has_saved_status,
            user_rating=user_specific_rating,
            spoonacular_id=db_recipe.spoonacular_id, # Added spoonacular_id
            # Add new nutritional fields to the response
            calories=db_recipe.calories,
            protein=db_recipe.protein,
            carbohydrates=db_recipe.carbohydrates,
            fat=db_recipe.fat
        )

    async def update_recipe(self, recipe_id: UUID, recipe_in: RecipeUpdate, user_id: UUID) -> Optional[RecipePublic]:
        # Fetch the recipe with its ingredients
        stmt = (
            select(DBRecipe)
            .where(DBRecipe.id == recipe_id)
            .options(
                joinedload(DBRecipe.recipe_ingredients).joinedload(DBRecipeIngredient.ingredient)
            )
        )
        db_recipe = self.db.execute(stmt).scalar_one_or_none()

        if db_recipe is None:
            return None

        # Authorization check
        if db_recipe.created_by_user_id != user_id:
            # Optionally, raise HTTPException(status_code=403, detail="Not authorized to update this recipe")
            return None

        # Update basic fields
        update_data = recipe_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(db_recipe, key) and key not in ["instructions", "ingredients"]:
                setattr(db_recipe, key, value)
            elif key == "image_url" or key == "source_url": # Handle HttpUrl conversion
                 setattr(db_recipe, key, str(value) if value else None)


        # Update instructions if provided
        if recipe_in.instructions is not None:
            db_recipe.instructions = [instr.model_dump() for instr in recipe_in.instructions]

        # Update ingredients if provided
        if recipe_in.ingredients is not None:
            # Clear existing ingredients.
            # The 'all, delete-orphan' cascade should handle deletion from the DB.
            db_recipe.recipe_ingredients.clear()
            # Or, explicit deletion:
            # for old_recipe_ingredient in list(db_recipe.recipe_ingredients): # Iterate over a copy
            #    self.db.delete(old_recipe_ingredient)
            # self.db.flush() # Ensure deletes are processed before adds if not using clear()

            # Add new ingredients
            for ingredient_link_in in recipe_in.ingredients:
                # It's good practice to ensure the ingredient exists, though not strictly required by this task
                # ingredient_check = self.db.query(DBIngredient).get(ingredient_link_in.ingredient_id)
                # if not ingredient_check:
                #     # Handle missing ingredient error, e.g., raise HTTPException
                #     continue
                new_db_recipe_ingredient = DBRecipeIngredient(
                    ingredient_id=ingredient_link_in.ingredient_id,
                    quantity=ingredient_link_in.quantity,
                    unit=ingredient_link_in.unit,
                    preparation_note=ingredient_link_in.preparation_note
                    # recipe_id=db_recipe.id # Not needed if appended to relationship
                )
                db_recipe.recipe_ingredients.append(new_db_recipe_ingredient)

        self.db.add(db_recipe) # Add to session to track changes
        self.db.commit()
        self.db.refresh(db_recipe) # Refresh to get updated state, including new ingredient IDs if any

        # Re-fetch the ingredient details for the response if they were changed.
        # The refresh above should update scalar properties and potentially collections,
        # but nested relationships (ingredient details within recipe_ingredients) might need care.
        # A simple way is to call get_recipe_by_id, but this is an extra DB hit.
        # For now, we will reconstruct it manually, assuming refresh populated enough.
        # If ingredient details were not part of the refresh of db_recipe.recipe_ingredients,
        # we might need to explicitly load them or use the get_recipe_by_id method.
        # Let's try to reconstruct manually assuming relationships are okay after refresh.

        parsed_instructions = parse_obj_as(List[InstructionStepPublic], db_recipe.instructions)

        recipe_ingredients_public = []
        for ri in db_recipe.recipe_ingredients:
            # After refresh, ri.ingredient might not be loaded if we only loaded it initially.
            # A full reload of the recipe or specific reloading of these relationships might be needed.
            # For simplicity, let's assume we need to fetch ingredient details if not present.
            # This is similar to create_recipe's ingredient fetching logic.
            ingredient_details = ri.ingredient
            if not ingredient_details: # If not eagerly loaded or refreshed properly
                 ingredient_details = self.db.query(DBIngredient).get(ri.ingredient_id)

            if ingredient_details:
                ingredient_link = RecipeIngredientLink(
                    id=ingredient_details.id,
                    name=ingredient_details.name,
                    category=ingredient_details.category
                )
                recipe_ingredients_public.append(
                    IngredientUsagePublic(
                        ingredient=ingredient_link,
                        quantity=float(ri.quantity),
                        unit=ri.unit,
                        preparation_note=ri.preparation_note
                    )
                )
            # else: handle missing ingredient if necessary, though FK should prevent this state.

        return RecipePublic(
            id=db_recipe.id,
            title=db_recipe.title,
            description=db_recipe.description,
            prep_time_minutes=db_recipe.prep_time_minutes,
            cook_time_minutes=db_recipe.cook_time_minutes,
            servings=db_recipe.servings,
            difficulty_level=db_recipe.difficulty_level,
            cuisine_type=db_recipe.cuisine_type,
            dietary_tags=db_recipe.dietary_tags,
            image_url=db_recipe.image_url,
            source_url=db_recipe.source_url,
            created_by_user_id=db_recipe.created_by_user_id,
            average_rating=float(db_recipe.average_rating),
            rating_count=db_recipe.rating_count,
            created_at=db_recipe.created_at,
            updated_at=db_recipe.updated_at, # Should be updated by DB timestamp trigger or manually
            instructions=parsed_instructions,
            recipe_ingredients=recipe_ingredients_public,
            user_has_saved=None, # TODO: Implement if needed
            user_rating=None,    # TODO: Implement if needed
            spoonacular_id=db_recipe.spoonacular_id, # Added spoonacular_id
            # Add new nutritional fields to the response
            calories=db_recipe.calories,
            protein=db_recipe.protein,
            carbohydrates=db_recipe.carbohydrates,
            fat=db_recipe.fat
        )

    async def delete_recipe(self, recipe_id: UUID, user_id: UUID) -> bool:
        stmt = select(DBRecipe).where(DBRecipe.id == recipe_id)
        # For async, ensure self.db.execute is compatible.
        # result = await self.db.execute(stmt) # type: ignore
        # db_recipe = result.scalar_one_or_none() # type: ignore
        db_recipe = self.db.execute(stmt).scalar_one_or_none() # type: ignore


        if db_recipe is None:
            return False # Recipe not found

        # Authorization check
        if db_recipe.created_by_user_id != user_id:
            # Optionally, raise HTTPException(status_code=403, detail="Not authorized to delete this recipe")
            return False # User is not the owner

        # self.db.delete is synchronous by default with traditional SQLAlchemy,
        # ensure it's called correctly in an async context (e.g. via await self.db.run_sync(self.db.delete, db_recipe) or similar
        # if using greenlet/asyncpg for true async. For this example, assuming direct compatibility or simplified async handling.
        self.db.delete(db_recipe)
        self.db.commit()
        # await self.db.delete(db_recipe) # If using an async session method
        # await self.db.commit()          # If using an async session method

        return True

    async def add_recipe_to_favorites(self, recipe_id: UUID, user_id: UUID) -> Any:
        # Placeholder: return would be RecipePublic
        print(f"RecipeService: add_recipe_to_favorites called for recipe_id: {recipe_id}, user_id: {user_id}")
        raise NotImplementedError("RecipeService: add_recipe_to_favorites not implemented")

    async def remove_recipe_from_favorites(self, recipe_id: UUID, user_id: UUID) -> bool:
        print(f"RecipeService: remove_recipe_from_favorites called for recipe_id: {recipe_id}, user_id: {user_id}")
        raise NotImplementedError("RecipeService: remove_recipe_from_favorites not implemented")

    async def rate_recipe(self, recipe_id: UUID, rating_in: Any, user_id: UUID) -> Any:
        # Placeholder: rating_in would be RecipeRatingCreate, return would be RecipeRatingPublic
        print(f"RecipeService: rate_recipe called for recipe_id: {recipe_id}, user_id: {user_id} with rating: {rating_in}")
        raise NotImplementedError("RecipeService: rate_recipe not implemented")

    async def get_ratings_for_recipe(self, recipe_id: UUID) -> List[Any]:
        # Placeholder: return would be List[RecipeRatingPublic]
        print(f"RecipeService: get_ratings_for_recipe called for recipe_id: {recipe_id}")
        raise NotImplementedError("RecipeService: get_ratings_for_recipe not implemented")

    async def _get_or_create_ingredient(
        self,
        name: str,
        category: Optional[str] = "Unknown",
        calories_per_unit: Optional[float] = None
    ) -> DBIngredient:
        normalized_name = name.strip().lower()
        stmt = select(DBIngredient).where(func.lower(DBIngredient.name) == normalized_name)
        existing_ingredient = self.db.execute(stmt).scalars().first()
        if existing_ingredient:
            return existing_ingredient
        else:
            # Use provided category, defaulting to "Unknown" if None
            ingredient_category = category if category is not None else "Unknown"
            new_ingredient = DBIngredient(
                name=name.strip(),
                category=ingredient_category,
                calories_per_unit=calories_per_unit
            )
            self.db.add(new_ingredient)
            try:
                self.db.commit()
                self.db.refresh(new_ingredient)
                return new_ingredient
            except Exception as e:
                self.db.rollback()
                stmt_retry = select(DBIngredient).where(func.lower(DBIngredient.name) == normalized_name)
                existing_ingredient_retry = self.db.execute(stmt_retry).scalars().first()
                if existing_ingredient_retry:
                    return existing_ingredient_retry
                logger.error(f"Error creating ingredient '{name}': {e}")
                raise

    async def search_external_recipes(
        self, query: str, page: int = 1, limit: int = 10
    ) -> Dict[str, Any]:
        client = None
        try:
            client = SpoonacularClient()
            offset = (page - 1) * limit
            spoonacular_response = await client.search_recipes(
                query=query, offset=offset, number=limit,
                add_recipe_information=True, fill_ingredients=False
            )
        except SpoonacularRateLimitException as e:
            logger.error(f"Spoonacular API rate limit during search: {e}")
            raise
        except SpoonacularException as e:
            logger.error(f"Spoonacular API error during search: {e}")
            raise
        except ValueError as e: # Catches API key configuration errors from SpoonacularClient init
            logger.error(f"SpoonacularClient config error: {e}")
            # Re-raise as a more generic exception or a custom one if defined for service layer
            raise Exception(f"Spoonacular client configuration error: {e}") from e
        finally:
            if client:
                await client.close()

        results = spoonacular_response.get("results", [])
        total_items = spoonacular_response.get("totalResults", 0)

        search_results_public = []
        for res in results:
            search_results_public.append({
                "spoonacular_id": res.get("id"),
                "title": res.get("title"),
                "image_url": res.get("image"),
                "source_url": res.get("sourceUrl"), # Spoonacular uses sourceUrl
                "ready_in_minutes": res.get("readyInMinutes"),
                "servings": res.get("servings")
            })

        total_pages = math.ceil(total_items / limit) if limit > 0 else 0
        pagination_meta = {
            "currentPage": page,
            "totalPages": total_pages,
            "totalItems": total_items,
            "hasNext": page < total_pages,
            "hasPrevious": page > 1,
            "itemsPerPage": limit,
            "externalSource": "Spoonacular" # Added to indicate the source
        }
        return {"results": search_results_public, "pagination": pagination_meta}

    async def import_recipe_from_spoonacular(self, spoonacular_id: int, user_id: UUID) -> RecipePublic:
        # Check if recipe already exists by spoonacular_id
        stmt_check = select(DBRecipe).where(DBRecipe.spoonacular_id == spoonacular_id)
        existing_recipe = self.db.execute(stmt_check).scalars().first()
        if existing_recipe:
            logger.info(f"Recipe with Spoonacular ID {spoonacular_id} (local ID {existing_recipe.id}) already exists.")
            # Return existing recipe, ensuring it's the full public model
            return await self.get_recipe_by_id(existing_recipe.id, user_id=user_id)

        client = None
        try:
            client = SpoonacularClient()
            spoonacular_recipe_data = await client.get_recipe_details(spoonacular_id, include_nutrition=True)
        except SpoonacularRateLimitException as e:
            logger.error(f"Spoonacular API rate limit for recipe {spoonacular_id}: {e}")
            raise
        except SpoonacularException as e:
            logger.error(f"Spoonacular API error for recipe {spoonacular_id}: {e}")
            raise
        except ValueError as e: # Catches API key configuration errors
            logger.error(f"SpoonacularClient config error: {e}")
            raise Exception(f"Spoonacular client configuration error: {e}") from e
        finally:
            if client:
                await client.close()

        try:
            # Map Spoonacular data to a structure suitable for RecipeCreate
            mapped_data = map_spoonacular_data_to_dict(spoonacular_recipe_data, spoonacular_id)
        except ValueError as e: # Catch specific mapping errors
            logger.error(f"Mapping error for Spoonacular recipe {spoonacular_id}: {e}")
            raise Exception(f"Error processing recipe data: {e}") from e

        # Ensure ingredients are present after mapping
        if not mapped_data.get("ingredients_data_temp"):
            # This might indicate an issue with the source data or mapping logic for this specific recipe
            logger.warning(f"Recipe {spoonacular_id} ('{mapped_data.get('title')}'): No ingredients were mapped.")
            # Depending on policy, you might raise an error or proceed without ingredients
            raise ValueError(f"Recipe {spoonacular_id} ('{mapped_data.get('title')}'): No ingredients mapped.")

        # Process ingredients: get or create local DBIngredient, then prepare RecipeIngredientLinkCreate
        recipe_ingredient_links_create: List[RecipeIngredientLinkCreate] = []
        for ing_data in mapped_data["ingredients_data_temp"]:
            try:
                ingredient_db_obj = await self._get_or_create_ingredient(
                    name=ing_data["name"],
                    category=ing_data.get("category"), # Pass category from mapped_data
                    calories_per_unit=ing_data.get("calories_per_unit") # Pass calories_per_unit
                )
                recipe_ingredient_links_create.append(
                    RecipeIngredientLinkCreate(
                        ingredient_id=ingredient_db_obj.id, # Use the ID from the DB object
                        quantity=ing_data["quantity"],
                        unit=ing_data["unit"],
                        preparation_note=ing_data.get("preparation_note") # Ensure this is optional
                    )
                )
            except Exception as e:
                # Log and re-raise or collect errors to decide if recipe import should fail
                logger.error(f"Failed to process or link ingredient '{ing_data['name']}' for Spoonacular recipe {spoonacular_id}: {e}")
                raise Exception(f"Error processing ingredient {ing_data['name']}: {e}") from e

        # If after processing, no ingredients are successfully linked (e.g., all had issues)
        if not recipe_ingredient_links_create:
             logger.warning(f"Recipe {spoonacular_id} ('{mapped_data.get('title')}'): No ingredients successfully processed/linked.")
             raise ValueError(f"Recipe {spoonacular_id} ('{mapped_data.get('title')}'): No ingredients could be successfully processed.")

        # Ensure instructions are present
        if not mapped_data.get("instructions_data"):
            logger.warning(f"Recipe {spoonacular_id} ('{mapped_data.get('title')}'): No instructions were mapped.")
            raise ValueError(f"Recipe {spoonacular_id} ('{mapped_data.get('title')}'): No instructions mapped.")

        instructions_create_list: List[InstructionStepCreate] = []
        for instr_data in mapped_data["instructions_data"]:
            instructions_create_list.append(InstructionStepCreate(**instr_data))

        if not instructions_create_list: # Should not happen if mapped_data["instructions_data"] was not empty
             logger.warning(f"Recipe {spoonacular_id} ('{mapped_data.get('title')}'): No instructions successfully processed into Pydantic models.")
             raise ValueError(f"Recipe {spoonacular_id} ('{mapped_data.get('title')}'): No instructions could be successfully processed.")

        # Create the recipe using the existing service method
        try:
            recipe_to_create = RecipeCreate(
                title=mapped_data["title"], # title is mandatory from mapper
                description=mapped_data.get("description"),
                prep_time_minutes=mapped_data.get("prep_time_minutes"),
                cook_time_minutes=mapped_data.get("cook_time_minutes"),
                servings=mapped_data.get("servings"),
                difficulty_level=mapped_data.get("difficulty_level", "medium"), # Default if not provided
                cuisine_type=mapped_data.get("cuisine_type"),
                dietary_tags=mapped_data.get("dietary_tags", []), # Default to empty list
                image_url=mapped_data.get("image_url"),
                source_url=mapped_data.get("source_url"),
                spoonacular_id=mapped_data["spoonacular_id"], # This is now part of RecipeBase and thus RecipeCreate
                calories=mapped_data.get("calories"),
                protein=mapped_data.get("protein"),
                carbohydrates=mapped_data.get("carbohydrates"),
                fat=mapped_data.get("fat"),
                instructions=instructions_create_list,
                ingredients=recipe_ingredient_links_create
            )
        except Exception as e: # Catch Pydantic validation errors or other issues
            logger.error(f"Pydantic validation error for creating RecipeCreate from Spoonacular recipe {spoonacular_id} data: {e}")
            raise Exception(f"Data validation failed for recipe {spoonacular_id}: {e}") from e

        # Use the existing create_recipe method
        try:
            # Pass user_id to create_recipe
            created_recipe_public = await self.create_recipe(recipe_in=recipe_to_create, user_id=user_id)
            logger.info(f"Successfully imported Spoonacular recipe {spoonacular_id} as local recipe ID {created_recipe_public.id}")
            return created_recipe_public
        except Exception as e:
            # Handle potential errors during recipe creation (e.g., DB issues)
            logger.error(f"Database error while saving imported Spoonacular recipe {spoonacular_id} (local title '{recipe_to_create.title}'): {e}")
            self.db.rollback() # Ensure rollback on error
            # Re-raise to inform the caller; specific error handling might be needed based on application flow
            raise Exception(f"Database error saving recipe {spoonacular_id}: {e}") from e
