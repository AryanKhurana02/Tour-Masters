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
} from "../types/api";

const apiRoot = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

interface ApiError {
  error?: {
    message?: string;
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiRoot}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new Error("We couldn't reach the trip desk. Check your connection and try again.");
  }

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

export function getDestinations(): Promise<
  Destination[]
> {
  return request<Destination[]>("/destinations");
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

export function getHomestays(destinationId: number): Promise<Homestay[]> {
  return request<Homestay[]>(`/homestays?destination_id=${destinationId}`);
}

export function getMockInventory(
  homestayId: number,
  checkIn: string,
  checkOut: string,
): Promise<MockInventoryResponse> {
  const params = new URLSearchParams({ check_in: checkIn, check_out: checkOut });
  return request<MockInventoryResponse>(
    `/homestays/${homestayId}/inventory?${params.toString()}`,
  );
}

export function submitDemoBooking(
  input: DemoBookingRequest,
): Promise<DemoBookingReceipt> {
  return request<DemoBookingReceipt>("/booking-requests", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
