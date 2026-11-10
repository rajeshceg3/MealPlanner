import pytest
import uuid
from unittest.mock import MagicMock

from fastapi import FastAPI, status
from fastapi.testclient import TestClient

# Adjust imports based on your project structure
from app.api.v1.endpoints.recipes import router as recipes_router
from app.models.recipe_schemas import RecipeCreate, RecipePublic, RecipeUpdate, PaginatedRecipeResponse


def PaginationMeta(**kwargs):
    """The recipe service returns pagination as a plain dict (Tuple[List[RecipePublic], Dict[str, Any]])."""
    return dict(kwargs)
from app.services.recipe_service import RecipeService
from app.api.v1.dependencies import get_current_active_user, get_recipe_service
from app.db.models.user_model import User as DBUser


# Fixture to set up the test client with mocked dependencies
@pytest.fixture
def client_and_mock_service():
    # Create a minimal FastAPI app for testing
    test_app = FastAPI()
    test_app.include_router(recipes_router, prefix="/api/v1/recipes")

    # Mock user
    mock_user_id = uuid.uuid4()
    mock_user = DBUser(
        id=mock_user_id,
        email="test@example.com",
        is_active=True,

        hashed_password="mockpassword" # Not used by endpoint, but good for model completeness
    )

    def override_get_current_active_user():
        return mock_user

    # Mock recipe service
    mock_recipe_service_instance = MagicMock(spec=RecipeService)

    def override_get_recipe_service():
        return mock_recipe_service_instance

    # Apply overrides
    test_app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    test_app.dependency_overrides[get_recipe_service] = override_get_recipe_service

    client = TestClient(test_app)
    yield client, mock_recipe_service_instance, mock_user_id # Yield mock_user_id for convenience in tests

    # Clear overrides after tests
    test_app.dependency_overrides.clear()


# --- Test Cases ---

# Helper to create a sample RecipePublic (can be expanded or moved to a conftest.py)
def create_sample_recipe_public(recipe_id=None, user_id=None, title="Test Recipe", **overrides):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    payload = dict(
        id=recipe_id or uuid.uuid4(),
        title=title,
        description="A delicious test recipe",
        instructions=[{"step_number": 1, "instruction": "Mix and bake."}],
        prep_time_minutes=10,
        cook_time_minutes=30,
        difficulty_level="Easy",
        calories=300.0,
        created_by_user_id=user_id or uuid.uuid4(),
        dietary_tags=["test", "easy"],
        image_url="http://example.com/image.jpg",
        created_at=now,
        updated_at=now,
    )
    payload.update(overrides)
    return RecipePublic(**payload)

# --- Create Recipe Tests ---
def test_create_recipe_success(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()
    recipe_create_data = {
        "title": "New Test Recipe",
        "description": "A fresh recipe for testing",
        "ingredients": [{"ingredient_id": str(uuid.uuid4()), "quantity": 2, "unit": "pcs"}],
        "instructions": [{"step_number": 1, "instruction": "Follow these new instructions."}],
        "cook_time_minutes": 45,
        "difficulty_level": "Medium",
        "dietary_tags": ["new", "test"]
    }

    # Configure mock service
    expected_recipe_public = create_sample_recipe_public(
        recipe_id=recipe_id,
        user_id=current_user_id,
        title=recipe_create_data["title"]
    )
    mock_service.create_recipe.return_value = expected_recipe_public

    response = client.post("/api/v1/recipes/", json=recipe_create_data)

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["title"] == recipe_create_data["title"]
    assert response_data["id"] == str(recipe_id)
    assert response_data["created_by_user_id"] == str(current_user_id)

    mock_service.create_recipe.assert_called_once()
    # More detailed argument checking if necessary:
    # call_args = mock_service.create_recipe.call_args[1] # keyword args
    # assert call_args['recipe_in'].title == recipe_create_data["title"]
    # assert call_args['user_id'] == current_user_id


def test_create_recipe_invalid_input(client_and_mock_service):
    client, _, _ = client_and_mock_service
    # Missing 'title' which is required
    invalid_recipe_data = {
        "description": "A recipe missing a title",
        "ingredients": [{"name": "Ingredient", "quantity": "1", "unit": "cup"}],
        "instructions": [{"step_number": 1, "instruction": "Some instructions."}],
        "cooking_time_minutes": 30,
        "difficulty": "Easy"
    }
    response = client.post("/api/v1/recipes/", json=invalid_recipe_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# --- Get Recipe by ID Tests ---
def test_get_recipe_success(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_id = uuid.uuid4()
    user_id = uuid.uuid4()

    expected_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=user_id)
    mock_service.get_recipe_by_id.return_value = expected_recipe

    response = client.get(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == str(recipe_id)
    assert response_data["title"] == expected_recipe.title
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)


def test_get_recipe_not_found(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_id = uuid.uuid4()
    mock_service.get_recipe_by_id.return_value = None

    response = client.get(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)

# --- List Recipes Tests ---
def test_list_recipes_success(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe1 = create_sample_recipe_public(title="Recipe Alpha")
    recipe2 = create_sample_recipe_public(title="Recipe Beta")

    recipes_list = [recipe1, recipe2]
    pagination_meta = PaginationMeta(
        total_items=2,
        total_pages=1,
        current_page=1,
        limit=10
    )
    mock_service.get_recipes_list.return_value = (recipes_list, pagination_meta)

    response = client.get("/api/v1/recipes/?page=1&limit=10")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data["data"]) == 2
    assert response_data["data"][0]["title"] == "Recipe Alpha"
    assert response_data["data"][1]["title"] == "Recipe Beta"
    assert response_data["pagination"]["total_items"] == 2
    assert response_data["pagination"]["current_page"] == 1

    mock_service.get_recipes_list.assert_called_once_with(page=1, limit=10)

# --- Update Recipe Tests ---
def test_update_recipe_success(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()

    update_data = RecipeUpdate(title="Updated Title", description="Updated description")

    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=current_user_id, title="Old Title")
    updated_recipe_public = create_sample_recipe_public(
        recipe_id=recipe_id,
        user_id=current_user_id,
        title=update_data.title,
        # description=update_data.description # Assuming the service would merge and return this
    )
    # Ensure description is part of the returned model if RecipeUpdate includes it
    if update_data.description:
        updated_recipe_public.description = update_data.description


    mock_service.get_recipe_by_id.return_value = existing_recipe # For the initial check
    mock_service.update_recipe.return_value = updated_recipe_public

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_data.model_dump(exclude_unset=True))

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["title"] == "Updated Title"
    assert response_data["id"] == str(recipe_id)

    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.update_recipe.assert_called_once()
    # call_args = mock_service.update_recipe.call_args[1]
    # assert call_args['recipe_id'] == recipe_id
    # assert call_args['recipe_in'].title == update_data.title
    # assert call_args['user_id'] == current_user_id


def test_update_recipe_not_found(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_id = uuid.uuid4()
    update_data = {"title": "Won't Update"}

    mock_service.get_recipe_by_id.return_value = None # Recipe doesn't exist

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.update_recipe.assert_not_called()


def test_update_recipe_forbidden(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()
    other_user_id = uuid.uuid4() # Recipe belongs to someone else
    update_data = RecipeUpdate(title="Attempted Update")

    # Recipe exists, but belongs to another user or update fails for auth reasons
    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=other_user_id)

    mock_service.get_recipe_by_id.return_value = existing_recipe
    mock_service.update_recipe.return_value = None # Service indicates auth failure

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_data.model_dump(exclude_unset=True))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.update_recipe.assert_called_once()


# --- Delete Recipe Tests ---
def test_delete_recipe_success(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()

    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=current_user_id)
    mock_service.get_recipe_by_id.return_value = existing_recipe # For the initial check
    mock_service.delete_recipe.return_value = True # Deletion successful

    response = client.delete(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.delete_recipe.assert_called_once_with(recipe_id=recipe_id, user_id=current_user_id)


def test_delete_recipe_not_found(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_id = uuid.uuid4()

    mock_service.get_recipe_by_id.return_value = None # Recipe doesn't exist

    response = client.delete(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.delete_recipe.assert_not_called()


def test_delete_recipe_forbidden(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=other_user_id)
    mock_service.get_recipe_by_id.return_value = existing_recipe # Recipe exists
    mock_service.delete_recipe.return_value = False # Deletion fails (auth)

    response = client.delete(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.delete_recipe.assert_called_once_with(recipe_id=recipe_id, user_id=current_user_id)

# Example of a more detailed check for create_recipe arguments
def test_create_recipe_detailed_arg_check(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()
    recipe_create_payload = RecipeCreate(
        title="Detailed Check Recipe",
        description="Description for detailed check.",
        ingredients=[{"ingredient_id": uuid.uuid4(), "quantity": 1, "unit": "item"}],
        instructions=[{"step_number": 1, "instruction": "Detailed instructions."}],
        cook_time_minutes=60,
        difficulty_level="Hard",
        dietary_tags=["detail", "check"],
        calories=500.0,
        image_url="http://example.com/detailed.jpg"
    )

    expected_recipe_public = create_sample_recipe_public(
        recipe_id=recipe_id,
        user_id=current_user_id,
        title=recipe_create_payload.title,
    )
    mock_service.create_recipe.return_value = expected_recipe_public

    response = client.post("/api/v1/recipes/", json=recipe_create_payload.model_dump(mode="json"))

    assert response.status_code == status.HTTP_201_CREATED

    mock_service.create_recipe.assert_called_once()
    args, kwargs = mock_service.create_recipe.call_args

    # Check the RecipeCreate model passed to the service
    assert isinstance(kwargs['recipe_in'], RecipeCreate)
    assert kwargs['recipe_in'].title == recipe_create_payload.title
    assert kwargs['recipe_in'].description == recipe_create_payload.description
    assert kwargs['recipe_in'].ingredients[0].ingredient_id == recipe_create_payload.ingredients[0].ingredient_id

    # Check the user_id passed to the service
    assert kwargs['user_id'] == current_user_id

    response_data = response.json()
    assert response_data["title"] == recipe_create_payload.title
    assert response_data["id"] == str(recipe_id)
    assert response_data["created_by_user_id"] == str(current_user_id)

# (Add more tests as needed, e.g., for pagination parameters in list_recipes)
def test_list_recipes_pagination_params(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service

    recipes_list = [create_sample_recipe_public()]
    pagination_meta = PaginationMeta(total_items=1, total_pages=1, current_page=5, limit=50)
    mock_service.get_recipes_list.return_value = (recipes_list, pagination_meta)

    response = client.get("/api/v1/recipes/?page=5&limit=50")

    assert response.status_code == status.HTTP_200_OK
    mock_service.get_recipes_list.assert_called_once_with(page=5, limit=50)
    response_data = response.json()
    assert response_data["pagination"]["current_page"] == 5
    assert response_data["pagination"]["limit"] == 50

# Test for optional fields in RecipeCreate (e.g. nutritional_info, image_url)
def test_create_recipe_with_optional_fields(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()
    recipe_create_data = {
        "title": "Recipe With Opts",
        "description": "Desc for opts",
        "ingredients": [{"ingredient_id": str(uuid.uuid4()), "quantity": 1, "unit": "g"}],
        "instructions": [{"step_number": 1, "instruction": "Opt instructions."}],
        "cook_time_minutes": 20,
        "difficulty_level": "Easy",
        "calories": 100.0,
        "protein": 10.0, # Optional
        "image_url": "http://example.com/optional.jpg", # Optional
        "dietary_tags": ["optional"]
    }

    expected_recipe_public = create_sample_recipe_public(
        recipe_id=recipe_id,
        user_id=current_user_id,
        title=recipe_create_data["title"],
        description=recipe_create_data["description"],
        cook_time_minutes=recipe_create_data["cook_time_minutes"],
        difficulty_level=recipe_create_data["difficulty_level"],
        calories=recipe_create_data["calories"],
        protein=recipe_create_data["protein"],
        image_url=recipe_create_data["image_url"],
        dietary_tags=recipe_create_data["dietary_tags"],
    )
    mock_service.create_recipe.return_value = expected_recipe_public

    response = client.post("/api/v1/recipes/", json=recipe_create_data)

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["title"] == recipe_create_data["title"]
    assert response_data["protein"] == 10.0
    assert response_data["image_url"] == recipe_create_data["image_url"]

    mock_service.create_recipe.assert_called_once()
    call_args = mock_service.create_recipe.call_args[1]
    assert call_args['recipe_in'].protein == recipe_create_data["protein"]
    assert str(call_args['recipe_in'].image_url) == recipe_create_data["image_url"]

# Test for update with partial data
def test_update_recipe_partial_data(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()

    # Only updating description and tags
    update_data = RecipeUpdate(description="New partial description", dietary_tags=["partial", "update"])

    existing_recipe = create_sample_recipe_public(
        recipe_id=recipe_id,
        user_id=current_user_id,
        title="Original Title for Partial Update",
        description="Old description",
        dietary_tags=["old_tag"]
    )
    # The updated recipe would retain old title, but have new description and tags
    updated_recipe_public = create_sample_recipe_public(
        recipe_id=recipe_id,
        user_id=current_user_id,
        title=existing_recipe.title, # Title remains the same
        description=update_data.description, # Description is updated
        dietary_tags=update_data.dietary_tags # Tags are updated
    )

    mock_service.get_recipe_by_id.return_value = existing_recipe
    mock_service.update_recipe.return_value = updated_recipe_public

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_data.model_dump(exclude_unset=True))

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["title"] == existing_recipe.title # Title should not have changed
    assert response_data["description"] == "New partial description"
    assert "partial" in response_data["dietary_tags"]

    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.update_recipe.assert_called_once()
    call_args = mock_service.update_recipe.call_args[1]
    assert call_args['recipe_in'].title is None # Title was not part of the update payload
    assert call_args['recipe_in'].description == update_data.description
    assert call_args['recipe_in'].dietary_tags == update_data.dietary_tags
    assert call_args['user_id'] == current_user_id
    assert call_args['recipe_id'] == recipe_id

# Test for server error during create
def test_create_recipe_server_error(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_create_data = {"title": "Error Recipe", "description": "...", "ingredients": [{"ingredient_id": str(uuid.uuid4()), "quantity": 1, "unit": "x"}], "instructions": [{"step_number": 1, "instruction": "Do something."}], "cook_time_minutes": 1, "difficulty_level": "Easy"}

    mock_service.create_recipe.side_effect = Exception("Database connection failed")

    response = client.post("/api/v1/recipes/", json=recipe_create_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error occurred" in response.json()["detail"].lower()

# Test for server error during get
def test_get_recipe_server_error(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_id = uuid.uuid4()

    mock_service.get_recipe_by_id.side_effect = Exception("Database query failed")

    response = client.get(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error occurred" in response.json()["detail"].lower()

# Test for server error during list
def test_list_recipes_server_error(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service

    mock_service.get_recipes_list.side_effect = Exception("Database query failed")

    response = client.get("/api/v1/recipes/?page=1&limit=10")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error occurred" in response.json()["detail"].lower()

# Test for server error during update
def test_update_recipe_server_error(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()
    update_data = {"title": "Error Update"}

    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=current_user_id)
    mock_service.get_recipe_by_id.return_value = existing_recipe # First check passes
    mock_service.update_recipe.side_effect = Exception("Database update failed")

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error occurred" in response.json()["detail"].lower()

# Test for server error during delete
def test_delete_recipe_server_error(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()

    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=current_user_id)
    mock_service.get_recipe_by_id.return_value = existing_recipe # First check passes
    mock_service.delete_recipe.side_effect = Exception("Database delete failed")

    response = client.delete(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error occurred" in response.json()["detail"].lower()

# Ensure the directory structure is created by the tool if it doesn't exist.
# The tool automatically handles directory creation for `create_file_with_block`.
# No explicit directory creation command is needed here.
# Final check: ensure all models are correctly imported and used.
# RecipeCreate, RecipePublic, RecipeUpdate, PaginatedRecipeResponse, PaginationMeta
# DBUser (as User)
# Make sure paths in imports like `from app.main import app` are correct.
# Here, we are not using `app.main` but constructing a minimal app with the router directly.
# `from app.api.v1.endpoints.recipes import router as recipes_router` - this is correct for this setup.
# `from app.models.recipe_schemas import ...` - this assumes 'app' is in PYTHONPATH.
# `from app.services.recipe_service import RecipeService` - same assumption.
# `from app.api.v1.dependencies import ...` - same assumption.
# `from app.db.models.user_model import User as DBUser` - same assumption.
# These paths should be valid if tests are run from the project root where `PYTHONPATH` includes the `smart_recipe_meal_planner` directory,
# or if the `app` directory itself is added to `PYTHONPATH`.
# For pytest, it usually handles this well if run from the project root.
# The `create_sample_recipe_public` helper uses many fields from `RecipePublic`.
# The `PaginatedRecipeResponse` is used in `test_list_recipes_success`.
# `RecipeUpdate` is used in update tests.
# `RecipeCreate` is used in create tests.
# `DBUser` is used for the mock user.
# All looks consistent with the plan.
