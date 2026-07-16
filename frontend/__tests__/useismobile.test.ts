import { renderHook } from "@testing-library/react";
import { useIsMobile } from "@/lib/useIsMobile";

function setWidth(matches: boolean) {
  window.matchMedia = ((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

test("parte false e diventa true dopo il mount quando il viewport è mobile", () => {
  setWidth(true);
  const { result } = renderHook(() => useIsMobile());
  // dopo l'effetto di mount riflette il match
  expect(result.current).toBe(true);
});

test("resta false su viewport desktop", () => {
  setWidth(false);
  const { result } = renderHook(() => useIsMobile());
  expect(result.current).toBe(false);
});
