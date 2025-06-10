// vitest.setup.js
import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Optional: Mock global browser APIs if needed, e.g., localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = value.toString();
    },
    removeItem: (key) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// You can also mock other global objects like 'fetch' here if you want a default mock for all tests,
// but it's often better to mock fetch specifically in tests where it's used.
// global.fetch = vi.fn(...);
