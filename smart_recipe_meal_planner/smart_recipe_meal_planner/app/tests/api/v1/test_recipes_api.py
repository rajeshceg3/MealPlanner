import pytest
import uuid
from unittest.mock import MagicMock

from fastapi import FastAPI, status
from fastapi.testclient import TestClient

# Adjust imports based on your project structure
from app.api.v1.endpoints.recipes import router as recipes_router
from app.models.recipe_schemas import RecipeCreate, RecipePublic, RecipeUpdate, PaginatedRecipeResponse, PaginationMeta
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
        is_superuser=False,
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
def create_sample_recipe_public(recipe_id=None, user_id=None, title="Test Recipe"):
    return RecipePublic(
        id=recipe_id or uuid.uuid4(),
        title=title,
        description="A delicious test recipe",
        ingredients=[{"name": "Test Ingredient", "quantity": "1", "unit": "cup"}],
        instructions="Mix and bake.",
        cooking_time_minutes=30,
        difficulty="Easy",
        nutritional_info={"calories": "300kcal"},
        user_id=user_id or uuid.uuid4(),
        tags=["test", "easy"],
        image_url="http://example.com/image.jpg"
    )

# --- Create Recipe Tests ---
def test_create_recipe_success(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()
    recipe_create_data = {
        "title": "New Test Recipe",
        "description": "A fresh recipe for testing",
        "ingredients": [{"name": "New Ingredient", "quantity": "2", "unit": "pcs"}],
        "instructions": "Follow these new instructions.",
        "cooking_time_minutes": 45,
        "difficulty": "Medium",
        "tags": ["new", "test"]
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
    assert response_data["user_id"] == str(current_user_id)

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
        "instructions": "Some instructions.",
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
        ingredients=[{"name": "Detailed Ing", "quantity": "1", "unit": "item"}],
        instructions="Detailed instructions.",
        cooking_time_minutes=60,
        difficulty="Hard",
        tags=["detail", "check"],
        nutritional_info={"calories": "500kcal"},
        image_url="http://example.com/detailed.jpg"
    )

    expected_recipe_public = RecipePublic(
        id=recipe_id,
        user_id=current_user_id,
        **recipe_create_payload.model_dump()
    )
    mock_service.create_recipe.return_value = expected_recipe_public

    response = client.post("/api/v1/recipes/", json=recipe_create_payload.model_dump())

    assert response.status_code == status.HTTP_201_CREATED

    mock_service.create_recipe.assert_called_once()
    args, kwargs = mock_service.create_recipe.call_args

    # Check the RecipeCreate model passed to the service
    assert isinstance(kwargs['recipe_in'], RecipeCreate)
    assert kwargs['recipe_in'].title == recipe_create_payload.title
    assert kwargs['recipe_in'].description == recipe_create_payload.description
    assert kwargs['recipe_in'].ingredients[0].name == recipe_create_payload.ingredients[0].name

    # Check the user_id passed to the service
    assert kwargs['user_id'] == current_user_id

    response_data = response.json()
    assert response_data["title"] == recipe_create_payload.title
    assert response_data["id"] == str(recipe_id)
    assert response_data["user_id"] == str(current_user_id)

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
        "ingredients": [{"name": "Opt Ing", "quantity": "1", "unit": "g"}],
        "instructions": "Opt instructions.",
        "cooking_time_minutes": 20,
        "difficulty": "Easy",
        "nutritional_info": {"calories": "100kcal", "protein": "10g"}, # Optional
        "image_url": "http://example.com/optional.jpg", # Optional
        "tags": ["optional"]
    }

    expected_recipe_public = RecipePublic(
        id=recipe_id,
        user_id=current_user_id,
        title=recipe_create_data["title"],
        description=recipe_create_data["description"],
        ingredients=recipe_create_data["ingredients"],
        instructions=recipe_create_data["instructions"],
        cooking_time_minutes=recipe_create_data["cooking_time_minutes"],
        difficulty=recipe_create_data["difficulty"],
        nutritional_info=recipe_create_data["nutritional_info"],
        image_url=recipe_create_data["image_url"],
        tags=recipe_create_data["tags"]
    )
    mock_service.create_recipe.return_value = expected_recipe_public

    response = client.post("/api/v1/recipes/", json=recipe_create_data)

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["title"] == recipe_create_data["title"]
    assert response_data["nutritional_info"]["protein"] == "10g"
    assert response_data["image_url"] == recipe_create_data["image_url"]

    mock_service.create_recipe.assert_called_once()
    call_args = mock_service.create_recipe.call_args[1]
    assert call_args['recipe_in'].nutritional_info == recipe_create_data["nutritional_info"]
    assert call_args['recipe_in'].image_url == recipe_create_data["image_url"]

# Test for update with partial data
def test_update_recipe_partial_data(client_and_mock_service):
    client, mock_service, current_user_id = client_and_mock_service
    recipe_id = uuid.uuid4()

    # Only updating description and tags
    update_data = RecipeUpdate(description="New partial description", tags=["partial", "update"])

    existing_recipe = create_sample_recipe_public(
        recipe_id=recipe_id,
        user_id=current_user_id,
        title="Original Title for Partial Update",
        description="Old description",
        tags=["old_tag"]
    )
    # The updated recipe would retain old title, but have new description and tags
    updated_recipe_public = create_sample_recipe_public(
        recipe_id=recipe_id,
        user_id=current_user_id,
        title=existing_recipe.title, # Title remains the same
        description=update_data.description, # Description is updated
        tags=update_data.tags # Tags are updated
    )

    mock_service.get_recipe_by_id.return_value = existing_recipe
    mock_service.update_recipe.return_value = updated_recipe_public

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_data.model_dump(exclude_unset=True))

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["title"] == existing_recipe.title # Title should not have changed
    assert response_data["description"] == "New partial description"
    assert "partial" in response_data["tags"]

    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.update_recipe.assert_called_once()
    call_args = mock_service.update_recipe.call_args[1]
    assert call_args['recipe_in'].title is None # Title was not part of the update payload
    assert call_args['recipe_in'].description == update_data.description
    assert call_args['recipe_in'].tags == update_data.tags
    assert call_args['user_id'] == current_user_id
    assert call_args['recipe_id'] == recipe_id

# Test for server error during create
def test_create_recipe_server_error(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_create_data = { "title": "Error Recipe", "description": "...", "ingredients": [], "instructions": "...", "cooking_time_minutes": 1, "difficulty": "Easy"}

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
```python
import pytest
import uuid
from unittest.mock import MagicMock

from fastapi import FastAPI, status
from fastapi.testclient import TestClient

# Adjust imports based on your project structure
# Assuming tests are run from a context where 'app' is a top-level package
# e.g. from the root of 'smart_recipe_meal_planner/smart_recipe_meal_planner/'
from app.api.v1.endpoints.recipes import router as recipes_router
from app.models.recipe_schemas import RecipeCreate, RecipePublic, RecipeUpdate, PaginatedRecipeResponse, PaginationMeta
from app.services.recipe_service import RecipeService
from app.api.v1.dependencies import get_current_active_user, get_recipe_service
from app.db.models.user_model import User as DBUser


# Fixture to set up the test client with mocked dependencies
@pytest.fixture
def client_and_mock_service():
    # Create a minimal FastAPI app for testing
    test_app = FastAPI()
    # Mount the recipes router. The prefix here should match how it's mounted in the main app
    # or be consistent for testing purposes.
    test_app.include_router(recipes_router, prefix="/api/v1/recipes")

    # Mock user
    mock_user_id = uuid.uuid4()
    mock_user = DBUser(
        id=mock_user_id,
        email="test@example.com",
        is_active=True,
        is_superuser=False,
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
    yield client, mock_recipe_service_instance, mock_user # Yield mock_user for convenience in tests

    # Clear overrides after tests
    test_app.dependency_overrides.clear()


# --- Test Cases ---

# Helper to create a sample RecipePublic (can be expanded or moved to a conftest.py)
def create_sample_recipe_public(recipe_id=None, user_id=None, title="Test Recipe", description="A delicious test recipe", ingredients=None, instructions="Mix and bake.", cooking_time_minutes=30, difficulty="Easy", nutritional_info=None, tags=None, image_url=None):
    return RecipePublic(
        id=recipe_id or uuid.uuid4(),
        title=title,
        description=description,
        ingredients=ingredients or [{"name": "Test Ingredient", "quantity": "1", "unit": "cup"}],
        instructions=instructions,
        cooking_time_minutes=cooking_time_minutes,
        difficulty=difficulty,
        nutritional_info=nutritional_info or {"calories": "300kcal"},
        user_id=user_id or uuid.uuid4(),
        tags=tags or ["test", "easy"],
        image_url=image_url or "http://example.com/image.jpg"
    )

# --- Create Recipe Tests ---
def test_create_recipe_success(client_and_mock_service):
    client, mock_service, current_user = client_and_mock_service
    recipe_id = uuid.uuid4()
    recipe_create_data = {
        "title": "New Test Recipe",
        "description": "A fresh recipe for testing",
        "ingredients": [{"name": "New Ingredient", "quantity": "2", "unit": "pcs"}],
        "instructions": "Follow these new instructions.",
        "cooking_time_minutes": 45,
        "difficulty": "Medium",
        "tags": ["new", "test"],
        "nutritional_info": {"calories": "450kcal"},
        "image_url": "http://example.com/new.jpg"
    }

    # Configure mock service
    # The service's create_recipe method is expected to return a RecipePublic model
    expected_recipe_public = RecipePublic(
        id=recipe_id,
        user_id=current_user.id,
        **recipe_create_data
    )
    mock_service.create_recipe.return_value = expected_recipe_public

    response = client.post("/api/v1/recipes/", json=recipe_create_data)

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["title"] == recipe_create_data["title"]
    assert response_data["id"] == str(recipe_id)
    assert response_data["user_id"] == str(current_user.id)

    mock_service.create_recipe.assert_called_once()
    # Check that the service was called with a RecipeCreate model and the correct user_id
    call_args = mock_service.create_recipe.call_args[1] # keyword args
    assert isinstance(call_args['recipe_in'], RecipeCreate)
    assert call_args['recipe_in'].title == recipe_create_data["title"]
    assert call_args['user_id'] == current_user.id


def test_create_recipe_invalid_input(client_and_mock_service):
    client, _, _ = client_and_mock_service
    # Missing 'title' which is required by RecipeCreate
    invalid_recipe_data = {
        "description": "A recipe missing a title",
        "ingredients": [{"name": "Ingredient", "quantity": "1", "unit": "cup"}],
        "instructions": "Some instructions.",
        "cooking_time_minutes": 30,
        "difficulty": "Easy"
    }
    response = client.post("/api/v1/recipes/", json=invalid_recipe_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# --- Get Recipe by ID Tests ---
def test_get_recipe_success(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_id = uuid.uuid4()

    expected_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=uuid.uuid4())
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
    recipe1_id, recipe2_id = uuid.uuid4(), uuid.uuid4()
    user_id = uuid.uuid4()

    recipe1 = create_sample_recipe_public(recipe_id=recipe1_id, user_id=user_id, title="Recipe Alpha")
    recipe2 = create_sample_recipe_public(recipe_id=recipe2_id, user_id=user_id, title="Recipe Beta")

    recipes_list = [recipe1, recipe2]
    pagination_meta = PaginationMeta(
        total_items=2,
        total_pages=1,
        current_page=1,
        limit=10 # Assuming default or passed limit
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
    client, mock_service, current_user = client_and_mock_service
    recipe_id = uuid.uuid4()

    update_data_dict = {"title": "Updated Title", "description": "Updated description"}
    update_data_model = RecipeUpdate(**update_data_dict) # Pydantic model for service call

    # Recipe as it exists before update
    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=current_user.id, title="Old Title")

    # Recipe as it should look after update
    updated_recipe_public = RecipePublic(
        id=recipe_id,
        user_id=current_user.id,
        title=update_data_dict["title"],
        description=update_data_dict["description"],
        # Other fields would typically be from existing_recipe, service handles merge
        ingredients=existing_recipe.ingredients,
        instructions=existing_recipe.instructions,
        cooking_time_minutes=existing_recipe.cooking_time_minutes,
        difficulty=existing_recipe.difficulty,
        tags=existing_recipe.tags,
        nutritional_info=existing_recipe.nutritional_info,
        image_url=existing_recipe.image_url
    )

    mock_service.get_recipe_by_id.return_value = existing_recipe # For the initial check in the endpoint
    mock_service.update_recipe.return_value = updated_recipe_public

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_data_dict)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["title"] == "Updated Title"
    assert response_data["description"] == "Updated description"
    assert response_data["id"] == str(recipe_id)

    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)

    mock_service.update_recipe.assert_called_once()
    call_args = mock_service.update_recipe.call_args[1]
    assert call_args['recipe_id'] == recipe_id
    assert isinstance(call_args['recipe_in'], RecipeUpdate)
    assert call_args['recipe_in'].title == update_data_model.title
    assert call_args['recipe_in'].description == update_data_model.description
    assert call_args['user_id'] == current_user.id


def test_update_recipe_not_found(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_id = uuid.uuid4()
    update_data = {"title": "Won't Update"}

    mock_service.get_recipe_by_id.return_value = None # Recipe doesn't exist for the initial check

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.update_recipe.assert_not_called()


def test_update_recipe_forbidden(client_and_mock_service):
    client, mock_service, current_user = client_and_mock_service
    recipe_id = uuid.uuid4()
    # Recipe belongs to a different user or update fails for auth reasons at service level
    other_user_id = uuid.uuid4()
    update_data_dict = {"title": "Attempted Update"}

    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=other_user_id)

    mock_service.get_recipe_by_id.return_value = existing_recipe # Recipe found
    mock_service.update_recipe.return_value = None # Service indicates auth failure or inability to update

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_data_dict)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)

    mock_service.update_recipe.assert_called_once()
    call_args = mock_service.update_recipe.call_args[1]
    assert call_args['recipe_id'] == recipe_id
    assert isinstance(call_args['recipe_in'], RecipeUpdate)
    assert call_args['recipe_in'].title == update_data_dict["title"]
    assert call_args['user_id'] == current_user.id


# --- Delete Recipe Tests ---
def test_delete_recipe_success(client_and_mock_service):
    client, mock_service, current_user = client_and_mock_service
    recipe_id = uuid.uuid4()

    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=current_user.id)
    mock_service.get_recipe_by_id.return_value = existing_recipe # For the initial check
    mock_service.delete_recipe.return_value = True # Deletion successful at service level

    response = client.delete(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.delete_recipe.assert_called_once_with(recipe_id=recipe_id, user_id=current_user.id)


def test_delete_recipe_not_found(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_id = uuid.uuid4()

    mock_service.get_recipe_by_id.return_value = None # Recipe doesn't exist for the initial check

    response = client.delete(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.delete_recipe.assert_not_called()


def test_delete_recipe_forbidden(client_and_mock_service):
    client, mock_service, current_user = client_and_mock_service
    recipe_id = uuid.uuid4()
    other_user_id = uuid.uuid4() # Recipe belongs to another user

    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=other_user_id)
    mock_service.get_recipe_by_id.return_value = existing_recipe # Recipe found
    mock_service.delete_recipe.return_value = False # Deletion fails at service level (auth)

    response = client.delete(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.delete_recipe.assert_called_once_with(recipe_id=recipe_id, user_id=current_user.id)

# --- Additional Test Cases for Robustness ---

def test_list_recipes_pagination_params(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service

    recipes_list = [create_sample_recipe_public()] # Dummy list
    # Ensure pagination meta reflects requested params
    pagination_meta = PaginationMeta(total_items=1, total_pages=1, current_page=5, limit=50)
    mock_service.get_recipes_list.return_value = (recipes_list, pagination_meta)

    response = client.get("/api/v1/recipes/?page=5&limit=50")

    assert response.status_code == status.HTTP_200_OK
    mock_service.get_recipes_list.assert_called_once_with(page=5, limit=50)
    response_data = response.json()
    assert response_data["pagination"]["current_page"] == 5
    assert response_data["pagination"]["limit"] == 50


def test_create_recipe_with_all_optional_fields(client_and_mock_service):
    client, mock_service, current_user = client_and_mock_service
    recipe_id = uuid.uuid4()
    recipe_create_data = {
        "title": "Recipe With All Opts",
        "description": "Desc for all opts",
        "ingredients": [{"name": "Opt Ing", "quantity": "1", "unit": "g"}],
        "instructions": "Opt instructions.",
        "cooking_time_minutes": 20,
        "difficulty": "Easy",
        "nutritional_info": {"calories": "100kcal", "protein": "10g"}, # Optional
        "image_url": "http://example.com/optional.jpg", # Optional
        "tags": ["optional_tag"]
    }

    expected_recipe_public = RecipePublic(
        id=recipe_id,
        user_id=current_user.id,
        **recipe_create_data # All fields from create_data are in public model
    )
    mock_service.create_recipe.return_value = expected_recipe_public

    response = client.post("/api/v1/recipes/", json=recipe_create_data)

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["title"] == recipe_create_data["title"]
    assert response_data["nutritional_info"]["protein"] == "10g"
    assert response_data["image_url"] == recipe_create_data["image_url"]

    mock_service.create_recipe.assert_called_once()
    call_args = mock_service.create_recipe.call_args[1]
    assert isinstance(call_args['recipe_in'], RecipeCreate)
    assert call_args['recipe_in'].nutritional_info == recipe_create_data["nutritional_info"]
    assert call_args['recipe_in'].image_url == recipe_create_data["image_url"]


def test_update_recipe_partial_data(client_and_mock_service):
    client, mock_service, current_user = client_and_mock_service
    recipe_id = uuid.uuid4()

    update_payload_dict = {"description": "New partial description", "tags": ["partial", "update"]}

    existing_recipe = create_sample_recipe_public(
        recipe_id=recipe_id, user_id=current_user.id,
        title="Original Title for Partial Update", description="Old description", tags=["old_tag"]
    )

    # Expected result after partial update
    updated_recipe_public = RecipePublic(
        id=recipe_id, user_id=current_user.id,
        title=existing_recipe.title, # Title should remain unchanged
        description=update_payload_dict["description"], # Description updated
        tags=update_payload_dict["tags"], # Tags updated
        # Other fields remain from 'existing_recipe'
        ingredients=existing_recipe.ingredients,
        instructions=existing_recipe.instructions,
        cooking_time_minutes=existing_recipe.cooking_time_minutes,
        difficulty=existing_recipe.difficulty,
        nutritional_info=existing_recipe.nutritional_info,
        image_url=existing_recipe.image_url,
    )

    mock_service.get_recipe_by_id.return_value = existing_recipe
    mock_service.update_recipe.return_value = updated_recipe_public

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_payload_dict)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["title"] == existing_recipe.title # Title should not have changed
    assert response_data["description"] == "New partial description"
    assert "partial" in response_data["tags"] and "update" in response_data["tags"]

    mock_service.get_recipe_by_id.assert_called_once_with(recipe_id=recipe_id)
    mock_service.update_recipe.assert_called_once()

    call_args = mock_service.update_recipe.call_args[1]
    assert isinstance(call_args['recipe_in'], RecipeUpdate)
    assert call_args['recipe_in'].title is None # Title was not part of the update payload
    assert call_args['recipe_in'].description == update_payload_dict["description"]
    assert call_args['recipe_in'].tags == update_payload_dict["tags"]
    assert call_args['user_id'] == current_user.id
    assert call_args['recipe_id'] == recipe_id

# --- Server Error Handling Tests (Endpoint Level) ---
# These tests verify that the generic exception handler in the endpoint works.

def test_create_recipe_endpoint_server_error(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_create_data = { "title": "Error Recipe", "description": "...", "ingredients": [{"name":"i","quantity":"1","unit":"pc"}], "instructions": "...", "cooking_time_minutes": 1, "difficulty": "Easy"}

    mock_service.create_recipe.side_effect = Exception("Simulated unexpected service error")

    response = client.post("/api/v1/recipes/", json=recipe_create_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error occurred while creating the recipe" in response.json()["detail"].lower()


def test_get_recipe_endpoint_server_error(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service
    recipe_id = uuid.uuid4()

    mock_service.get_recipe_by_id.side_effect = Exception("Simulated unexpected service error")

    response = client.get(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error occurred while retrieving the recipe" in response.json()["detail"].lower()


def test_list_recipes_endpoint_server_error(client_and_mock_service):
    client, mock_service, _ = client_and_mock_service

    mock_service.get_recipes_list.side_effect = Exception("Simulated unexpected service error")

    response = client.get("/api/v1/recipes/?page=1&limit=10")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error occurred while listing recipes" in response.json()["detail"].lower()


def test_update_recipe_endpoint_server_error(client_and_mock_service):
    client, mock_service, current_user = client_and_mock_service
    recipe_id = uuid.uuid4()
    update_data = {"title": "Error Update"}

    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=current_user.id)
    mock_service.get_recipe_by_id.return_value = existing_recipe # First check passes
    mock_service.update_recipe.side_effect = Exception("Simulated unexpected service error")

    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error occurred while updating the recipe" in response.json()["detail"].lower()


def test_delete_recipe_endpoint_server_error(client_and_mock_service):
    client, mock_service, current_user = client_and_mock_service
    recipe_id = uuid.uuid4()

    existing_recipe = create_sample_recipe_public(recipe_id=recipe_id, user_id=current_user.id)
    mock_service.get_recipe_by_id.return_value = existing_recipe # First check passes
    mock_service.delete_recipe.side_effect = Exception("Simulated unexpected service error")

    response = client.delete(f"/api/v1/recipes/{recipe_id}")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unexpected error occurred while deleting the recipe" in response.json()["detail"].lower()

```
