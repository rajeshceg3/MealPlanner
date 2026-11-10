---
name: verify-meal-planner
description: Verifies the Smart Recipe Meal Planner backend against its promised behavior - the full pytest suite (unit, API, and integration tests) plus a route-ordering smoke check - with machine-readable evidence.
---

# Verify Meal Planner

## Launch

```bash
python3 -m venv smart_recipe_meal_planner/.venv   # first run only
smart_recipe_meal_planner/.venv/bin/pip install fastapi 'uvicorn[standard]' 'pydantic[email]' pydantic-settings sqlalchemy psycopg2-binary alembic beautifulsoup4 'python-jose[cryptography]' 'passlib[bcrypt]' tenacity python-multipart httpx pytest pytest-cov pytest-asyncio requests
python3 .cursor/skills/verify-meal-planner/verify.py
```

Exit 0 and `FAILURES=0` mean green. No database or network services are
needed: the suite replaces the DB with a stateful mock session and patches
the Spoonacular HTTP client.

## Doctor

The first check gates on the backend deps being importable (fastapi,
sqlalchemy, pytest). Use the venv at `smart_recipe_meal_planner/.venv`;
the runner picks it up automatically when present.

## Drive

1. Route-table smoke check: `GET /api/v1/recipes/search-external` must be
   answered by the search-external route, not shadowed by
   `/recipes/{recipe_id}` (a UUID-parse 422 signals the regression).
2. `pytest app/tests`: the unit, API, and integration suites.

## Evidence

Each run writes a fresh `EVIDENCE_DIR` with `evidence.json` (one record
per check). `FAILURES=n` is the last line; the exit code mirrors it.

## Cleanup

Nothing persists: no servers are started, no files written outside the
evidence directory.

## Maintenance

When the API surface the README promises changes, extend the suite and the
smoke check in the same commit.

## Known boundaries

- The frontend (`frontend/`, React/Vite) is not covered by this skill.
- Integration tests use a stateful mock session, not a live PostgreSQL;
  SQL-level behavior (constraints, real joins) is not exercised.
- `get_current_active_user` is a placeholder dependency returning a fixed
  user; real auth is not implemented.
