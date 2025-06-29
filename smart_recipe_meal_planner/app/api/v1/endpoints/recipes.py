from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from uuid import UUID

from app.models.recipe_schemas import (
    RecipeCreate,
    RecipePublic,
    PaginatedRecipeResponse,
    RecipeUpdate,
    PaginatedExternalRecipeSearchResponse, # Added import
)
from app.services.recipe_service import RecipeService
# Corrected import path for Spoonacular exceptions
from app.clients.spoonacular_client import SpoonacularRateLimitException, SpoonacularException
from app.api.v1.dependencies import get_recipe_service, get_current_active_user
from app.db.models.user_model import User as DBUser

router = APIRouter()


@router.post("/", response_model=RecipePublic, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    recipe_in: RecipeCreate,
    recipe_service: RecipeService = Depends(get_recipe_service),
    current_user: DBUser = Depends(get_current_active_user),
):
    """
    Create new recipe.
    """
    try:
        recipe = await recipe_service.create_recipe(recipe_in=recipe_in, user_id=current_user.id)
        return recipe
    except Exception as e:
        # More specific error handling can be added here if the service method
        # raises specific exceptions that need to be mapped to different HTTP status codes.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the recipe.",
        ) from e


@router.get("/", response_model=PaginatedRecipeResponse)
async def list_recipes(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    recipe_service: RecipeService = Depends(get_recipe_service),
):
    """
    List recipes with pagination.
    """
    try:
        recipes_list, pagination_meta = await recipe_service.get_recipes_list(page=page, limit=limit)
        return PaginatedRecipeResponse(data=recipes_list, pagination=pagination_meta)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing recipes.",
        ) from e


@router.get("/{recipe_id}", response_model=RecipePublic)
async def get_recipe(
    recipe_id: UUID,
    recipe_service: RecipeService = Depends(get_recipe_service),
):
    """
    Get a specific recipe by its ID.
    """
    try:
        recipe = await recipe_service.get_recipe_by_id(recipe_id=recipe_id)
        if recipe is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found",
            )
        return recipe
    except HTTPException as http_exc:
        # Re-raise HTTPException to ensure FastAPI handles it correctly
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the recipe.",
        ) from e


@router.put("/{recipe_id}", response_model=RecipePublic)
async def update_recipe_endpoint(
    recipe_id: UUID,
    recipe_in: RecipeUpdate,
    recipe_service: RecipeService = Depends(get_recipe_service),
    current_user: DBUser = Depends(get_current_active_user),
):
    """
    Update a specific recipe.
    """
    try:
        # First, check if the recipe exists
        existing_recipe = await recipe_service.get_recipe_by_id(recipe_id=recipe_id)
        if existing_recipe is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found",
            )

        # If it exists, attempt to update it
        updated_recipe = await recipe_service.update_recipe(
            recipe_id=recipe_id, recipe_in=recipe_in, user_id=current_user.id
        )

        if updated_recipe is None:
            # If update_recipe returns None, and we know the recipe exists,
            # it means the user is not authorized.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this recipe",
            )
        return updated_recipe
    except HTTPException as http_exc:
        # Re-raise HTTPException to ensure FastAPI handles it correctly
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the recipe.",
        ) from e


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe_endpoint(
    recipe_id: UUID,
    recipe_service: RecipeService = Depends(get_recipe_service),
    current_user: DBUser = Depends(get_current_active_user),
):
    """
    Delete a specific recipe.
    """
    try:
        # First, check if the recipe exists
        existing_recipe = await recipe_service.get_recipe_by_id(recipe_id=recipe_id)
        if existing_recipe is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found",
            )

        # If it exists, attempt to delete it
        deleted_successfully = await recipe_service.delete_recipe(
            recipe_id=recipe_id, user_id=current_user.id
        )

        if not deleted_successfully:
            # If delete_recipe returns False, and we know the recipe exists,
            # it means the user is not authorized.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this recipe",
            )
        # If deletion was successful, FastAPI will return a 204 No Content response
        # because of the status_code in the decorator and no return value.
        return
    except HTTPException as http_exc:
        # Re-raise HTTPException to ensure FastAPI handles it correctly
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the recipe.",
        ) from e


@router.get("/search-external", response_model=PaginatedExternalRecipeSearchResponse, summary="Search Recipes from External Source (Spoonacular)", description="Searches for recipes on Spoonacular based on a query string. Requires authentication.")
async def search_external_recipes(
    query: str = Query(..., min_length=3, description="Search query for recipes"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=30, description="Number of results per page"),
    recipe_service: RecipeService = Depends(get_recipe_service),
    current_user: DBUser = Depends(get_current_active_user), # Added dependency
):
    """
    Search recipes from Spoonacular.
    """
    try:
        results = await recipe_service.search_external_recipes(query=query, page=page, limit=limit)
        # The service returns a dict with 'results' and 'pagination' keys
        # which maps to 'data' and 'pagination' in PaginatedExternalRecipeSearchResponse
        return PaginatedExternalRecipeSearchResponse(data=results.get("results", []), pagination=results.get("pagination", {}))
    except SpoonacularRateLimitException as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except SpoonacularException as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        # Log the exception e for debugging
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while searching external recipes.")


@router.post("/import-external/{spoonacular_id}", response_model=RecipePublic, status_code=status.HTTP_200_OK, summary="Import Recipe from External Source (Spoonacular)", description="Imports a recipe from Spoonacular using its ID and saves it to the local database. If the recipe already exists locally (based on Spoonacular ID), it returns the existing local recipe. Requires authentication.")
async def import_external_recipe(
    spoonacular_id: int = Path(..., ge=1, description="Spoonacular recipe ID"),
    recipe_service: RecipeService = Depends(get_recipe_service),
    current_user: DBUser = Depends(get_current_active_user),
):
    """
    Import a recipe from Spoonacular by its ID.
    """
    try:
        recipe = await recipe_service.import_recipe_from_spoonacular(
            spoonacular_id=spoonacular_id, user_id=current_user.id
        )
        # The service method is expected to return a RecipePublic object (new or existing)
        # or raise an exception.
        return recipe
    except SpoonacularRateLimitException as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except SpoonacularException as e: # Covers issues like recipe not found on Spoonacular or API errors
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except ValueError as e: # For data mapping issues or if recipe structure is not as expected
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        # Log the exception e for debugging
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while importing the recipe.")
