import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest'; // Vitest's mocking utility
import RecipeList from './RecipeList';

// Mock the global fetch function
global.fetch = vi.fn();

const mockRecipesData = {
  data: [
    { id: '1', title: 'Test Recipe 1', description: 'Delicious test recipe 1', time_to_prepare: 30, servings: 2 },
    { id: '2', title: 'Test Recipe 2', description: 'Another tasty test recipe', time_to_prepare: 45, servings: 4 },
  ]
};

const mockEmptyRecipesData = {
  data: []
};

describe('RecipeList Component', () => {
  beforeEach(() => {
    // Reset mocks before each test
    global.fetch.mockReset();
  });

  test('renders recipes correctly', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: mockRecipesData }), // Ensure the response structure matches component expectation
    });

    render(<RecipeList />);

    // Wait for recipes to be displayed
    await waitFor(() => {
      expect(screen.getByText('Test Recipe 1')).toBeInTheDocument();
      expect(screen.getByText('Delicious test recipe 1')).toBeInTheDocument();
    });

    expect(screen.getByText('Test Recipe 2')).toBeInTheDocument();
    expect(screen.getByText('Another tasty test recipe')).toBeInTheDocument();
    // Check that loading is gone
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  test('renders loading state initially', () => {
    // Mock fetch to return a promise that never resolves
    global.fetch.mockImplementationOnce(() => new Promise(() => {}));

    render(<RecipeList />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  test('renders error state on fetch failure', async () => {
    global.fetch.mockRejectedValueOnce(new Error('API Error'));

    render(<RecipeList />);

    await waitFor(() => {
      expect(screen.getByText(/Error fetching recipes: API Error/i)).toBeInTheDocument();
    });
    // Check that loading is gone
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  test('renders "No recipes found" message for empty data', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: mockEmptyRecipesData }), // Ensure the response structure matches
    });

    render(<RecipeList />);

    await waitFor(() => {
      expect(screen.getByText('No recipes found.')).toBeInTheDocument();
    });
    // Check that loading is gone
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  test('handles unexpected response structure gracefully', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ unexpected: "structure" }), // Not matching { data: { data: [] } }
    });
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {}); // Suppress console.warn for this test

    render(<RecipeList />);

    await waitFor(() => {
      // It should default to showing "No recipes found" or an error,
      // depending on how the component handles it.
      // Based on current RecipeList.jsx, it will log a warning and set recipes to [].
      expect(screen.getByText('No recipes found.')).toBeInTheDocument();
    });
    expect(consoleWarnSpy).toHaveBeenCalledWith("Unexpected response structure:", { unexpected: "structure" });
    consoleWarnSpy.mockRestore();
  });
});
