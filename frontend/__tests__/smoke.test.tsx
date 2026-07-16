// frontend/__tests__/smoke.test.tsx
import { render, screen } from "@testing-library/react";
import { Button } from "@/components/ui/button";
test("shadcn button renders", () => {
  render(<Button>Cerca</Button>);
  expect(screen.getByText("Cerca")).toBeInTheDocument();
});
