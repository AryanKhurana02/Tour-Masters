import { describe, expect, it } from "vitest";

import { buildRecommendationRequest } from "./TripRequestForm";

describe("trip request form", () => {
  it("searches the whole region without asking for a starting place", () => {
    const request = buildRecommendationRequest({
      date: "2026-11-01",
      days: 2,
      interests: ["nature"],
      budget: "",
      broaden: true,
    });

    expect(request).toEqual({
      region: "Uttarakhand",
      start_date: "2026-11-01",
      days: 2,
      interests: ["nature"],
      avoid_crowds: true,
      allow_broadened_search: true,
    });
    expect(request).not.toHaveProperty("start_destination_id");
  });
});
