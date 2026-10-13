import { describe, expect, it } from "vitest";

import { formatDate, isDemoRecord } from "./presentation";

describe("presentation helpers", () => {
  it("formats a catalogue date without changing its day", () => {
    expect(formatDate("2026-10-13")).toMatch(/13/);
    expect(formatDate("2026-10-13")).toMatch(/Oct/);
  });

  it("only flags explicitly labelled synthetic fixture provenance", () => {
    expect(isDemoRecord("DEMO FIXTURE - NOT VERIFIED")).toBe(true);
    expect(isDemoRecord("District tourism board")).toBe(false);
  });
});
