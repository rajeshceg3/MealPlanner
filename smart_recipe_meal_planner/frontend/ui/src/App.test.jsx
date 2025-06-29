import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import App from './App'; // Assuming App.jsx is in the same src directory

// Mock the global fetch function
global.fetch = vi.fn();

// Helper function to mock successful fetch with empty recipes
const mockFetchEmptyRecipes = () => {
  global.fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ data: { data: [] } }), // Match expected structure
  });
};

describe('App Component', () => {
  beforeEach(() => {
    global.fetch.mockReset();
    // Suppress console.error for expected "No recipes found" scenario if necessary
    // vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('renders without crashing and displays header', () => {
    mockFetchEmptyRecipes(); // Mock fetch even for a simple render to avoid console errors from RecipeList
    render(<App />);

    // Check for the header
    expect(screen.getByText('Recipe Meal Planner')).toBeInTheDocument();
  });

  test('renders RecipeList component', async () => {
    mockFetchEmptyRecipes();
    render(<App />);

    // Wait for RecipeList to process the mocked fetch and render its state
    // We expect "No recipes found." due to the mockFetchEmptyRecipes
    await waitFor(() => {
      expect(screen.getByText('No recipes found.')).toBeInTheDocument();
    });
  });

  test('RecipeList integration: handles loading state from App', () => {
    // Mock fetch to return a promise that never resolves
    const unresolvedPromise = new Promise(() => {});
    global.fetch.mockImplementationOnce(() => unresolvedPromise);

    render(<App />);
    // Check that RecipeList's loading state is rendered
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

});
