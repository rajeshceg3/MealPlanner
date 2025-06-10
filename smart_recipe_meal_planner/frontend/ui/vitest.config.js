/// <reference types="vitest" />
import { defineConfig } from 'vitest'; // Changed from 'vitest/config'
import react from '@vitejs/plugin-react'; // To process JSX from React components

export default defineConfig({
  plugins: [react()], // Important for JSX transformation
  test: {
    globals: true, // Makes expect, describe, it, etc. available globally
    environment: 'jsdom', // Use JSDOM for simulating browser environment
    setupFiles: ['./vitest.setup.js'], // Path to your setup file
    // Optional: You can configure include paths for your tests if they are not in default locations
    // include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    // Optional: Coverage configuration
    // coverage: {
    //   provider: 'v8', // or 'istanbul'
    //   reporter: ['text', 'json', 'html'],
    // },
  },
});
