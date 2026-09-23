// Vitest global setup file.
// Extends `expect` with @testing-library/jest-dom matchers
// (toBeInTheDocument, toHaveClass, ...). Required by apps/frontend/vitest.config.ts:11.
//
// Kept minimal on purpose: T-130 only needs pure-function tests with no DOM.

import '@testing-library/jest-dom/vitest';
