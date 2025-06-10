import React, { useState, useEffect } from 'react';
import './RecipeList.css'; // Import the CSS file

const RecipeList = () => {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRecipes = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch('http://localhost:8000/api/v1/recipes/');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        // Assuming the actual recipe data is nested under a 'data' key
        // and the recipes themselves are in result.data.data based on PaginatedRecipeResponse
        if (result && result.data && Array.isArray(result.data.data)) {
          setRecipes(result.data.data);
        } else {
          // Handle cases where the structure is not as expected
          console.warn("Unexpected response structure:", result);
          setRecipes([]); // Set to empty array or handle as an error
        }
      } catch (err) {
        console.error("Failed to fetch recipes:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchRecipes();
  }, []); // Empty dependency array means this effect runs once on mount

  if (loading) {
    return <p className="loading-message">Loading...</p>;
  }

  if (error) {
    return <p className="error-message">Error fetching recipes: {error}</p>;
  }

  if (recipes.length === 0) {
    return <p className="no-recipes-message">No recipes found.</p>;
  }

  return (
    <div className="recipe-list-container">
      <h1>Recipe List</h1>
      <ul className="recipe-list">
        {recipes.map((recipe) => (
          <li key={recipe.id} className="recipe-item">
            <h2>{recipe.title}</h2>
            <p>{recipe.description || 'No description available.'}</p>
            {(recipe.time_to_prepare || recipe.servings) && (
              <div className="details">
                {recipe.time_to_prepare && <p>Time to prepare: {recipe.time_to_prepare} minutes</p>}
                {recipe.servings && <p>Servings: {recipe.servings}</p>}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default RecipeList;
