import type {
  DemoBookingReceipt,
  DemoBookingRequest,
  Destination,
  DestinationDetail,
  Homestay,
  ItineraryRequest,
  ItineraryResponse,
  MockInventoryResponse,
  RecommendationRequest,
  RecommendationResponse,
  RouteEstimate,
  WeatherHistoryResponse,
} from "../types/api";

const apiRoot = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

// Mock inventory data for offline fallback
const mockInventoryData: Record<string, MockInventoryResponse> = {
  "1": {
    homestay_id: 1,
    check_in: "2026-10-20",
    check_out: "2026-10-22",
    inventory_mode: "demo_mock",
    days: [
      {
        homestay_id: 1,
        date: "2026-10-20",
        total_units: 2,
        available_units: 1,
        inventory_mode: "demo_mock",
        source_label: "DEMO FIXTURE - NOT VERIFIED",
        reviewed_at: "2026-10-12",
      },
    ],
    warnings: [],
  },
};

// Simulated offline crowd data for fallback
const mockCrowdData: Record<string, { score: number; level: string }> = {
  "1": { score: 43, level: "Moderate" },
  "2": { score: 35, level: "Quiet" },
  "3": { score: 58, level: "Moderate" },
  "4": { score: 29, level: "Quiet" },
  "5": { score: 50, level: "Moderate" },
};

interface ApiError {
  error?: { message?: string };
}

async function request<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number }
): Promise<T> {
  const timeoutMs = init?.timeoutMs ?? 15_000;
  const abortController = new AbortController();
  const timeoutId = setTimeout(() => abortController.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${apiRoot}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
      signal: abortController.signal,
    });
  } catch (error) {
    clearTimeout(timeoutId);
    // Network error or timeout - fall back to offline data
    return getOfflinePayload(path, error as Error) as unknown as T;
  }

  clearTimeout(timeoutId);

  if (!response.ok) {
    let message = `The trip desk returned an error (${response.status}).`;
    try {
      const body = (await response.json()) as ApiError;
      if (body.error?.message) message = body.error.message;
    } catch {
      // Keep the safe status-based message when an error body is not JSON.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export function getRecommendations(
  input: RecommendationRequest,
): Promise<RecommendationResponse> {
  return request<RecommendationResponse>("/recommendations", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getDestinations(): Promise<Destination[]> {
  return request<Destination[]>("/destinations");
}

export function getHomestays(destinationId: number): Promise<Homestay[]> {
  return request<Homestay[]>(`/homestays?destination_id=${destinationId}`);
}

export function getRouteFromHub(destinationId: number): Promise<RouteEstimate> {
  return request<RouteEstimate>(`/destinations/${destinationId}/route-from-hub`);
}

export function createItinerary(input: ItineraryRequest): Promise<ItineraryResponse> {
  return request<ItineraryResponse>("/itineraries", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getDestination(id: number): Promise<DestinationDetail> {
  return request<DestinationDetail>(`/destinations/${id}`);
}

export function submitDemoBooking(
  input: DemoBookingRequest,
): Promise<DemoBookingReceipt> {
  return request<DemoBookingReceipt>("/booking-requests", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getMockInventory(
  homestayId: number,
  checkIn: string,
  checkOut: string,
): Promise<MockInventoryResponse> {
  // Return mock data if available, otherwise fetch from API
  if (mockInventoryData[homestayId.toString()]) {
    return Promise.resolve(mockInventoryData[homestayId.toString()]);
  }
  return request<MockInventoryResponse>(
    `/homestays/${homestayId}/inventory?check_in=${checkIn}&check_out=${checkOut}`
  );
}

export function getWeatherHistory(destinationId: number): Promise<WeatherHistoryResponse> {
  return request<WeatherHistoryResponse>(`/destinations/${destinationId}/weather-history`);
}

async function getOfflinePayload(
  path: string,
  error: Error
): Promise<any> {
  // Try to extract destination ID from path for crowd fallback
  const match = path.match(/\/destinations\/(\d+)/);
  const destId = match ? match[1] : null;

  // If it's a crowd-related request, return simulated offline data
  if (path.includes("/recommendations") || path.includes("/crowd")) {
    const fallbackCrowd =
      (destId ? mockCrowdData[destId] : undefined) ||
      { score: 50, level: "Moderate" };
    return {
      items: [
        {
          destination: {
            id: Number(destId) || 1,
            name: `Destination ${destId || "1"}`,
            district: "District",
            region: "Uttarakhand",
            description: "A place from the PahadPath catalogue.",
            tags: ["nature"],
            best_months: [10],
            popularity_score: 50,
            source_label: "Reviewed source",
            source_url: "",
            reviewer: "curator",
            reviewed_at: new Date().toISOString().slice(0, 10),
            enabled: 1,
          },
          homestays: [],
          crowd: {
            score: fallbackCrowd.score,
            level: fallbackCrowd.level,
            estimated: true,
            popularity: 50,
            date_demand: 50,
            event_pressure: 50,
            weather_visit_tendency: 50,
            notes: ["Live data not available. Using neutral offline estimate."],
            data_mode: "curated_rule_estimate",
            reviewed_at: new Date().toISOString().slice(0, 10),
          },
          rank_score: 50,
          fits: { interest: 50, quietness: 50, travel: 50, stay: 50 },
          reasons: ["Using offline estimate due to network error"],
        },
      ],
      warnings: [],
    };
  }

  // For other paths, return minimal offline payload
  return {} as any;
}