# Smart Recipe Meal Planner

Backend services for the Smart Recipe Meal Planner Application.

This project provides the API endpoints and backend logic for managing recipes, meal plans, user accounts, and other related functionalities.

## Project Structure

```
smart_recipe_meal_planner/
├── app/                      # Main application code
│   ├── api/                  # API route definitions
│   ├── core/                 # Core logic, configuration, settings
│   ├── db/                   # Database models, session, migrations (Alembic)
│   ├── models/               # Pydantic models (request/response schemas)
│   ├── services/             # Business logic services
│   └── tests/                # Unit and integration tests
├── migrations/               # Alembic migration scripts
├── pyproject.toml            # Project dependencies and metadata (Poetry)
├── README.md                 # This file
└── .gitignore                # Git ignore file
```

## Setup and Installation

This section outlines the steps to set up the development environment, install dependencies, and run the application.

*   **Python Version:** Ensure you have Python 3.8 or higher installed.
*   **Poetry:** This project uses Poetry for dependency management. Install Poetry if you haven't already (see [Poetry documentation](https://python-poetry.org/docs/#installation)).
*   **Dependencies:** Navigate to the project root (`smart_recipe_meal_planner/`) and run `poetry install` to create a virtual environment and install all required dependencies.
*   **Database Setup:**
    *   This application uses PostgreSQL. Ensure you have a PostgreSQL server running.
    *   Configure your database connection details in a `.env` file (see Environment Variables section below). Key variables include `DATABASE_URL`.
    *   Example: `DATABASE_URL="postgresql+asyncpg://user:password@host:port/dbname"`
*   **Environment Variables:**
    *   The application uses environment variables for configuration, managed via a `.env` file in the project root (`smart_recipe_meal_planner/`). Create this file if it doesn't exist.
    *   **Spoonacular API Key:** To enable recipe import from Spoonacular, you need an API key.
        *   The API key is essential for any features that interact with the Spoonacular API.
        *   Add your Spoonacular API key to your `.env` file like this:
            ```env
            SPOONACULAR_API_KEY="your_actual_api_key_here"
            ```
        *   You can obtain an API key by registering on the [Spoonacular API website](https://spoonacular.com/food-api).
    *   Other environment variables like database connection strings (e.g., `DATABASE_URL`) and JWT secrets (e.g., `SECRET_KEY`, `ALGORITHM`) also need to be defined in the `.env` file.
*   **Database Migrations:**
    *   Once your database connection is configured in `.env`, run database migrations using Alembic. From the project root, with Poetry's virtual environment active, you might run:
        ```bash
        poetry shell
        alembic upgrade head
        ```
*   **Starting the FastAPI Server:**
    *   With the environment active and migrations applied, start the FastAPI development server using Uvicorn:
        ```bash
        poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ```
    *   The `--reload` flag enables auto-reloading on code changes, useful for development.

## API Documentation

API documentation will be available via Swagger UI and ReDoc, accessible through the `/docs` and `/redoc` endpoints once the application is running.

## Future Phases

*   **Phase 1 (Current):** Core backend setup, user authentication, recipe management, basic meal planning.
*   **Phase 2:** Integration with external recipe APIs (Spoonacular, Edamam), advanced meal planning features, nutritional analysis.
*   **Phase 3:** User preferences, dietary restrictions, shopping list generation, notifications.

## Contributing

Contribution guidelines will be added here.

## License

This project is licensed under the MIT License (or specify another if applicable).

---

## Frontend UI (React)

A React-based frontend application is available in the `frontend/ui` directory. This UI interacts with the FastAPI backend to provide a user interface for the Smart Recipe Meal Planner.

### Setup Instructions

1.  **Navigate to the frontend directory**:
    ```bash
    cd smart_recipe_meal_planner/frontend/ui
    ```

2.  **Install dependencies**:
    This command will install all the necessary Node.js packages defined in `package.json`.
    ```bash
    npm install
    ```

### Running the Frontend Development Server

1.  **Start the Vite development server**:
    ```bash
    npm run dev
    ```
    The frontend application will typically be accessible at `http://localhost:5173` (this is the default port for Vite, but it may choose another if 5173 is busy). Check the terminal output when you run the command for the exact URL.

### Note on Backend Server

For the frontend application to function correctly (e.g., fetch recipes, manage meal plans), the FastAPI backend server **must be running**.

**To run the backend server (from the project root directory):**
1. Navigate to the backend app directory: `cd smart_recipe_meal_planner/app` (or ensure your terminal is in the `smart_recipe_meal_planner` root if using `python -m app.main` etc.).
2. Start the Uvicorn server. A common command is:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   (Ensure you have your Python environment activated and backend dependencies installed as per backend setup instructions.)

Refer to the main "Setup and Installation" section of this README (once updated) for detailed backend setup.
