import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest'; // Vitest's mocking utility
import RecipeList from './RecipeList';

// Mock the global fetch function
global.fetch = vi.fn();

const MOCK_RECIPES_RESPONSE = {
  data: [
    { id: '1', title: 'Apple Pie', description: 'Sweet apple dessert', time_to_prepare: 60, servings: 8, ingredients: ['apple', 'sugar', 'flour'], instructions: 'Bake it.' },
    { id: '2', title: 'Banana Bread', description: 'Moist banana loaf', time_to_prepare: 70, servings: 6, ingredients: ['banana', 'flour'], instructions: 'Mix and bake.' },
    { id: '3', title: 'Chicken Curry', description: 'Spicy chicken dish', time_to_prepare: 45, servings: 4, ingredients: ['chicken', 'curry powder'], instructions: 'Cook it.' },
    { id: '4', title: 'Spaghetti Bolognese', description: 'Classic Italian pasta', time_to_prepare: 90, servings: 5, ingredients: ['spaghetti', 'beef', 'tomato'], instructions: 'Simmer sauce.' },
    { id: '5', title: 'Vegetable Stir-fry', description: 'Healthy veggie meal', time_to_prepare: 25, servings: 2, ingredients: ['broccoli', 'carrot', 'soy sauce'], instructions: 'Stir fry quickly.' },
    { id: '6', title: 'Salmon Salad', description: 'Light salmon and greens', time_to_prepare: 15, servings: 1, ingredients: ['salmon', 'lettuce'], instructions: 'Grill salmon.' },
    { id: '7', title: 'Pancakes', description: 'Fluffy breakfast cakes', time_to_prepare: 20, servings: 3, ingredients: ['flour', 'milk', 'egg'], instructions: 'Cook on griddle.' },
  ]
};

const MOCK_RECIPES_SINGLE_PAGE_RESPONSE = { // For testing pagination disable states
  data: [
    { id: '1', title: 'Apple Pie', description: 'Sweet apple dessert', time_to_prepare: 60, servings: 8 },
    { id: '2', title: 'Banana Bread', description: 'Moist banana loaf', time_to_prepare: 70, servings: 6 },
  ]
}


const mockEmptyRecipesData = { // Keep this for the empty test
  data: []
};


// Helper function to mock successful fetch
const mockFetchSuccess = (data = MOCK_RECIPES_RESPONSE.data) => {
  global.fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ data: { data } }), // Adjusted to match component's expected nested structure
  });
};

// Helper function to mock failed fetch
const mockFetchFailure = (error = new Error('API Error')) => {
  global.fetch.mockRejectedValueOnce(error);
};


describe('RecipeList Component - Initial Rendering', () => {
  beforeEach(() => {
    global.fetch.mockReset();
    vi.spyOn(console, 'warn').mockImplementation(() => {}); // Suppress console.warn
  });

  afterEach(() => {
    vi.restoreAllMocks(); // Restore console.warn
  });

  test('renders recipes correctly', async () => {
    mockFetchSuccess();
    render(<RecipeList />);

    await waitFor(() => {
      expect(screen.getByText('Apple Pie')).toBeInTheDocument();
      expect(screen.getByText('Sweet apple dessert')).toBeInTheDocument();
    });
    // RECIPES_PER_PAGE is 6, so Banana Bread should also be there
    expect(screen.getByText('Banana Bread')).toBeInTheDocument();
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  test('renders loading state initially', () => {
    // Mock fetch to return a promise that never resolves for this specific test
    const unresolvedPromise = new Promise(() => {});
    global.fetch.mockImplementationOnce(() => unresolvedPromise);

    render(<RecipeList />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  test('renders error state on fetch failure', async () => {
    mockFetchFailure();
    render(<RecipeList />);

    await waitFor(() => {
      expect(screen.getByText(/Error fetching recipes: API Error/i)).toBeInTheDocument();
    });
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  test('renders "No recipes found" message for empty data', async () => {
    global.fetch.mockResolvedValueOnce({ // Using specific mock for this one
      ok: true,
      json: async () => ({ data: { data: mockEmptyRecipesData.data } }),
    });
    render(<RecipeList />);

    await waitFor(() => {
      expect(screen.getByText('No recipes found.')).toBeInTheDocument();
    });
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  test('handles unexpected response structure gracefully', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ unexpected: "structure" }),
    });
    render(<RecipeList />);

    await waitFor(() => {
      expect(screen.getByText('No recipes found.')).toBeInTheDocument();
    });
    expect(console.warn).toHaveBeenCalledWith("Unexpected response structure:", { unexpected: "structure" });
  });
});

describe('RecipeList Component - Search and Filtering', () => {
  beforeEach(async () => {
    global.fetch.mockReset();
    mockFetchSuccess(); // Provide all recipes by default
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    render(<RecipeList />);
    // Wait for initial recipes to load
    await waitFor(() => expect(screen.getByText('Apple Pie')).toBeInTheDocument());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('filters by keyword in title (case-insensitive)', async () => {
    const searchInput = screen.getByPlaceholderText('Search by keyword...');
    await act(async () => {
      await userEvent.type(searchInput, 'apple');
    });

    expect(screen.getByText('Apple Pie')).toBeInTheDocument();
    expect(screen.queryByText('Banana Bread')).not.toBeInTheDocument();
    expect(screen.queryByText('Chicken Curry')).not.toBeInTheDocument();
  });

  test('filters by keyword in description', async () => {
    const searchInput = screen.getByPlaceholderText('Search by keyword...');
    await act(async () => {
      await userEvent.type(searchInput, 'healthy veggie');
    });

    expect(screen.getByText('Vegetable Stir-fry')).toBeInTheDocument();
    expect(screen.queryByText('Apple Pie')).not.toBeInTheDocument();
  });

  test('filters by max preparation time', async () => {
    const prepTimeInput = screen.getByPlaceholderText('Max prep time (mins)');
    await act(async () => {
      await userEvent.type(prepTimeInput, '30');
    });

    expect(screen.getByText('Vegetable Stir-fry')).toBeInTheDocument(); // 25 mins
    expect(screen.getByText('Salmon Salad')).toBeInTheDocument();      // 15 mins
    expect(screen.getByText('Pancakes')).toBeInTheDocument();          // 20 mins
    expect(screen.queryByText('Apple Pie')).not.toBeInTheDocument();   // 60 mins
    expect(screen.queryByText('Chicken Curry')).not.toBeInTheDocument(); // 45 mins
  });

  test('combines keyword and prep time filtering', async () => {
    const searchInput = screen.getByPlaceholderText('Search by keyword...');
    const prepTimeInput = screen.getByPlaceholderText('Max prep time (mins)');

    await act(async () => {
      await userEvent.type(searchInput, 'cake'); // Pancakes
      await userEvent.type(prepTimeInput, '20'); // Pancakes (20 mins)
    });

    expect(screen.getByText('Pancakes')).toBeInTheDocument();
    expect(screen.queryByText('Apple Pie')).not.toBeInTheDocument();
    expect(screen.queryByText('Banana Bread')).not.toBeInTheDocument(); // Also has 'cake' if we were less specific, but time is 70
  });

  test('displays "No recipes match your criteria" when filters result in no matches', async () => {
    const searchInput = screen.getByPlaceholderText('Search by keyword...');
    await act(async () => {
      await userEvent.type(searchInput, 'NonExistentRecipeZZZ');
    });

    expect(screen.getByText('No recipes match your criteria.')).toBeInTheDocument();
  });
});

// Placeholder for Sorting tests
describe('RecipeList Component - Sorting', () => {
  beforeEach(async () => {
    global.fetch.mockReset();
    mockFetchSuccess();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    render(<RecipeList />);
    await waitFor(() => expect(screen.getByText('Apple Pie')).toBeInTheDocument());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('sorts by Title (A-Z) by default', () => {
    const recipeTitles = screen.getAllByRole('heading', { level: 2 }).map(h => h.textContent);
    // First page (6 items)
    expect(recipeTitles).toEqual([
      'Apple Pie',
      'Banana Bread',
      'Chicken Curry',
      'Pancakes',         // Sorted 'Pancakes' before 'Salmon Salad' etc.
      'Salmon Salad',
      'Spaghetti Bolognese' // Sorted 'Spaghetti' before 'Vegetable Stir-fry'
    ]);
  });

  test('sorts by Title (Z-A)', async () => {
    const sortSelect = screen.getByRole('combobox');
    await act(async () => {
      await userEvent.selectOptions(sortSelect, 'title-desc');
    });
    const recipeTitles = screen.getAllByRole('heading', { level: 2 }).map(h => h.textContent);
    expect(recipeTitles).toEqual([
      'Vegetable Stir-fry',
      'Spaghetti Bolognese',
      'Salmon Salad',
      'Pancakes',
      'Chicken Curry',
      'Banana Bread',
    ]);
  });

  test('sorts by Prep Time (Low to High)', async () => {
    const sortSelect = screen.getByRole('combobox');
    await act(async () => {
      await userEvent.selectOptions(sortSelect, 'time-asc');
    });
    const recipeTitles = screen.getAllByRole('heading', { level: 2 }).map(h => h.textContent);
    expect(recipeTitles).toEqual([
      'Salmon Salad',       // 15
      'Pancakes',           // 20
      'Vegetable Stir-fry', // 25
      'Chicken Curry',      // 45
      'Apple Pie',          // 60
      'Banana Bread',       // 70
    ]);
  });

  test('sorts by Prep Time (High to Low)', async () => {
    const sortSelect = screen.getByRole('combobox');
    await act(async () => {
      await userEvent.selectOptions(sortSelect, 'time-desc');
    });
    const recipeTitles = screen.getAllByRole('heading', { level: 2 }).map(h => h.textContent);
    expect(recipeTitles).toEqual([
      'Spaghetti Bolognese', // 90
      'Banana Bread',       // 70
      'Apple Pie',          // 60
      'Chicken Curry',      // 45
      'Vegetable Stir-fry', // 25
      'Pancakes',           // 20
    ]);
  });

  test('maintains sort order after filtering', async () => {
    const searchInput = screen.getByPlaceholderText('Search by keyword...');
    const sortSelect = screen.getByRole('combobox');

    // Sort by Prep Time (High to Low) first
    await act(async () => {
      await userEvent.selectOptions(sortSelect, 'time-desc');
    });

    // Then filter by "dessert"
    await act(async () => {
      await userEvent.type(searchInput, 'dessert'); // Apple Pie (60), Banana Bread (70)
    });

    const recipeTitles = screen.getAllByRole('heading', { level: 2 }).map(h => h.textContent);
    expect(recipeTitles).toEqual([
      'Banana Bread', // 70 (dessert)
      'Apple Pie',    // 60 (dessert)
    ]);
  });
});

// Placeholder for Pagination tests
describe('RecipeList Component - Pagination', () => {
  // Note: RECIPES_PER_PAGE is 6 in RecipeList.jsx
  // MOCK_RECIPES_RESPONSE has 7 items.

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('With multiple pages of recipes', () => {
    beforeEach(async () => {
      global.fetch.mockReset();
      mockFetchSuccess(MOCK_RECIPES_RESPONSE.data); // 7 recipes
      vi.spyOn(console, 'warn').mockImplementation(() => {});
      render(<RecipeList />);
      await waitFor(() => expect(screen.getByText('Apple Pie')).toBeInTheDocument());
    });

    test('displays first page correctly with "Previous" disabled and "Next" enabled', () => {
      expect(screen.getByText('Apple Pie')).toBeInTheDocument();
      expect(screen.getByText('Spaghetti Bolognese')).toBeInTheDocument(); // 6th item by default sort
      expect(screen.queryByText('Vegetable Stir-fry')).not.toBeInTheDocument(); // 7th item, should be on page 2

      const prevButton = screen.getByRole('button', { name: /previous/i });
      const nextButton = screen.getByRole('button', { name: /next/i });
      expect(prevButton).toBeDisabled();
      expect(nextButton).toBeEnabled();
      expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();
    });

    test('navigates to the next page and updates controls', async () => {
      const nextButton = screen.getByRole('button', { name: /next/i });
      await act(async () => {
        await userEvent.click(nextButton);
      });

      expect(screen.getByText('Vegetable Stir-fry')).toBeInTheDocument(); // 7th item now visible
      expect(screen.queryByText('Apple Pie')).not.toBeInTheDocument();   // 1st item (page 1) no longer visible

      const prevButton = screen.getByRole('button', { name: /previous/i });
      expect(prevButton).toBeEnabled();
      expect(nextButton).toBeDisabled(); // Now on last page
      expect(screen.getByText('Page 2 of 2')).toBeInTheDocument();
    });

    test('navigates to previous page after going next', async () => {
      const nextButton = screen.getByRole('button', { name: /next/i });
      await act(async () => {
        await userEvent.click(nextButton);
      });

      // Now on page 2, click previous
      const prevButton = screen.getByRole('button', { name: /previous/i });
      await act(async () => {
        await userEvent.click(prevButton);
      });

      expect(screen.getByText('Apple Pie')).toBeInTheDocument(); // Back to page 1
      expect(screen.queryByText('Vegetable Stir-fry')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /next/i })).toBeEnabled();
      expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();
    });
  });

  describe('With single page of recipes', () => {
    beforeEach(async () => {
      global.fetch.mockReset();
      // Using MOCK_RECIPES_SINGLE_PAGE_RESPONSE which has 2 items. RECIPES_PER_PAGE is 6.
      mockFetchSuccess(MOCK_RECIPES_SINGLE_PAGE_RESPONSE.data);
      vi.spyOn(console, 'warn').mockImplementation(() => {});
      render(<RecipeList />);
      await waitFor(() => expect(screen.getByText('Apple Pie')).toBeInTheDocument());
    });

    test('does not display pagination controls if total pages is 1', () => {
      expect(screen.queryByRole('button', { name: /previous/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /next/i })).not.toBeInTheDocument();
      expect(screen.queryByText(/Page \d+ of \d+/i)).not.toBeInTheDocument();
    });
  });

  describe('Pagination reset', () => {
     beforeEach(async () => {
      global.fetch.mockReset();
      mockFetchSuccess(MOCK_RECIPES_RESPONSE.data); // 7 recipes
      vi.spyOn(console, 'warn').mockImplementation(() => {});
      render(<RecipeList />);
      await waitFor(() => expect(screen.getByText('Apple Pie')).toBeInTheDocument());
    });

    test('resets to page 1 when search term changes', async () => {
      // Go to page 2
      const nextButton = screen.getByRole('button', { name: /next/i });
      await act(async () => { await userEvent.click(nextButton); });
      expect(screen.getByText('Page 2 of 2')).toBeInTheDocument();
      expect(screen.getByText('Vegetable Stir-fry')).toBeInTheDocument();

      // Apply a search filter
      const searchInput = screen.getByPlaceholderText('Search by keyword...');
      await act(async () => { await userEvent.type(searchInput, 'Apple'); }); // Filters to 'Apple Pie' (1 item)

      // Should be back on page 1 of the new filtered results
      expect(screen.getByText('Apple Pie')).toBeInTheDocument();
      // Pagination controls should not be visible as there's only 1 result now (1 page)
      expect(screen.queryByText(/Page \d+ of \d+/i)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /previous/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /next/i })).not.toBeInTheDocument();
    });

    test('resets to page 1 when sort criteria changes', async () => {
       // Go to page 2
      const nextButton = screen.getByRole('button', { name: /next/i });
      await act(async () => { await userEvent.click(nextButton); });
      expect(screen.getByText('Page 2 of 2')).toBeInTheDocument();
      expect(screen.getByText('Vegetable Stir-fry')).toBeInTheDocument(); // Default: Apple Pie, Banana Bread, Chicken Curry, Pancakes, Salmon Salad, Spaghetti Bolognese | Vegetable Stir-fry

      // Change sort criteria
      const sortSelect = screen.getByRole('combobox');
      await act(async () => { await userEvent.selectOptions(sortSelect, 'time-desc'); }); // Richest first: Spaghetti, Banana, Apple Pie, Chicken, Veg, Salmon, Pancakes

      // Should be back on page 1 of the new sorted results
      // First 6 items by time-desc: Spaghetti, Banana, Apple, Chicken, Veg, Salmon
      expect(screen.getByText('Spaghetti Bolognese')).toBeInTheDocument();
      expect(screen.getByText('Salmon Salad')).toBeInTheDocument();
      expect(screen.queryByText('Pancakes')).not.toBeInTheDocument(); // Pancakes is 7th by time-desc, so on page 2
      expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();
    });
  });
});
