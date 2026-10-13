import { describe, expect, it } from "vitest";

import { getCrowdLevelClass } from "./theme";

describe("crowd level theme mapping", () => {
  it.each([
    ["Quiet", "crowd-tone--quiet"],
    ["Moderate", "crowd-tone--moderate"],
    ["Busy", "crowd-tone--busy"],
    ["Very busy", "crowd-tone--verybusy"],
  ] as const)("maps the API level %s to its design token class", (level, className) => {
    expect(getCrowdLevelClass(level)).toBe(className);
  });
});
