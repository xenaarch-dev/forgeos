import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { ItemList } from "@/components/ItemList";

describe("ItemList", () => {
  it("renders empty state", () => {
    render(<ItemList items={[]} />);
    expect(screen.getByText(/no items yet/i)).toBeTruthy();
  });
});
