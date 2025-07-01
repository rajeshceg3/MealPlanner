import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session # For type hinting and conceptual DB checks

# Assuming your FastAPI app instance is in app.main.app
# Adjust this import based on your actual project structure
# from smart_recipe_meal_planner.app.main import app
# For this subtask, we'll assume 'app' can be imported or provided by a fixture.

# Placeholder for actual database models if direct DB checks were fully implemented here
# from smart_recipe_meal_planner.app.db.models.recipe_model import Recipe as DBRecipe
# from smart_recipe_meal_planner.app.db.models.user_model import User as DBUser

from smart_recipe_meal_planner.app.clients.spoonacular_client import SpoonacularException, SpoonacularRateLimitException

# Path to the SpoonacularClient where it's instantiated in the service layer
MOCK_SPOONACULAR_CLIENT_PATH = "smart_recipe_meal_planner.app.services.recipe_service.SpoonacularClient"

# Dummy user ID for created_by_user_id checks, assuming auth provides this.
# In a real setup, auth_headers fixture would create a user and use their ID.
DUMMY_USER_ID = uuid4()

# Sample Spoonacular recipe data for mocking responses
SAMPLE_SPOONACULAR_ID = 716429
MOCK_RECIPE_DATA_VALID = {
    "id": SAMPLE_SPOONACULAR_ID,
    "title": "Pasta with Garlic, Scallions, Cauliflower & Breadcrumbs",
    "summary": "This is a <b>delicious</b> and <em>easy</em> pasta recipe. Perfect for a weeknight dinner!",
    "image": "https://spoonacular.com/recipeImages/716429-556x370.jpg",
    "sourceUrl": "http://fullbellysisters.blogspot.com/2012/06/pasta-with-garlic-scallions.html",
    "preparationMinutes": 10,
    "cookingMinutes": 20,
    "readyInMinutes": 30,
    "servings": 2,
    "cuisines": ["Italian", "Mediterranean"],
    "diets": ["lacto ovo vegetarian"],
    "extendedIngredients": [
        {
            "id": 1001,
            "aisle": "Produce",
            "name": "cauliflower",
            "nameClean": "cauliflower",
            "amount": 0.5,
            "unit": "head",
            "original": "1/2 head of cauliflower, cut into florets",
            "nutrition": {"nutrients": [{"name": "Calories", "amount": 50, "unit": "kcal"}]} # Per 0.5 head
        },
        {
            "id": 1002,
            "aisle": "Pasta and Rice",
            "name": "pasta",
            "nameClean": "pasta",
            "amount": 1.0, # Amount is 1, so calories should be mapped directly
            "unit": "serving (100g)",
            "original": "1 serving (100g) of pasta",
            "nutrition": {"nutrients": [{"name": "Calories", "amount": 350, "unit": "kcal"}]}
        }
    ],
    "analyzedInstructions": [
        {
            "name": "",
            "steps": [
                {"number": 1, "step": "Cook pasta according to package directions."},
                {"number": 2, "step": "Steam or roast cauliflower florets until tender."},
                {"number": 3, "step": "Combine all ingredients and serve."}
            ]
        }
    ],
    "nutrition": {
        "nutrients": [
            {"name": "Calories", "amount": 550.0, "unit": "kcal"},
            {"name": "Protein", "amount": 20.0, "unit": "g"},
            {"name": "Fat", "amount": 15.0, "unit": "g"},
            {"name": "Carbohydrates", "amount": 80.0, "unit": "g"}
        ]
    }
}

MOCK_RECIPE_DATA_MISSING_TITLE = {
    "id": 716430,
    # "title": "Recipe with no Title", # Title is missing
    "summary": "This recipe is missing a title, which should cause a mapping error.",
    "extendedIngredients": [{"nameClean": "test", "amount": 1, "unit": "g"}] # Minimal valid ingredient
}


# Pytest fixtures would typically be in conftest.py
# These are conceptual placeholders for what the tests would need.
@pytest.fixture(scope="module")
def client():
    # In a real setup, this would import the FastAPI app and wrap it in TestClient
    # from smart_recipe_meal_planner.app.main import app
    # with TestClient(app) as c:
    #     yield c
    # For now, returning a simple mock that can have methods like .post()
    # This won't actually run an HTTP server but allows testing the call structure.
    # A real TestClient is needed for full integration. For this subtask, we focus on test structure.
    # This placeholder will cause tests to fail if not replaced by a real TestClient.
    # For the purpose of this subtask, assume 'client' is a working TestClient.
    pass # This should be a real TestClient provided by the test environment

@pytest.fixture(scope="module")
def db_session(): # Placeholder for a test DB session
    # yield session
    pass

@pytest.fixture(scope="module")
def auth_headers(): # Placeholder for authentication headers
    # This would typically involve creating a test user and logging them in
    # For now, a dummy token. The actual API endpoint uses `CurrentUser` dependency.
    return {"Authorization": f"Bearer dummytoken-for-user-{DUMMY_USER_ID}"}


def test_import_new_recipe_success(client: TestClient, db_session: Session, auth_headers):
    """
    Test successful import of a new recipe from Spoonacular.
    """
    spoonacular_id_to_import = SAMPLE_SPOONACULAR_ID

    with patch(MOCK_SPOONACULAR_CLIENT_PATH) as MockSpoonClient:
        mock_client_instance = MockSpoonClient.return_value
        mock_client_instance.get_recipe_details = AsyncMock(return_value=MOCK_RECIPE_DATA_VALID)
        mock_client_instance.close = AsyncMock() # Important to mock if called in 'finally'

        # API call to import the recipe
        response = client.post(
            f"/api/v1/recipes/import-external/{spoonacular_id_to_import}",
            headers=auth_headers
        )

    assert response.status_code == 200, response.text
    data = response.json()

    # Verify response structure and data (RecipePublic)
    assert data["title"] == MOCK_RECIPE_DATA_VALID["title"]
    assert data["description"] == "This is a delicious and easy pasta recipe. Perfect for a weeknight dinner!" # HTML Stripped
    assert data["spoonacular_id"] == spoonacular_id_to_import
    assert data["prep_time_minutes"] == MOCK_RECIPE_DATA_VALID["preparationMinutes"]
    assert data["cook_time_minutes"] == MOCK_RECIPE_DATA_VALID["cookingMinutes"]
    assert data["servings"] == MOCK_RECIPE_DATA_VALID["servings"]
    assert data["cuisine_type"] == MOCK_RECIPE_DATA_VALID["cuisines"][0]
    assert data["calories"] == MOCK_RECIPE_DATA_VALID["nutrition"]["nutrients"][0]["amount"]
    assert len(data["instructions"]) == len(MOCK_RECIPE_DATA_VALID["analyzedInstructions"][0]["steps"])
    assert len(data["recipe_ingredients"]) == len(MOCK_RECIPE_DATA_VALID["extendedIngredients"])

    # Check ingredient details from mapping
    mapped_ingredient_1 = next(i for i in data["recipe_ingredients"] if i["ingredient"]["name"] == "cauliflower")
    assert mapped_ingredient_1["quantity"] == 0.5
    assert mapped_ingredient_1["ingredient"]["category"] == "Produce"
    # Calories for cauliflower: amount is 0.5, so calories_per_unit in DB should be None or calculated if logic existed
    # The mapper currently sets it to None if amount != 1. The service stores this None.
    # The DBIngredient.calories_per_unit is what _get_or_create_ingredient receives.
    # If this test requires checking the DBIngredient.calories_per_unit, a DB query is needed.
    # For RecipePublic, this field is not directly exposed per ingredient.

    mapped_ingredient_2 = next(i for i in data["recipe_ingredients"] if i["ingredient"]["name"] == "pasta")
    assert mapped_ingredient_2["quantity"] == 1.0
    assert mapped_ingredient_2["ingredient"]["category"] == "Pasta and Rice"
    # For pasta, amount is 1.0, so calories_per_unit (350) should have been passed to _get_or_create_ingredient.

    # Conceptual DB Verification (requires a real db_session and DBRecipe model)
    # recipe_in_db = db_session.query(DBRecipe).filter(DBRecipe.spoonacular_id == spoonacular_id_to_import).first()
    # assert recipe_in_db is not None
    # assert recipe_in_db.title == MOCK_RECIPE_DATA_VALID["title"]
    # assert recipe_in_db.created_by_user_id == DUMMY_USER_ID # Verify user assignment
    # assert len(recipe_in_db.ingredients) == 2
    # pasta_ing_db = db_session.query(DBIngredient).filter(DBIngredient.name == "pasta").first()
    # assert pasta_ing_db.calories_per_unit == 350.0


def test_import_existing_recipe_is_idempotent(client: TestClient, db_session: Session, auth_headers):
    """
    Test that importing an already existing Spoonacular recipe returns the existing one.
    """
    spoonacular_id_to_import = SAMPLE_SPOONACULAR_ID

    # Initial import (conceptual: this would populate the DB)
    # For this test, we assume a previous import has occurred and an entry exists.
    # A more robust test would actually perform the first import.
    # Here, we'll mock the service layer to simulate an existing recipe.

    # To simulate this properly, we'd need to:
    # 1. Call the import endpoint once. Get back a local recipe ID.
    # 2. Call it again. Assert the same local recipe ID is returned.
    # For now, we'll patch the service's check for existing recipe.

    # This test is more complex without a running DB and full app state.
    # The key check is that RecipeService.import_recipe_from_spoonacular
    # correctly finds an existing recipe by spoonacular_id and returns it.

    # Let's assume the first import created a recipe with local_id "some_uuid"
    # For this test, we'll directly call the endpoint twice with the same mock.
    # The service itself has the logic to check if `DBRecipe.spoonacular_id == spoonacular_id` exists.

    with patch(MOCK_SPOONACULAR_CLIENT_PATH) as MockSpoonClientFirstCall:
        mock_instance_first = MockSpoonClientFirstCall.return_value
        mock_instance_first.get_recipe_details = AsyncMock(return_value=MOCK_RECIPE_DATA_VALID)
        mock_instance_first.close = AsyncMock()

        response_first_import = client.post(
            f"/api/v1/recipes/import-external/{spoonacular_id_to_import}",
            headers=auth_headers
        )
        assert response_first_import.status_code == 200
        data_first_import = response_first_import.json()
        local_recipe_id_first = data_first_import["id"]

    # db_recipe_count_before_second_import = db_session.query(DBRecipe).count()

    with patch(MOCK_SPOONACULAR_CLIENT_PATH) as MockSpoonClientSecondCall:
        # Note: SpoonacularClient is not even called if recipe exists by spoonacular_id.
        # So, mocking get_recipe_details here is just a fallback.
        # The service short-circuits before SpoonacularClient is used if recipe exists.
        mock_instance_second = MockSpoonClientSecondCall.return_value
        mock_instance_second.get_recipe_details = AsyncMock(return_value=MOCK_RECIPE_DATA_VALID) # Should not be called ideally
        mock_instance_second.close = AsyncMock()

        response_second_import = client.post(
            f"/api/v1/recipes/import-external/{spoonacular_id_to_import}",
            headers=auth_headers
        )

    assert response_second_import.status_code == 200
    data_second_import = response_second_import.json()
    assert data_second_import["id"] == local_recipe_id_first # Should be the same local ID
    assert data_second_import["title"] == MOCK_RECIPE_DATA_VALID["title"] # And other data matches

    # db_recipe_count_after_second_import = db_session.query(DBRecipe).count()
    # assert db_recipe_count_after_second_import == db_recipe_count_before_second_import # No new recipe created


def test_import_recipe_spoonacular_api_error(client: TestClient, auth_headers):
    """
    Test error handling when Spoonacular API call fails.
    """
    spoonacular_id_to_import = 999999 # A non-existent or error-causing ID

    with patch(MOCK_SPOONACULAR_CLIENT_PATH) as MockSpoonClient:
        mock_client_instance = MockSpoonClient.return_value
        mock_client_instance.get_recipe_details = AsyncMock(side_effect=SpoonacularException("API unavailable"))
        mock_client_instance.close = AsyncMock()

        response = client.post(
            f"/api/v1/recipes/import-external/{spoonacular_id_to_import}",
            headers=auth_headers
        )

    # The RecipeService catches SpoonacularException and raises HTTPException(503)
    assert response.status_code == 503 # Service Unavailable
    assert "Spoonacular API error" in response.json()["detail"]


def test_import_recipe_spoonacular_rate_limit_error(client: TestClient, auth_headers):
    """
    Test error handling for Spoonacular API rate limit.
    """
    spoonacular_id_to_import = 999998

    with patch(MOCK_SPOONACULAR_CLIENT_PATH) as MockSpoonClient:
        mock_client_instance = MockSpoonClient.return_value
        mock_client_instance.get_recipe_details = AsyncMock(side_effect=SpoonacularRateLimitException("Rate limit exceeded"))
        mock_client_instance.close = AsyncMock()

        response = client.post(
            f"/api/v1/recipes/import-external/{spoonacular_id_to_import}",
            headers=auth_headers
        )

    # The RecipeService catches SpoonacularRateLimitException and raises HTTPException(429)
    assert response.status_code == 429 # Too Many Requests
    assert "Spoonacular API rate limit" in response.json()["detail"]


def test_import_recipe_data_mapping_error(client: TestClient, auth_headers):
    """
    Test error handling when Spoonacular data causes a mapping (ValueError) or validation error.
    """
    spoonacular_id_to_import = MOCK_RECIPE_DATA_MISSING_TITLE["id"]

    with patch(MOCK_SPOONACULAR_CLIENT_PATH) as MockSpoonClient:
        mock_client_instance = MockSpoonClient.return_value
        # Return data that will fail mapping (e.g., missing title)
        mock_client_instance.get_recipe_details = AsyncMock(return_value=MOCK_RECIPE_DATA_MISSING_TITLE)
        mock_client_instance.close = AsyncMock()

        response = client.post(
            f"/api/v1/recipes/import-external/{spoonacular_id_to_import}",
            headers=auth_headers
        )

    # RecipeService catches ValueError from map_spoonacular_data_to_dict or RecipeCreate validation
    # and raises HTTPException(422) or a general 500 if not specifically caught for validation.
    # The current service setup for import_recipe_from_spoonacular:
    # - map_spoonacular_data_to_dict raises ValueError for missing title -> caught, re-raised as generic Exception
    # - RecipeCreate could raise Pydantic's ValidationError -> caught, re-raised as generic Exception
    # - The endpoint decorator for this path catches Exception and returns 500.
    # - However, there's also specific `except ValueError as e: raise HTTPException(status_code=422, detail=str(e))`
    #   in the endpoint for `import_recipe`. The service re-raises as generic Exception,
    #   but the API route might catch it. Let's assume the service's re-raised Exception becomes a 500
    #   unless the endpoint's specific ValueError catch is hit.
    #   The `map_spoonacular_data_to_dict` raises ValueError("Spoonacular data missing 'title'.")
    #   The service catches this and logs "Mapping error...: Spoonacular data missing 'title'." then
    #   `raise Exception(f"Error processing recipe data: {e}") from e`
    #   The API endpoint (`router_recipes.py`) has:
    #   `except ValueError as e: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))`
    #   `except SpoonacularException as e: ...`
    #   `except Exception as e: raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, ...)`
    #   So, a ValueError from mapping, if re-raised as a generic Exception by the service, might become 500.
    #   If the service re-raised it as ValueError, it would be 422.
    #   Given `raise Exception(...) from e` in service, it's likely a 500.
    #   Let's refine based on current error handling in RecipeService which wraps original error.
    #   The service catches `ValueError as e` from mapping and does `raise Exception(f"Error processing recipe data: {e}")`.
    #   The API endpoint's `except ValueError` won't catch this `Exception`. It will hit the generic `except Exception`.

    # If the service `import_recipe_from_spoonacular` re-raises the mapping `ValueError` as a generic `Exception`,
    # the current API endpoint in `routers/recipes.py` would catch it with its broad `except Exception as e:`
    # block, which returns a 500.
    # If the specific `ValueError` from the mapper was to be propagated as `ValueError`
    # all the way to the router, then 422 would be correct.
    # Based on current `RecipeService` code:
    # `except ValueError as e: # Catch specific mapping errors`
    # `  logger.error(f"Mapping error for Spoonacular recipe {spoonacular_id}: {e}")`
    # `  raise Exception(f"Error processing recipe data: {e}") from e`
    # This will lead to a 500.

    assert response.status_code == 500 # Due to service wrapping ValueError into generic Exception
    # Example detail: "Internal server error. Please try again later."
    # Or, if the detail from the wrapped exception is passed:
    assert "Error processing recipe data: Spoonacular data missing 'title'." in response.json()["detail"]


# To run these tests (requires pytest and FastAPI test setup):
# Ensure conftest.py provides actual 'client', 'db_session', 'auth_headers' fixtures.
# pytest app/tests/api/v1/test_recipes_integration.py
