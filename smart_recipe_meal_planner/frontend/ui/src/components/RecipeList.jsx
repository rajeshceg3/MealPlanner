import React, { useState, useEffect } from 'react';
import './RecipeList.css'; // Import the CSS file

const RecipeList = () => {
  const [allRecipes, setAllRecipes] = useState([]); // Store all fetched recipes
  const [filteredRecipes, setFilteredRecipes] = useState([]); // Store recipes to display
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [maxPrepTime, setMaxPrepTime] = useState(''); // Initialize as empty string or a sensible default
  const [sortCriteria, setSortCriteria] = useState('title-asc'); // Default sort
  const [currentPage, setCurrentPage] = useState(1);
  const RECIPES_PER_PAGE = 6; // Number of recipes per page

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
        if (result && result.data && Array.isArray(result.data.data)) {
          setAllRecipes(result.data.data);
          setFilteredRecipes(result.data.data); // Initially, display all recipes
        } else {
          console.warn("Unexpected response structure:", result);
          setAllRecipes([]);
          setFilteredRecipes([]);
        }
      } catch (err) {
        console.error("Failed to fetch recipes:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchRecipes();
  }, []);

  useEffect(() => {
    let currentRecipes = [...allRecipes];

    // Filter by search term
    if (searchTerm) {
      currentRecipes = currentRecipes.filter(recipe =>
        (recipe.title && recipe.title.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (recipe.description && recipe.description.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    // Filter by max preparation time
    if (maxPrepTime && parseInt(maxPrepTime, 10) > 0) {
      const prepTime = parseInt(maxPrepTime, 10);
      currentRecipes = currentRecipes.filter(recipe =>
        recipe.time_to_prepare && recipe.time_to_prepare <= prepTime
      );
    }

    // Sorting logic
    if (sortCriteria === 'title-asc') {
      currentRecipes.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    } else if (sortCriteria === 'title-desc') {
      currentRecipes.sort((a, b) => (b.title || '').localeCompare(a.title || ''));
    } else if (sortCriteria === 'time-asc') {
      currentRecipes.sort((a, b) => (a.time_to_prepare || Infinity) - (b.time_to_prepare || Infinity));
    } else if (sortCriteria === 'time-desc') {
      currentRecipes.sort((a, b) => (b.time_to_prepare || 0) - (a.time_to_prepare || 0));
    }
    // Add more sort criteria here if needed (e.g. by servings, by ID for 'default')

    setFilteredRecipes(currentRecipes);
    setCurrentPage(1); // Reset to first page when filters/sorting change
  }, [searchTerm, maxPrepTime, allRecipes, sortCriteria]);

  // Pagination logic
  const indexOfLastRecipe = currentPage * RECIPES_PER_PAGE;
  const indexOfFirstRecipe = indexOfLastRecipe - RECIPES_PER_PAGE;
  const currentRecipesToDisplay = filteredRecipes.slice(indexOfFirstRecipe, indexOfLastRecipe);
  const totalPages = Math.ceil(filteredRecipes.length / RECIPES_PER_PAGE);

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  if (loading) {
    return <p className="loading-message">Loading...</p>;
  }

  if (error) {
    return <p className="error-message">Error fetching recipes: {error}</p>;
  }

  return (
    <div className="recipe-list-container">
      <h1>Recipe List</h1>
      <div className="filter-controls">
        <input
          type="text"
          placeholder="Search by keyword..."
          className="search-input"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <input
          type="number"
          placeholder="Max prep time (mins)"
          className="prep-time-input"
          value={maxPrepTime}
          onChange={(e) => setMaxPrepTime(e.target.value)}
          min="0"
        />
        <select
          className="sort-select"
          value={sortCriteria}
          onChange={(e) => setSortCriteria(e.target.value)}
        >
          <option value="title-asc">Sort by Title (A-Z)</option>
          <option value="title-desc">Sort by Title (Z-A)</option>
          <option value="time-asc">Sort by Prep Time (Low to High)</option>
          <option value="time-desc">Sort by Prep Time (High to Low)</option>
          {/* <option value="default">Default</option> */}
        </select>
      </div>

      {filteredRecipes.length === 0 && !loading && (
        <p className="no-recipes-message">
          {allRecipes.length > 0 ? 'No recipes match your criteria.' : 'No recipes found.'}
        </p>
      )}

      <ul className="recipe-list">
        {currentRecipesToDisplay.map((recipe) => (
          <li key={recipe.id} className="recipe-item">
            <h2>{recipe.title}</h2>
            <div className="recipe-image-placeholder">Beautiful recipe image coming soon!</div> {/* Image Placeholder */}
            <p>{recipe.description || 'No description available.'}</p>

            {recipe.ingredients && recipe.ingredients.length > 0 && (
              <div className="ingredients-section">
                <h3>Ingredients:</h3>
                <ul className="ingredients-list">
                  {recipe.ingredients.map((ingredient, index) => (
                    <li key={index} className="ingredient-item">{ingredient}</li>
                  ))}
                </ul>
              </div>
            )}

            {recipe.instructions && (
              <div className="instructions-section">
                <h3>Instructions:</h3>
                <p>{recipe.instructions}</p>
              </div>
            )}

            {(recipe.time_to_prepare || recipe.servings) && (
              <div className="details">
                {recipe.time_to_prepare && <p>Time to prepare: {recipe.time_to_prepare} minutes</p>}
                {recipe.servings && <p>Servings: {recipe.servings}</p>}
              </div>
            )}
          </li>
        ))}
      </ul>

      {totalPages > 1 && (
        <div className="pagination-controls">
          <button
            onClick={handlePrevPage}
            disabled={currentPage === 1}
            className="pagination-button"
          >
            Previous
          </button>
          <span className="page-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={handleNextPage}
            disabled={currentPage === totalPages}
            className="pagination-button"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default RecipeList;
