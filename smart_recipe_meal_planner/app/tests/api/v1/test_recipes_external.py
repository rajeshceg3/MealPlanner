import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid
from datetime import datetime

from fastapi import FastAPI, status, HTTPException
from fastapi.testclient import TestClient

from app.main import app  # Main FastAPI application
from app.models.recipe_schemas import (
    RecipePublic,
    PaginatedExternalRecipeSearchResponse,
    ExternalRecipeSearchResultItem,
    InstructionStepPublic, # Added for RecipePublic
    IngredientUsagePublic, # Added for RecipePublic
)
from app.services.recipe_service import RecipeService
from app.clients.spoonacular_client import SpoonacularRateLimitException, SpoonacularException
from app.api.v1.dependencies import get_recipe_service, get_current_active_user
from app.db.models.user_model import User as DBUser # For mock user type hint

# Mock User Model for testing
class MockUser(DBUser):
    id: uuid.UUID = uuid.uuid4()
    email: str = "testuser@example.com"
    is_active: bool = True
    is_superuser: bool = False
    username: str = "testuser"


@pytest.fixture
def mock_recipe_service() -> AsyncMock:
    """Provides an AsyncMock instance of RecipeService."""
    return AsyncMock(spec=RecipeService)

@pytest.fixture
def mock_current_active_user() -> MockUser:
    """Provides a mock active user."""
    return MockUser()

@pytest.fixture
def client(
    mock_recipe_service: AsyncMock,
    mock_current_active_user: MockUser
) -> TestClient:
    """Provides a TestClient with overridden dependencies."""
    app.dependency_overrides[get_recipe_service] = lambda: mock_recipe_service
    app.dependency_overrides[get_current_active_user] = lambda: mock_current_active_user
    return TestClient(app)

# Base API URL prefix
API_V1_STR = "/api/v1/recipes"

# Tests for GET /search-external
# ==============================

def test_search_external_recipes_success(client: TestClient, mock_recipe_service: AsyncMock, mock_current_active_user: MockUser):
    """Test successful search for external recipes."""
    mock_search_results = [
        ExternalRecipeSearchResultItem(spoonacular_id=1, title="Test Recipe 1", image_url="http://example.com/img1.jpg", ready_in_minutes=30, servings=4),
        ExternalRecipeSearchResultItem(spoonacular_id=2, title="Test Recipe 2", source_url="http://example.com/recipe2", ready_in_minutes=45, servings=2),
    ]
    mock_pagination = {"currentPage": 1, "totalPages": 1, "totalItems": 2, "hasNext": False, "hasPrevious": False}
    mock_recipe_service.search_external_recipes.return_value = {
        "results": mock_search_results,
        "pagination": mock_pagination,
    }

    response = client.get(f"{API_V1_STR}/search-external", params={"query": "pasta", "page": 1, "limit": 10})

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["success"] is True
    assert len(json_response["data"]) == 2
    assert json_response["data"][0]["title"] == "Test Recipe 1"
    assert json_response["pagination"] == mock_pagination

    mock_recipe_service.search_external_recipes.assert_called_once_with(query="pasta", page=1, limit=10)

def test_search_external_recipes_auth_error(client: TestClient, mock_recipe_service: AsyncMock):
    """Test search external recipes with simulated authentication error."""
    # Override get_current_active_user for this specific test
    app.dependency_overrides[get_current_active_user] = lambda: (_ for _ in ()).throw(HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"))

    response = client.get(f"{API_V1_STR}/search-external", params={"query": "pasta"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Clean up the override
    del app.dependency_overrides[get_current_active_user]

def test_search_external_recipes_rate_limit_error(client: TestClient, mock_recipe_service: AsyncMock):
    """Test search external recipes when Spoonacular rate limit is hit."""
    mock_recipe_service.search_external_recipes.side_effect = SpoonacularRateLimitException("Rate limit exceeded")

    response = client.get(f"{API_V1_STR}/search-external", params={"query": "pizza"})

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Rate limit exceeded" in response.json()["detail"]

def test_search_external_recipes_spoonacular_error(client: TestClient, mock_recipe_service: AsyncMock):
    """Test search external recipes when there's a general Spoonacular API error."""
    mock_recipe_service.search_external_recipes.side_effect = SpoonacularException("Spoonacular service error")

    response = client.get(f"{API_V1_STR}/search-external", params={"query": "salad"})

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Spoonacular service error" in response.json()["detail"]

def test_search_external_recipes_generic_error(client: TestClient, mock_recipe_service: AsyncMock):
    """Test search external recipes with an unexpected generic server error."""
    mock_recipe_service.search_external_recipes.side_effect = Exception("Some generic error")

    response = client.get(f"{API_V1_STR}/search-external", params={"query": "soup"})

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "An error occurred while searching external recipes." in response.json()["detail"]

def test_search_external_recipes_validation_error(client: TestClient):
    """Test search external recipes with invalid query parameters (query too short)."""
    response = client.get(f"{API_V1_STR}/search-external", params={"query": "s"}) # query < 3 chars

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# Tests for POST /import-external/{spoonacular_id}
# ===============================================

SAMPLE_RECIPE_ID = uuid.uuid4()
MOCK_USER_ID = uuid.uuid4() # Re-use mock_current_active_user.id if possible

@pytest.fixture
def mock_current_active_user_with_id() -> MockUser:
    """Provides a mock active user with a fixed ID for import tests."""
    return MockUser(id=MOCK_USER_ID)

@pytest.fixture # Re-define client for import tests to use user with fixed ID
def client_for_import(
    mock_recipe_service: AsyncMock,
    mock_current_active_user_with_id: MockUser # Use the user with fixed ID
) -> TestClient:
    """Provides a TestClient with overridden dependencies for import tests."""
    app.dependency_overrides[get_recipe_service] = lambda: mock_recipe_service
    app.dependency_overrides[get_current_active_user] = lambda: mock_current_active_user_with_id
    client = TestClient(app)
    yield client # Use yield to allow for cleanup
    # Clean up overrides after test
    del app.dependency_overrides[get_recipe_service]
    del app.dependency_overrides[get_current_active_user]


def test_import_external_recipe_success(client_for_import: TestClient, mock_recipe_service: AsyncMock, mock_current_active_user_with_id: MockUser):
    """Test successful import of an external recipe."""
    spoonacular_id_to_import = 12345

    # Ensure mock user ID is available
    user_id_for_call = mock_current_active_user_with_id.id

    mock_imported_recipe = RecipePublic(
        id=SAMPLE_RECIPE_ID,
        title="Imported Recipe",
        description="A delicious recipe imported from Spoonacular.",
        prep_time_minutes=20,
        cook_time_minutes=40,
        servings=4,
        difficulty_level="easy",
        cuisine_type="italian",
        image_url="http://example.com/imported.jpg",
        source_url=f"https://spoonacular.com/recipes/imported-recipe-{spoonacular_id_to_import}",
        spoonacular_id=spoonacular_id_to_import,
        created_by_user_id=user_id_for_call,
        average_rating=0.0,
        rating_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        instructions=[InstructionStepPublic(id=uuid.uuid4(), step_number=1, instruction="Do this", recipe_id=SAMPLE_RECIPE_ID)],
        recipe_ingredients=[IngredientUsagePublic(
            ingredient_id=uuid.uuid4(),
            name="Test Ingredient",
            quantity=1,
            unit="cup",
            recipe_id=SAMPLE_RECIPE_ID, # Added for completeness
            category="testing" # Added for completeness
            )]
    )
    mock_recipe_service.import_recipe_from_spoonacular.return_value = mock_imported_recipe

    response = client_for_import.post(f"{API_V1_STR}/import-external/{spoonacular_id_to_import}")

    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert json_response["title"] == "Imported Recipe"
    assert json_response["spoonacular_id"] == spoonacular_id_to_import
    assert uuid.UUID(json_response["created_by_user_id"]) == user_id_for_call # Compare UUID objects

    mock_recipe_service.import_recipe_from_spoonacular.assert_called_once_with(
        spoonacular_id=spoonacular_id_to_import, user_id=user_id_for_call
    )

def test_import_external_recipe_auth_error(client: TestClient, mock_recipe_service: AsyncMock): # Use original client
    """Test import external recipe with simulated authentication error."""
    app.dependency_overrides[get_current_active_user] = lambda: (_ for _ in ()).throw(HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"))

    response = client.post(f"{API_V1_STR}/import-external/67890")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    del app.dependency_overrides[get_current_active_user]

def test_import_external_recipe_rate_limit_error(client_for_import: TestClient, mock_recipe_service: AsyncMock):
    """Test import external recipe when Spoonacular rate limit is hit."""
    mock_recipe_service.import_recipe_from_spoonacular.side_effect = SpoonacularRateLimitException("Rate limit exceeded on import")

    response = client_for_import.post(f"{API_V1_STR}/import-external/11122")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Rate limit exceeded on import" in response.json()["detail"]

def test_import_external_recipe_spoonacular_error(client_for_import: TestClient, mock_recipe_service: AsyncMock):
    """Test import external recipe when Spoonacular API returns an error (e.g., recipe not found)."""
    mock_recipe_service.import_recipe_from_spoonacular.side_effect = SpoonacularException("Recipe not found on Spoonacular")

    response = client_for_import.post(f"{API_V1_STR}/import-external/33445")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Recipe not found on Spoonacular" in response.json()["detail"]

def test_import_external_recipe_mapping_error(client_for_import: TestClient, mock_recipe_service: AsyncMock):
    """Test import external recipe when there's a data mapping or validation error."""
    mock_recipe_service.import_recipe_from_spoonacular.side_effect = ValueError("Data mapping failed for recipe")

    response = client_for_import.post(f"{API_V1_STR}/import-external/55667")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Data mapping failed for recipe" in response.json()["detail"]

def test_import_external_recipe_generic_error(client_for_import: TestClient, mock_recipe_service: AsyncMock):
    """Test import external recipe with an unexpected generic server error."""
    mock_recipe_service.import_recipe_from_spoonacular.side_effect = Exception("Unexpected server issue")

    response = client_for_import.post(f"{API_V1_STR}/import-external/77889")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "An error occurred while importing the recipe." in response.json()["detail"]

def test_import_external_recipe_invalid_id(client_for_import: TestClient):
    """Test import external recipe with an invalid Spoonacular ID (e.g., 0)."""
    # The Path(..., ge=1) should catch this
    response = client_for_import.post(f"{API_V1_STR}/import-external/0")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# Cleanup dependency overrides after all tests in this module are done
@pytest.fixture(scope="module", autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()
