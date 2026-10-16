import { describe, expect, it } from "vitest";
import { sanitizeCsvCell, scoreColor } from "@/lib/api";

describe("sanitizeCsvCell (formula-injection guard)", () => {
  it("prefixes cells starting with formula characters", () => {
    expect(sanitizeCsvCell("=SUM(A1:A2)")).toBe("'=SUM(A1:A2)");
    expect(sanitizeCsvCell("+123")).toBe("'+123");
    expect(sanitizeCsvCell("-2+3")).toBe("'-2+3");
    expect(sanitizeCsvCell("@mention")).toBe("'@mention");
  });

  it("leaves normal cells untouched", () => {
    expect(sanitizeCsvCell("Lilongwe Foods")).toBe("Lilongwe Foods");
    expect(sanitizeCsvCell("")).toBe("");
  });
});

describe("scoreColor", () => {
  it("buckets scores into qualified / borderline / poor / unscored", () => {
    expect(scoreColor(80)).toContain("green");
    expect(scoreColor(40)).toContain("amber");
    expect(scoreColor(10)).toContain("red");
    expect(scoreColor(null)).toContain("slate");
  });
});
