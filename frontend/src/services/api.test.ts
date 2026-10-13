import { beforeEach, describe, expect, it, vi } from "vitest";

import { createItinerary, getRecommendations } from "./api";

describe("backend API client", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends recommendation inputs unchanged and consumes backend-owned scores", async () => {
    const responseBody = {
      request_id: "demo-request",
      items: [{ destination: { id: 2 }, rank_score: 76, crowd: { score: 31, level: "Quiet" } }],
      warnings: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const input = {
      region: "Uttarakhand",
      start_destination_id: 1,
      start_date: "2026-10-20",
      days: 2,
      interests: ["nature"],
      avoid_crowds: true,
      allow_broadened_search: true,
    };

    await expect(getRecommendations(input)).resolves.toEqual(responseBody);
    expect(fetchMock).toHaveBeenCalledWith("/api/recommendations", expect.objectContaining({
      method: "POST",
      body: JSON.stringify(input),
    }));
  });

  it("shows safe API validation messages without swallowing request failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: { message: "Request validation failed." } }), { status: 422 }),
    ));
    await expect(createItinerary({
      start_date: "2026-10-20",
      days: 1,
      destination_ids: [2],
      homestay_ids: [null],
      use_llm: false,
    })).rejects.toThrow("Request validation failed.");
  });
});
