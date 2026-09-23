// Vitest global setup file.
// Extends `expect` with @testing-library/jest-dom matchers
// (toBeInTheDocument, toHaveClass, ...). Required by apps/frontend/vitest.config.ts:11.

import '@testing-library/jest-dom/vitest';

// T-135: TanStack Router's scroll-restoration calls window.scrollTo()
// during navigation. jsdom declares scrollTo as "not implemented" and
// prints a stderr warning for every call — noisy in test output. We
// overwrite it with a no-op. See F-014.
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'scrollTo', {
    value: () => undefined,
    writable: true,
    configurable: true,
  });
}
