import type { SavedStayRequest, SavedTrip } from "../types/api";

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T12:00:00`));
}

export function isDemoRecord(sourceLabel: string): boolean {
  return sourceLabel.toUpperCase().includes("DEMO FIXTURE");
}

export function isSavedStayRequest(record: SavedTrip): record is SavedStayRequest {
  return "type" in record && record.type === "stay_request";
}
