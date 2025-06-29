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

  // New state variables for external search
  const [externalSearchTerm, setExternalSearchTerm] = useState('');
  const [externalRecipes, setExternalRecipes] = useState([]);
  const [externalLoading, setExternalLoading] = useState(false);
  const [externalError, setExternalError] = useState(null);
  const [importingStatus, setImportingStatus] = useState({}); // For import status per recipe

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

  // Implemented function for handling external search
  const handleExternalSearch = async () => {
    if (!externalSearchTerm.trim()) {
      setExternalError("Please enter a search term.");
      setExternalRecipes([]);
      return;
    }

    setExternalLoading(true);
    setExternalError(null);
    setExternalRecipes([]); // Clear previous results

    try {
      const response = await fetch(`http://localhost:8000/api/v1/recipes/search-external?query=${encodeURIComponent(externalSearchTerm)}&page=1&limit=10`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: `HTTP error! status: ${response.status}` }));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      if (result && result.data && Array.isArray(result.data.results)) {
        setExternalRecipes(result.data.results);
      } else {
        console.warn("Unexpected external search response structure:", result);
        setExternalRecipes([]);
        // Optionally set an error if the structure is not as expected but response was ok
        // setExternalError("Could not parse external recipes.");
      }
    } catch (err) {
      console.error("Failed to fetch external recipes:", err);
      setExternalError(err.message || "An unknown error occurred during external search.");
      setExternalRecipes([]);
    } finally {
      setExternalLoading(false);
    }
  };

  const handleImportRecipe = async (spoonacularId, title) => {
    console.log(`Starting import for recipe ID: ${spoonacularId}, Title: ${title}`);
    setImportingStatus(prevStatus => ({ ...prevStatus, [spoonacularId]: 'importing' }));

    const token = localStorage.getItem('jwt_token'); // Assuming token is stored in localStorage

    try {
      const response = await fetch(`http://localhost:8000/api/v1/recipes/import-external/${spoonacularId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` }), // Add Authorization header if token exists
        },
      });

      const responseData = await response.json(); // Try to parse JSON regardless of status for error messages

      if (response.ok) { // Typically 200 or 201 for successful POST
        console.log('Successfully imported recipe:', responseData);
        setImportingStatus(prevStatus => ({ ...prevStatus, [spoonacularId]: 'imported' }));

        // Assuming responseData.data is the successfully imported recipe object
        // and it conforms to the structure expected by the local recipe list.
        if (responseData && responseData.data && responseData.data.id) {
          const recipeExists = allRecipes.some(recipe => recipe.id === responseData.data.id);
          if (recipeExists) {
            alert(`Recipe '${title}' is already in your saved recipes.`);
          } else {
            setAllRecipes(prevRecipes => [responseData.data, ...prevRecipes]);
            alert(`Successfully imported '${title}'! It has been added to your saved recipes.`);
          }
        } else {
          // This case might indicate an issue with the backend response structure
          console.error('Import successful, but recipe data not in expected format:', responseData);
          alert(`Successfully imported '${title}', but there was an issue displaying it immediately. You may need to refresh the page.`);
        }
      } else {
        const errorMessage = responseData.detail || responseData.message || `Failed to import '${title}'. Status: ${response.status}`;
        console.error('Failed to import recipe:', errorMessage, responseData);
        setImportingStatus(prevStatus => ({ ...prevStatus, [spoonacularId]: 'error' }));
        alert(errorMessage);
      }
    } catch (err) {
      console.error('Error during import recipe:', err);
      setImportingStatus(prevStatus => ({ ...prevStatus, [spoonacularId]: 'error' }));
      alert(`An unexpected error occurred while importing '${title}'. Please try again. ${err.message}`);
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
        {/* External Search Input and Button */}
        <input
          type="text"
          placeholder="Search external recipes..."
          className="search-input external-search-field" // Added specific class
          value={externalSearchTerm}
          onChange={(e) => setExternalSearchTerm(e.target.value)}
        />
        <button
          onClick={handleExternalSearch}
          className="external-search-button action-button" // Added common button class
        >
          Search External
        </button>

        {/* Existing Filter Controls */}
        <input
          type="text"
          placeholder="Search by keyword..."
          className="search-input local-search-field" // Added specific class
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

      {/* External Search Results Section */}
      <div className="external-results-container">
        <h2>External Recipe Search Results</h2>
        {externalLoading && <p className="loading-message">Loading external recipes...</p>}
        {externalError && <p className="error-message">Error searching external recipes: {externalError}</p>}
        {!externalLoading && !externalError && externalRecipes.length === 0 && externalSearchTerm && (
          <p className="no-recipes-message">No external recipes found for "{externalSearchTerm}".</p>
        )}
        {!externalLoading && !externalError && externalRecipes.length === 0 && !externalSearchTerm && (
          <p className="info-message">Enter a term above and click "Search External" to find recipes from external sources.</p>
        )}
        {externalRecipes.length > 0 && (
          <ul className="external-recipe-list">
            {externalRecipes.map((recipe) => {
              const status = importingStatus[recipe.id];
              let buttonText = 'Import';
              let buttonDisabled = false;
              let buttonClasses = "import-button action-button"; // Added common button class for all buttons that perform actions

              if (status === 'importing') {
                buttonText = 'Importing...';
                buttonDisabled = true;
                buttonClasses += " import-button--importing";
              } else if (status === 'imported') {
                buttonText = 'Imported';
                buttonDisabled = true;
                buttonClasses += " import-button--imported";
              } else if (status === 'error') {
                buttonText = 'Import Failed';
                buttonDisabled = true;
                buttonClasses += " import-button--error";
              }

              return (
              <li key={recipe.id} className="external-recipe-item">
                <h3>{recipe.title}</h3>
                {recipe.image ? (
                  <img src={recipe.image} alt={recipe.title} className="external-recipe-image"/>
                ) : (
                  <div className="recipe-image-placeholder external-recipe-image-placeholder">No image available</div>
                )}
                {recipe.sourceUrl && (
                  <p className="external-recipe-source"><a href={recipe.sourceUrl} target="_blank" rel="noopener noreferrer">View Recipe Source</a></p>
                )}
                <button
                  onClick={() => handleImportRecipe(recipe.id, recipe.title)}
                  className={buttonClasses}
                  disabled={buttonDisabled}
                >
                  {buttonText}
                </button>
              </li>
              );
            })}
          </ul>
        )}
      </div>

      <hr className="section-separator"/>

      <h2 className="section-title">My Saved Recipes</h2>
      {filteredRecipes.length === 0 && !loading && (
        <p className="no-recipes-message">
          {allRecipes.length > 0 ? 'No recipes match your criteria for saved recipes.' : 'No saved recipes found.'}
        </p>
      )}

      <ul className="recipe-list">
        {currentRecipesToDisplay.map((recipe) => (
          <li key={recipe.id} className="recipe-item">
            <h2>{recipe.title}</h2>
            <div className="recipe-image-placeholder">Beautiful recipe image coming soon!</div> {/* Image Placeholder for local recipes */}
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
