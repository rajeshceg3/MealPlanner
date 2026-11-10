# Feature map - MealPlanner

| Feature | Entry point | Proven by |
| --- | --- | --- |
| Recipe CRUD with pagination | `/api/v1/recipes/*` | `app/tests/api/v1/test_recipes_api.py` |
| Spoonacular search | `GET /api/v1/recipes/search-external` | `test_recipes_external.py` + route-order smoke check |
| Spoonacular import (incl. idempotency, error mapping) | `POST /api/v1/recipes/import-external/{id}` | `test_recipes_external.py`, `test_recipes_integration.py` |
| Spoonacular data mapping | `app/services/recipe_mapper.py` | `app/tests/services/test_recipe_mapper.py` |
| Recipe service (create/import, nutrition fields) | `app/services/recipe_service.py` | `app/tests/services/test_recipe_service.py` |

The automated proof lives in `.cursor/skills/verify-meal-planner/`.
