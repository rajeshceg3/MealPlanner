import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.services.recipe_service import RecipeService
from app.clients.spoonacular_client import SpoonacularClient, SpoonacularException
from app.models.recipe_schemas import RecipeCreate, RecipePublic
from app.db.models.recipe_model import Recipe as DBRecipe
from app.db.models.user_model import User # Assuming User model is needed for created_by_user_id

# Sample Spoonacular response with nutritional information
SAMPLE_SPOONACULAR_NUTRITION_RESPONSE = {
    "id": 12345,
    "title": "Test Recipe with Nutrition",
    "image": "http://example.com/image.jpg",
    "sourceUrl": "http://example.com/source",
    "readyInMinutes": 30,
    "servings": 4,
    "summary": "A delicious test recipe summary.",
    "cuisines": ["Italian"],
    "diets": ["vegetarian"],
    "extendedIngredients": [
        {"id": 1, "nameClean": "Pasta", "amount": 200, "unit": "g", "original": "200g pasta"},
        {"id": 2, "nameClean": "Tomato Sauce", "amount": 400, "unit": "g", "original": "400g tomato sauce"},
    ],
    "analyzedInstructions": [{
        "name": "",
        "steps": [
            {"number": 1, "step": "Cook pasta."},
            {"number": 2, "step": "Add sauce."},
        ]
    }],
    "nutrition": {
        "nutrients": [
            {"name": "Calories", "amount": 550.0, "unit": "kcal"},
            {"name": "Protein", "amount": 25.0, "unit": "g"},
            {"name": "Fat", "amount": 15.0, "unit": "g"},
            {"name": "Carbohydrates", "amount": 75.0, "unit": "g"},
            {"name": "Net Carbohydrates", "amount": 70.0, "unit": "g"} # Example of alternative name
        ]
    }
}

# Sample Spoonacular response with MISSING nutritional information
SAMPLE_SPOONACULAR_NO_NUTRITION_RESPONSE = {
    "id": 67890,
    "title": "Test Recipe without Nutrition",
    "image": "http://example.com/image2.jpg",
    "sourceUrl": "http://example.com/source2",
    "readyInMinutes": 20,
    "servings": 2,
    "summary": "Another test recipe summary.",
    "extendedIngredients": [
        {"id": 3, "nameClean": "Flour", "amount": 100, "unit": "g", "original": "100g flour"},
    ],
    "analyzedInstructions": [{
        "name": "",
        "steps": [{"number": 1, "step": "Mix ingredients."}]
    }],
    "nutrition": { # Nutrition object present, but nutrients array is empty or missing relevant items
        "nutrients": [
            {"name": "Fiber", "amount": 5.0, "unit": "g"} # Only non-target nutrient
        ]
    }
}


@pytest.fixture
def mock_db_session():
    session = MagicMock(spec=Session)
    # Mock query results as needed, e.g., for existing recipe checks or ingredient lookups
    session.execute.return_value.scalars.return_value.first.return_value = None # Default: no existing recipe

    # Mock for _get_or_create_ingredient
    # This mock needs to be more sophisticated if testing complex ingredient logic
    mock_ingredient = MagicMock()
    mock_ingredient.id = uuid4()
    session.query.return_value.filter_by.return_value.first.return_value = None # No existing ingredient

    # session.add, session.commit, session.refresh will be called, mock them if necessary
    # For RecipeService.create_recipe, these are called on db_recipe_obj
    # The service method itself returns a RecipePublic, so direct db_recipe_obj inspection is tricky
    # without further mocking or a more integrated test setup.
    # For now, focusing on the RecipePublic output from import_recipe_from_spoonacular.

    return session

@pytest.fixture
def mock_spoonacular_client():
    client = AsyncMock(spec=SpoonacularClient)
    return client

@pytest.fixture
def recipe_service(mock_db_session):
    # Patching SpoonacularClient instantiation within RecipeService if it's created there,
    # or pass the mock_spoonacular_client if it's injected.
    # For this example, let's assume RecipeService might instantiate SpoonacularClient,
    # or we can patch where it's used.
    # The current RecipeService does not seem to take SpoonacularClient in __init__.
    # It's instantiated ad-hoc in methods. So we'll need to patch it there.
    return RecipeService(db=mock_db_session)

@pytest.mark.asyncio
async def test_import_recipe_from_spoonacular_with_nutrition(recipe_service: RecipeService, mock_db_session: MagicMock, mock_spoonacular_client: AsyncMock):
    user_id = uuid4()
    spoonacular_id = SAMPLE_SPOONACULAR_NUTRITION_RESPONSE["id"]

    # Mock the SpoonacularClient's get_recipe_details method
    mock_spoonacular_client.get_recipe_details.return_value = SAMPLE_SPOONACULAR_NUTRITION_RESPONSE

    # Mock _get_or_create_ingredient to simplify ingredient handling
    # It should return a mock DBIngredient object with an ID
    mock_ingredient_db = MagicMock()
    mock_ingredient_db.id = uuid4()
    mock_ingredient_db.name = "Test Ingredient"
    mock_ingredient_db.category = "Test Category"

    # The service calls `self.db.execute(stmt).scalars().first()` for existing ingredient checks,
    # and `self.db.add`, `self.db.commit`, `self.db.refresh` for new ones.
    # The `_get_or_create_ingredient` method is complex.
    # We can mock it directly on the service instance for a more focused unit test.

    recipe_service._get_or_create_ingredient = AsyncMock(return_value=mock_ingredient_db)

    with patch('app.services.recipe_service.SpoonacularClient', return_value=mock_spoonacular_client):
        # Mocking the DB behavior for create_recipe part
        # create_recipe adds a DBRecipe and then refreshes it.
        # We need to ensure that the object passed to add() is captured or mocked,
        # and that refresh() populates it with necessary fields like 'id', 'created_at', etc.

        # This part is tricky because create_recipe does a lot of DB interaction.
        # A simpler approach for this unit test might be to also mock parts of create_recipe,
        # or to validate the RecipeCreate object passed into it.
        # However, the goal is to test the *result* of import_recipe_from_spoonacular.

        # Let's refine the mock_db_session to better handle the create_recipe flow.
        # When self.db.add(db_recipe_obj) is called, we can capture db_recipe_obj.
        # Then, when self.db.refresh(db_recipe_obj) is called, we can manually add attributes.

        captured_db_recipe = None
        def capture_add(obj):
            nonlocal captured_db_recipe
            captured_db_recipe = obj

        def mock_refresh(obj):
            obj.id = uuid4()
            obj.created_at = "2023-01-01T12:00:00Z" # Placeholder
            obj.updated_at = "2023-01-01T12:00:00Z" # Placeholder
            obj.average_rating = 0.0 # Default from model
            obj.rating_count = 0 # Default from model
            # recipe_ingredients will be populated by the service, ensure they have .ingredient data
            for ri in obj.recipe_ingredients:
                if not hasattr(ri, 'ingredient') or ri.ingredient is None:
                    # Attach a mock DBIngredient if not present.
                    # This assumes ri.ingredient_id is set.
                    mock_ing = MagicMock()
                    mock_ing.id = ri.ingredient_id
                    mock_ing.name = "Mocked Ing from Refresh"
                    mock_ing.category = "Mocked Cat"
                    ri.ingredient = mock_ing


        mock_db_session.add = MagicMock(side_effect=capture_add)
        mock_db_session.refresh = MagicMock(side_effect=mock_refresh)
        # Mock the check for existing recipe by spoonacular_id to return None (not existing)
        mock_db_session.execute.return_value.scalars.return_value.first.return_value = None


        result_recipe: RecipePublic = await recipe_service.import_recipe_from_spoonacular(spoonacular_id, user_id)

    assert result_recipe is not None
    assert result_recipe.title == SAMPLE_SPOONACULAR_NUTRITION_RESPONSE["title"]
    assert result_recipe.spoonacular_id == spoonacular_id
    assert result_recipe.calories == 550.0
    assert result_recipe.protein == 25.0
    assert result_recipe.fat == 15.0
    assert result_recipe.carbohydrates == 75.0 # or 70.0 if "Net Carbohydrates" is prioritized by mapper

    mock_spoonacular_client.get_recipe_details.assert_called_once_with(spoonacular_id, include_nutrition=True)
    # Further assertions on db interactions can be added if needed

@pytest.mark.asyncio
async def test_import_recipe_from_spoonacular_no_nutrition(recipe_service: RecipeService, mock_db_session: MagicMock, mock_spoonacular_client: AsyncMock):
    user_id = uuid4()
    spoonacular_id = SAMPLE_SPOONACULAR_NO_NUTRITION_RESPONSE["id"]

    mock_spoonacular_client.get_recipe_details.return_value = SAMPLE_SPOONACULAR_NO_NUTRITION_RESPONSE

    mock_ingredient_db = MagicMock()
    mock_ingredient_db.id = uuid4()
    recipe_service._get_or_create_ingredient = AsyncMock(return_value=mock_ingredient_db)

    captured_db_recipe = None
    def capture_add(obj):
        nonlocal captured_db_recipe
        captured_db_recipe = obj

    def mock_refresh(obj): # Simplified refresh for this test
        obj.id = uuid4()
        obj.created_at = "2023-01-01T12:00:00Z"
        obj.updated_at = "2023-01-01T12:00:00Z"
        obj.average_rating = 0.0
        obj.rating_count = 0
        for ri in obj.recipe_ingredients:
            if not hasattr(ri, 'ingredient') or ri.ingredient is None:
                mock_ing = MagicMock()
                mock_ing.id = ri.ingredient_id
                mock_ing.name = "Mocked Ing from Refresh"
                mock_ing.category = "Mocked Cat"
                ri.ingredient = mock_ing

    mock_db_session.add = MagicMock(side_effect=capture_add)
    mock_db_session.refresh = MagicMock(side_effect=mock_refresh)
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = None # No existing recipe

    with patch('app.services.recipe_service.SpoonacularClient', return_value=mock_spoonacular_client):
        result_recipe: RecipePublic = await recipe_service.import_recipe_from_spoonacular(spoonacular_id, user_id)

    assert result_recipe is not None
    assert result_recipe.title == SAMPLE_SPOONACULAR_NO_NUTRITION_RESPONSE["title"]
    assert result_recipe.spoonacular_id == spoonacular_id
    assert result_recipe.calories is None
    assert result_recipe.protein is None
    assert result_recipe.fat is None
    assert result_recipe.carbohydrates is None # Mapper should map to None if not found by specific names

    mock_spoonacular_client.get_recipe_details.assert_called_once_with(spoonacular_id, include_nutrition=True)

# TODO: Add tests for direct recipe creation/update if those schemas were changed
# For example, test RecipeService.create_recipe if it now takes nutritional info directly.
# Based on previous tasks, RecipeCreate was updated, so create_recipe should handle these fields.

@pytest.mark.asyncio
async def test_create_recipe_with_nutrition(recipe_service: RecipeService, mock_db_session: MagicMock):
    user_id = uuid4()
    recipe_in = RecipeCreate(
        title="Test Manual Recipe",
        description="A recipe created manually with nutrition.",
        instructions=[{"step_number": 1, "instruction": "Mix it."}],
        ingredients=[{
            "ingredient_id": uuid4(), # Mocked ingredient ID
            "quantity": 100,
            "unit": "g",
            "preparation_note": "diced"
        }],
        calories=300.5,
        protein=10.2,
        carbohydrates=30.7,
        fat=15.1,
        # Other RecipeCreate fields
        prep_time_minutes=10,
        cook_time_minutes=20,
        servings=2,
        difficulty_level="easy",
        cuisine_type="home",
        dietary_tags=["vegan"],
    )

    # Mock DB interactions for create_recipe
    # Similar to import_recipe, but RecipeService.create_recipe is called directly.
    captured_db_recipe = None
    def capture_add(obj):
        nonlocal captured_db_recipe
        captured_db_recipe = obj
        # Simulate that obj.recipe_ingredients are DBRecipeIngredient instances
        # and need their .ingredient populated for the response part
        for ri_link in obj.recipe_ingredients:
            # In a real scenario, ri_link.ingredient_id would be used to fetch DBIngredient
            # Here, we mock that DBIngredient is available
            mock_ing_db = MagicMock(spec=DBIngredient) # Use spec for more accurate mocking
            mock_ing_db.id = ri_link.ingredient_id
            mock_ing_db.name = "Fetched Ingredient"
            mock_ing_db.category = "Fetched Category"

            # The service fetches ingredient details using:
            # ingredient_db = self.db.query(DBIngredient).get(ri.ingredient_id)
            # So, the mock_db_session needs to handle this.

            # We can refine the mock_db_session.query().get() behavior
            # For now, let's assume the refresh mock below handles it.

    def mock_refresh(obj):
        obj.id = uuid4()
        obj.created_at = "2023-01-01T12:00:00Z"
        obj.updated_at = "2023-01-01T12:00:00Z"
        obj.average_rating = 0.0
        obj.rating_count = 0
        # Populate ri.ingredient for each item in obj.recipe_ingredients
        for ri in obj.recipe_ingredients:
            if not hasattr(ri, 'ingredient') or ri.ingredient is None:
                mock_ing = MagicMock(spec=DBIngredient)
                mock_ing.id = ri.ingredient_id
                mock_ing.name = "Mocked Ing In Refresh"
                mock_ing.category = "Mocked Cat"
                ri.ingredient = mock_ing


    mock_db_session.add = MagicMock(side_effect=capture_add)
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock(side_effect=mock_refresh)

    # Mock for the ingredient query in create_recipe
    # self.db.query(DBIngredient).get(ri.ingredient_id)
    mock_queried_ingredient = MagicMock(spec=DBIngredient)
    mock_queried_ingredient.id = recipe_in.ingredients[0].ingredient_id # Match the one in RecipeCreate
    mock_queried_ingredient.name = "Queried Ingredient"
    mock_queried_ingredient.category = "Queried Category"

    # Setup query mock: session.query(DBIngredient).get(...)
    # This is a bit simplified; a more robust mock might involve a dictionary lookup.
    # For a single ingredient, this should work.
    mock_query_obj = MagicMock()
    mock_query_obj.get.return_value = mock_queried_ingredient
    mock_db_session.query.return_value = mock_query_obj


    result_recipe: RecipePublic = await recipe_service.create_recipe(recipe_in, user_id)

    assert result_recipe is not None
    assert result_recipe.title == recipe_in.title
    assert result_recipe.calories == recipe_in.calories
    assert result_recipe.protein == recipe_in.protein
    assert result_recipe.carbohydrates == recipe_in.carbohydrates
    assert result_recipe.fat == recipe_in.fat

    # Verify that captured_db_recipe (the DBRecipe instance) also has these fields set
    assert captured_db_recipe is not None
    assert captured_db_recipe.calories == recipe_in.calories
    assert captured_db_recipe.protein == recipe_in.protein
    assert captured_db_recipe.carbohydrates == recipe_in.carbohydrates
    assert captured_db_recipe.fat == recipe_in.fat


@pytest.mark.asyncio
async def test_create_recipe_without_nutrition(recipe_service: RecipeService, mock_db_session: MagicMock):
    user_id = uuid4()
    recipe_in = RecipeCreate(
        title="Test Manual Recipe No Nutrition",
        description="A recipe created manually without nutrition.",
        instructions=[{"step_number": 1, "instruction": "Mix it."}],
        ingredients=[{
            "ingredient_id": uuid4(), # Mocked ingredient ID
            "quantity": 100,
            "unit": "g",
        }],
        # Nutritional fields are Optional, so not providing them
        # Other RecipeCreate fields
        prep_time_minutes=10,
        cook_time_minutes=20,
        servings=2,
    )

    captured_db_recipe = None
    def capture_add(obj):
        nonlocal captured_db_recipe
        captured_db_recipe = obj

    def mock_refresh(obj):
        obj.id = uuid4()
        obj.created_at = "2023-01-01T12:00:00Z"
        obj.updated_at = "2023-01-01T12:00:00Z"
        obj.average_rating = 0.0
        obj.rating_count = 0
        for ri in obj.recipe_ingredients: # Ensure .ingredient is populated
            if not hasattr(ri, 'ingredient') or ri.ingredient is None:
                mock_ing = MagicMock(spec=DBIngredient)
                mock_ing.id = ri.ingredient_id
                mock_ing.name = "Mocked Ing In Refresh"
                mock_ing.category = "Mocked Cat"
                ri.ingredient = mock_ing

    mock_db_session.add = MagicMock(side_effect=capture_add)
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock(side_effect=mock_refresh)

    mock_queried_ingredient = MagicMock(spec=DBIngredient)
    mock_queried_ingredient.id = recipe_in.ingredients[0].ingredient_id
    mock_queried_ingredient.name = "Queried Ingredient No Nutrition"
    mock_queried_ingredient.category = "Queried Category"
    mock_query_obj = MagicMock()
    mock_query_obj.get.return_value = mock_queried_ingredient
    mock_db_session.query.return_value = mock_query_obj

    result_recipe: RecipePublic = await recipe_service.create_recipe(recipe_in, user_id)

    assert result_recipe is not None
    assert result_recipe.title == recipe_in.title
    assert result_recipe.calories is None # Should be None as per Pydantic model Optional[float]
    assert result_recipe.protein is None
    assert result_recipe.carbohydrates is None
    assert result_recipe.fat is None

    assert captured_db_recipe is not None
    assert captured_db_recipe.calories is None # DB field is nullable
    assert captured_db_recipe.protein is None
    assert captured_db_recipe.carbohydrates is None
    assert captured_db_recipe.fat is None

# Note: The actual carbohydrate value asserted for SAMPLE_SPOONACULAR_NUTRITION_RESPONSE
# depends on the mapper logic: if it finds "Carbohydrates" first or "Net Carbohydrates".
# The current mapper logic:
# if name == "carbohydrates": carbohydrates = amount
# elif name == "net carbohydrates" and carbohydrates is None: carbohydrates = amount
# So, if "Carbohydrates" is present, it will be used.
# SAMPLE_SPOONACULAR_NUTRITION_RESPONSE has "Carbohydrates" with amount 75.0. So, 75.0 is correct.

# Further tests could include:
# - What if Spoonacular returns nutrition info as strings? (The Pydantic models expect float)
#   The mapper currently takes `amount` as is. Pydantic will try to coerce.
# - Test edge cases for `_get_or_create_ingredient` if that logic is complex.
#   (Here, it's mostly mocked on the service for simplicity).
# - Test updates to recipes with nutritional info. (RecipeUpdate schema was also updated).
#   This would involve `RecipeService.update_recipe`.
# - Ensure the test database session (`mock_db_session`) accurately mocks all necessary DB calls
#   for the methods under test. This can get quite involved.
#   For example, the `create_recipe` and `import_recipe_from_spoonacular` methods in `RecipeService`
#   interact with `DBRecipe`, `DBRecipeIngredient`, and `DBIngredient` tables.
#   The current mocks are somewhat simplified.
#   A more robust approach for service layer tests might involve an in-memory SQLite database
#   with real SQLAlchemy models, if true async support for SQLite in tests is handled.
#   However, for unit tests with mocks, this level of detail is a common trade-off.

# One key aspect for the create_recipe part of the tests:
# The RecipeService.create_recipe method, when constructing RecipePublic, does this:
# `ingredient_db = self.db.query(DBIngredient).get(ri.ingredient_id)`
# This needs to be mocked in `mock_db_session` for `test_create_recipe_...` tests.
# I've added a basic mock for this in `test_create_recipe_with_nutrition` and `_without_nutrition`.
# The `captured_db_recipe.calories` etc. assertions in `test_create_recipe_...` are good
# because they check what's actually being written to the DB model before commit.

# The `mock_refresh` function needs to ensure that `ri.ingredient` is populated
# because the `RecipePublic` construction relies on it.
# I've updated `mock_refresh` in all tests to simulate this.

# Final check on the carbohydrate assertion:
# SAMPLE_SPOONACULAR_NUTRITION_RESPONSE has:
#   {"name": "Carbohydrates", "amount": 75.0, "unit": "g"},
#   {"name": "Net Carbohydrates", "amount": 70.0, "unit": "g"}
# The mapper logic is:
#   if name == "carbohydrates": carbohydrates = amount
#   elif name == "net carbohydrates" and carbohydrates is None: carbohydrates = amount
# So, "Carbohydrates" (75.0) will be picked first. The assertion `assert result_recipe.carbohydrates == 75.0` is correct.

# One more check: the `create_recipe` in `RecipeService` does not directly take nutritional fields.
# It takes a `RecipeCreate` object. `RecipeCreate` *does* have these fields.
# The service then creates a `DBRecipe` object.
# `db_recipe_obj = DBRecipe(title=recipe_in.title, ..., spoonacular_id=recipe_in.spoonacular_id)`
# This instantiation of `DBRecipe` needs to also pass the nutritional fields from `recipe_in`.
# This was NOT part of the previous subtasks for `recipe_service.py` explicitly, but it's an
# implied change for `create_recipe` to fully support the new fields in `RecipeCreate`.
# Let's assume for now the tests I've written for `create_recipe` will FAIL if `DBRecipe`
# is not correctly populated with these fields from `recipe_in` within `RecipeService.create_recipe`.
# If they fail, a subsequent step would be to fix `RecipeService.create_recipe`.
# The current tests assert `captured_db_recipe.calories == recipe_in.calories`, etc.
# This will verify if the `DBRecipe` model instance gets these values.
# It's possible `RecipeService.create_recipe` needs an update like:
# `calories=recipe_in.calories, protein=recipe_in.protein, ...` when creating `DBRecipe`.
# I will add this to the report as a potential necessary change if tests fail.
# Let's assume the tests pass for now and the `DBRecipe` instantiation is correct.
# (The Pydantic model `RecipeCreate` has the fields, and the DB model `DBRecipe` has them.
# The SQLAlchemy model instantiation `DBRecipe(...)` will map them if `recipe_in.calories` etc. are passed).
# This is an important point, I should verify this in `RecipeService.create_recipe`.
# I will do a quick read of `RecipeService.create_recipe` again.

# Ok, I will re-read `recipe_service.py` specifically for the `create_recipe` method's instantiation of `DBRecipe`.
# This is crucial for the `test_create_recipe_...` tests to be valid.
# (This is a self-correction/verification step based on writing the tests).I've created the test file `smart_recipe_meal_planner/app/tests/services/test_recipe_service.py` with:
-   Mock Spoonacular responses (with and without nutrition).
-   Fixtures for `mock_db_session`, `mock_spoonacular_client`, and `recipe_service`.
-   Test for `import_recipe_from_spoonacular` with full nutrition data, asserting correct mapping.
-   Test for `import_recipe_from_spoonacular` with missing nutrition data, asserting fields are `None`.
-   Tests for `create_recipe` (which uses `RecipeCreate` Pydantic model that now includes nutritional fields):
    -   One test providing nutritional data.
    -   One test omitting nutritional data (fields should be `None`).

A critical point arose while writing these tests: the `RecipeService.create_recipe` method itself needs to map the nutritional fields from the input `RecipeCreate` Pydantic model to the `DBRecipe` SQLAlchemy model when it's instantiated. If it doesn't, the `test_create_recipe_*` tests will fail on assertions like `captured_db_recipe.calories == recipe_in.calories`.

I need to verify the `create_recipe` method in `recipe_service.py` to ensure it correctly passes these new fields.
