import { describe, expect, it } from "vitest";
import { callerOf } from "./session.js";

describe("callerOf", () => {
  it("names the user a bearer token belongs to", () => {
    expect(callerOf("Bearer t-9")?.name).toBe("ranger-9");
  });
});
