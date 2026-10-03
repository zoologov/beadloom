import { describe, expect, it } from "vitest";
import { makeNote } from "./note.js";

describe("makeNote", () => {
  it("trims the title", () => {
    expect(makeNote(1, "ranger-4", "  tides ", "").title).toBe("tides");
  });

  it("refuses an empty title", () => {
    expect(() => makeNote(1, "ranger-4", "  ", "")).toThrow();
  });
});
