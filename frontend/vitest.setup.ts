import "@testing-library/jest-dom/vitest";

// Stub window.matchMedia for jsdom (not implemented there).
// Default: desktop width (matches = false) so chatpage tests render the desktop grid unchanged.
// Individual tests that need mobile behaviour override this stub themselves (e.g. useismobile.test.ts).
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
