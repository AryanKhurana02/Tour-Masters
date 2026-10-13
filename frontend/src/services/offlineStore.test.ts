import { beforeEach, describe, expect, it, vi } from "vitest";
import { openDB } from "idb";

import { deleteSavedTrip, getSavedTrip, listSavedTrips, saveTrip } from "./offlineStore";
import type { SavedTrip } from "../types/api";

vi.mock("idb", () => ({ openDB: vi.fn() }));

const db = {
  put: vi.fn().mockResolvedValue(undefined),
  getAllFromIndex: vi.fn().mockResolvedValue([{ id: "older" }, { id: "newer" }]),
  get: vi.fn().mockResolvedValue({ id: "saved" }),
  delete: vi.fn().mockResolvedValue(undefined),
};

describe("offline trip store", () => {
  beforeEach(() => {
    db.put.mockClear();
    db.getAllFromIndex.mockClear();
    db.get.mockClear();
    db.delete.mockClear();
    vi.mocked(openDB).mockResolvedValue(db as never);
  });

  it("saves, reads, lists newest first, and deletes a complete saved snapshot", async () => {
    const trip = {
      id: "saved",
      saved_at: "2026-10-13T00:00:00.000Z",
      title: "A gentle escape",
      request: { start_date: "2026-10-20", days: 1, destination_ids: [2], homestay_ids: [null], use_llm: false },
      itinerary: { request_id: "request-1", generation_mode: "rule_fallback", days: [], warnings: [] },
      destinations: [{ id: 2, name: "Demo place" }],
      homestays: [],
    } as unknown as SavedTrip;

    await saveTrip(trip);
    await expect(getSavedTrip("saved")).resolves.toEqual({ id: "saved" });
    await expect(listSavedTrips()).resolves.toEqual([{ id: "newer" }, { id: "older" }]);
    await expect(deleteSavedTrip("saved")).resolves.toBeUndefined();

    expect(db.put).toHaveBeenCalledWith("trips", trip);
    expect(db.getAllFromIndex).toHaveBeenCalledWith("trips", "by-saved-at");
    expect(db.delete).toHaveBeenCalledWith("trips", "saved");
  });

  it("propagates IndexedDB failures to the UI", async () => {
    db.get.mockRejectedValueOnce(new Error("storage unavailable"));
    await expect(getSavedTrip("missing")).rejects.toThrow("storage unavailable");
  });
});
