from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from pydantic import BaseModel, HttpUrl

from app.services.recipe_service import RecipeService
from app.api.v1.dependencies import get_recipe_service, get_current_active_user
from app.models.recipe_schemas import RecipePublic
from app.db.models.user_model import User as DBUser
from app.clients.spoonacular_client import SpoonacularException, SpoonacularRateLimitException
import logging # Added for logging

router = APIRouter()
logger = logging.getLogger(__name__) # Added logger

class ExternalRecipeSummary(BaseModel):
    spoonacular_id: int
    title: str
    image_url: Optional[HttpUrl] = None
    source_url: Optional[HttpUrl] = None
    ready_in_minutes: Optional[int] = None
    servings: Optional[int] = None

class ExternalRecipeSearchResponse(BaseModel):
    results: List[ExternalRecipeSummary]
    pagination: Dict[str, Any]

@router.get(
    "/search",
    response_model=ExternalRecipeSearchResponse,
    summary="Search for recipes on Spoonacular"
)
async def search_external_recipes_api(
    query: str,
    page: int = Query(1, ge=1, description="Page number to retrieve."),
    limit: int = Query(10, ge=1, le=100, description="Number of results per page."),
    recipe_service: RecipeService = Depends(get_recipe_service)
):
    """
    Search for recipes from the Spoonacular API.
    """
    try:
        search_results = await recipe_service.search_external_recipes(query=query, page=page, limit=limit)

        # Pydantic V2 should handle URL conversion if types are correct in source dict.
        # If image_url/source_url from service are already valid HttpUrl strings or None, this is fine.
        # If they are some other type that Pydantic can't coerce, pre-validation might be needed.
        # The current structure of search_external_recipes in RecipeService seems to return dicts
        # with string URLs, which Pydantic should handle.
        # Example pre-validation if needed (but likely not with current service output):
        # validated_results = []
        # for item in search_results.get("results", []):
        #     if item.get("image_url") and not isinstance(item["image_url"], (str, HttpUrl)):
        #         item["image_url"] = str(item["image_url"])
        #     if item.get("source_url") and not isinstance(item["source_url"], (str, HttpUrl)):
        #         item["source_url"] = str(item["source_url"])
        #     validated_results.append(item)
        # search_results["results"] = validated_results

        return search_results
    except SpoonacularRateLimitException as e:
        logger.warning(f"Spoonacular API rate limit hit during external search for query '{query}': {e}")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"External API rate limit exceeded. Please try again later.")
    except SpoonacularException as e:
        logger.error(f"Spoonacular API error during external search for query '{query}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"External API error. Please try again later.")
    except Exception as e:
        logger.error(f"Unexpected error during external recipe search for query '{query}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred.")

@router.post(
    "/import/{spoonacular_id}",
    response_model=RecipePublic,
    summary="Import a recipe from Spoonacular by its ID"
)
async def import_spoonacular_recipe_api(
    spoonacular_id: int = Path(..., ge=1, description="The Spoonacular ID of the recipe to import."),
    recipe_service: RecipeService = Depends(get_recipe_service),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Import a recipe from Spoonacular using its ID.
    The recipe will be saved to the local database.
    If the recipe already exists locally (based on spoonacular_id), the existing local version is returned.
    """
    try:
        imported_recipe = await recipe_service.import_recipe_from_spoonacular(
            spoonacular_id=spoonacular_id,
            user_id=current_user.id
        )
        return imported_recipe
    except SpoonacularRateLimitException as e:
        logger.warning(f"Spoonacular API rate limit hit during import for ID {spoonacular_id}: {e}")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"External API rate limit exceeded. Please try again later.")
    except SpoonacularException as e:
        logger.error(f"Spoonacular API error during import for ID {spoonacular_id}: {e}", exc_info=True)
        # Check if it's a "not found" type of error from the client's message
        if "not found" in str(e).lower() or (hasattr(e, 'response') and e.response and e.response.status_code == 404):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recipe {spoonacular_id} not found on Spoonacular.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"External API error. Please try again later.")
    except ValueError as e:
        logger.warning(f"Validation error during import of recipe {spoonacular_id}: {e}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error importing recipe {spoonacular_id}: {e}", exc_info=True)
        if "Spoonacular client configuration error" in str(e):
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="External API client configuration error.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred.")
