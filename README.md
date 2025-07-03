# Smart Recipe Meal Planner

## Introduction

The Smart Recipe Meal Planner is a full-stack application designed to help users plan their meals efficiently. It features a Python/FastAPI backend for managing recipes, meal plans, and user accounts, and a React/Vite frontend for a user-friendly interface. The application aims to simplify the process of discovering recipes, organizing weekly meal schedules, and potentially generating shopping lists.

## Project Structure Overview

```
.
├── frontend/
│   └── ui/                   # React/Vite frontend application
│       ├── public/
│       ├── src/
│       ├── package.json
│       └── vite.config.js
├── smart_recipe_meal_planner/  # Python/FastAPI backend application
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── services/
│   │   └── tests/
│   ├── migrations/
│   ├── pyproject.toml
│   └── README.md             # Backend specific README
├── .gitignore
└── README.md                 # This file (main project README)
```

## Setup and Run Instructions

This section outlines the steps to set up the development environment, install dependencies, and run both the backend and frontend applications.

### Prerequisites

*   **Python:** Version 3.8 or higher.
*   **Node.js and npm:** Node.js (LTS version recommended) and npm (usually comes with Node.js). You can download them from [nodejs.org](https://nodejs.org/).
*   **Poetry:** For Python dependency management. Installation instructions can be found on the [Poetry official website](https://python-poetry.org/docs/#installation).
*   **PostgreSQL:** A running PostgreSQL database server.

### Backend Setup (Python/FastAPI)

1.  **Navigate to the backend directory:**
    ```bash
    cd smart_recipe_meal_planner
    ```

2.  **Install Python Dependencies:**
    Use Poetry to install the dependencies specified in `pyproject.toml`.
    ```bash
    poetry install
    ```
    This will create a virtual environment and install all necessary packages.

3.  **Environment Variable Setup:**
    *   Create a `.env` file in the `smart_recipe_meal_planner/` directory. This file will store sensitive configuration details.
    *   **Database Connection:** Add your PostgreSQL connection URL.
        ```env
        DATABASE_URL="postgresql+asyncpg://YOUR_DB_USER:YOUR_DB_PASSWORD@YOUR_DB_HOST:YOUR_DB_PORT/YOUR_DB_NAME"
        ```
        Replace the placeholders with your actual database credentials.
    *   **Spoonacular API Key:** To enable recipe import from the Spoonacular API, obtain an API key from the [Spoonacular API website](https://spoonacular.com/food-api) and add it to your `.env` file.
        ```env
        SPOONACULAR_API_KEY="your_actual_spoonacular_api_key_here"
        ```
    *   **JWT Secrets:** Define secrets for JWT authentication.
        ```env
        SECRET_KEY="your_very_secret_key_for_jwt"
        ALGORITHM="HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES=30
        ```

4.  **Database Migrations:**
    *   Ensure your PostgreSQL server is running and the `DATABASE_URL` in your `.env` file is correctly configured.
    *   Activate the Poetry virtual environment if you haven't already:
        ```bash
        poetry shell
        ```
    *   Run Alembic migrations to set up the database schema:
        ```bash
        alembic upgrade head
        ```

5.  **Run the Backend Server:**
    *   With the Poetry environment active (`poetry shell`), start the FastAPI development server using Uvicorn:
        ```bash
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ```
    *   The server will be accessible at `http://localhost:8000`. The `--reload` flag enables auto-reloading on code changes.

### Frontend Setup (React/Vite)

1.  **Navigate to the frontend directory:**
    From the project root:
    ```bash
    cd frontend/ui
    ```

2.  **Install Node.js Dependencies:**
    Use npm to install the packages defined in `package.json`.
    ```bash
    npm install
    ```

3.  **Environment Variable Setup (Frontend):**
    *   The frontend might also require environment variables, for example, to specify the backend API URL. Create a `.env` file in the `frontend/ui/` directory if needed.
    *   Example for Vite:
        ```env
        VITE_API_BASE_URL="http://localhost:8000"
        ```
    *   Refer to the Vite documentation for more details on environment variables in Vite projects.

4.  **Run the Frontend Development Server:**
    ```bash
    npm run dev
    ```
    *   The frontend application will typically be accessible at `http://localhost:5173` (Vite's default port). Check the terminal output for the exact URL.

**Important:** The backend server must be running for the frontend application to function correctly (e.g., to fetch data, authenticate users).

## Usage Examples

*   **Accessing the API:**
    Once the backend server is running, you can access the API documentation via:
    *   Swagger UI: `http://localhost:8000/docs`
    *   ReDoc: `http://localhost:8000/redoc`
    These interfaces allow you to explore and interact with the API endpoints.

*   **Using the UI:**
    Once the frontend server is running (and the backend is also running), open your web browser and navigate to the frontend URL (e.g., `http://localhost:5173`). You can then register, log in, search for recipes, and plan your meals.

## Contributing

We welcome contributions to the Smart Recipe Meal Planner! To contribute:

1.  **Fork the repository.**
2.  **Create a new branch** for your feature or bug fix: `git checkout -b feature/your-feature-name` or `git checkout -b fix/issue-number`.
3.  **Make your changes.** Ensure you follow coding standards and write tests for new functionality.
4.  **Test your changes thoroughly.**
5.  **Commit your changes** with a clear and descriptive commit message.
6.  **Push your branch** to your forked repository.
7.  **Create a Pull Request (PR)** against the `main` branch of the original repository. Provide a detailed description of your changes in the PR.
8.  **Wait for review and address any feedback.**

## CI/CD Pipeline

A Continuous Integration/Continuous Deployment (CI/CD) pipeline helps automate the testing and deployment process.

### General Principles

*   **Backend (Python/FastAPI):**
    *   Linting (e.g., Flake8, Black)
    *   Unit and integration testing (e.g., Pytest)
    *   Building a Docker image (optional, for deployment)
    *   Deploying to a server or cloud platform.
*   **Frontend (React/Vite):**
    *   Linting (e.g., ESLint, Prettier)
    *   Unit and component testing (e.g., Jest, React Testing Library)
    *   Building static assets (`npm run build`)
    *   Deploying static assets to a hosting service (e.g., Netlify, Vercel, AWS S3).

### Suggested Tools

*   **GitHub Actions:** For automating workflows directly within GitHub.
*   **Jenkins:** A self-hosted CI/CD server.
*   **GitLab CI/CD:** Integrated CI/CD with GitLab repositories.
*   **Docker:** For containerizing the backend application.

### Example Workflow Steps (Conceptual)

1.  **Push to Repository:** Developer pushes code to a branch.
2.  **Trigger CI Pipeline:**
    *   **Linting:** Check code style and quality for both backend and frontend.
    *   **Testing:** Run automated tests (unit, integration, component) for both.
    *   **Build:**
        *   Backend: Build a Docker image or package the application.
        *   Frontend: Build the static assets (`npm run build`).
3.  **Deploy (Optional, on merge to main/release branch):**
    *   Backend: Deploy Docker image to a container registry and then to a server/cloud service.
    *   Frontend: Deploy static assets to a web hosting service.

## Bug Scanning and Fixing

Proactive bug detection and efficient fixing are crucial for maintaining a healthy codebase.

### Tools for Static Analysis

*   **SonarQube:** A comprehensive platform for continuous inspection of code quality, including bug detection, vulnerability scanning, and code smell identification.
*   **Linters:**
    *   **Python (Backend):**
        *   `Flake8`: For enforcing PEP 8 style guide and detecting common errors.
        *   `Black`: For automated code formatting.
        *   `MyPy`: For static type checking.
    *   **JavaScript/TypeScript (Frontend):**
        *   `ESLint`: For identifying and fixing problems in JavaScript code.
        *   `Prettier`: For automated code formatting.

### Importance of Writing Tests

*   **Unit Tests:** Verify individual functions or components work correctly in isolation. (e.g., Pytest for Python, Jest/Vitest for React).
*   **Integration Tests:** Ensure that different parts of the application (e.g., API endpoint and database interaction) work together as expected.
*   **End-to-End (E2E) Tests:** Simulate real user scenarios from the frontend to the backend. (e.g., Cypress, Playwright).

### Debugging Techniques

*   **Backend (Python):**
    *   Using `pdb` (Python Debugger) or IDE debuggers (VS Code, PyCharm).
    *   Logging effectively using the `logging` module.
    *   FastAPI's interactive API documentation (`/docs`) for testing endpoints.
*   **Frontend (React):**
    *   Browser Developer Tools (Inspector, Console, Network tabs).
    *   React Developer Tools browser extension.
    *   Using `console.log()` strategically.
    *   Source maps for easier debugging of transpiled code.

### Reporting Bugs

*   Provide clear and concise steps to reproduce the bug.
*   Include information about the environment (browser version, OS, application version).
*   Attach screenshots or error messages if applicable.
*   Use the project's issue tracker (e.g., GitHub Issues) to report bugs.

## Industry Standard Best Practices

This project aims to follow or adopt several industry best practices:

*   **Code Linting and Formatting:** Enforced using tools like Black, Flake8 (Python) and ESLint, Prettier (JavaScript) to maintain consistent code style and quality.
*   **Version Control (Git):** Using Git for version control with a clear branching strategy (e.g., Gitflow or feature branches).
*   **Dependency Management:**
    *   **Backend:** Poetry for managing Python packages and virtual environments.
    *   **Frontend:** npm (or Yarn) for managing Node.js packages.
*   **Modular Design:** Structuring the code into reusable and maintainable modules and components.
*   **API Documentation:** Generating interactive API documentation using Swagger/OpenAPI (provided by FastAPI).
*   **Security Considerations:**
    *   Using environment variables for secrets (`.env` file).
    *   Input validation (Pydantic for FastAPI, form validation in React).
    *   Protecting against common web vulnerabilities (e.g., XSS, CSRF - to be continuously reviewed).
    *   Secure handling of user authentication and authorization (JWTs).
*   **Testing:** Comprehensive testing at different levels (unit, integration, E2E).
*   **Clear Commit Messages:** Following conventional commit message formats.

This README provides a comprehensive guide to the Smart Recipe Meal Planner project. For more specific details on the backend, refer to `smart_recipe_meal_planner/README.md`.
