import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ScoreBadge, StatusBadge } from "@/components/ui";

describe("StatusBadge", () => {
  it("renders the status text", () => {
    render(<StatusBadge status="qualified" />);
    expect(screen.getByText("qualified")).toBeInTheDocument();
  });
});

describe("ScoreBadge", () => {
  it("renders score and handles unscored leads", () => {
    const { rerender } = render(<ScoreBadge score={72} />);
    expect(screen.getByText("72/100")).toBeInTheDocument();
    rerender(<ScoreBadge score={null} />);
    expect(screen.getByText("not scored")).toBeInTheDocument();
  });
});
