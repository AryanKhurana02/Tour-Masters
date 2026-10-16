export interface Destination {
  id: number;
  name: string;
  district: string;
  region: string;
  description: string;
  tags: string[];
  best_months: number[];
  popularity_score: number | null;
  source_label: string;
  source_url: string | null;
  reviewer: string;
  reviewed_at: string;
}

export interface DestinationDetail extends Destination {
  alternatives: Array<{
    destination: Destination;
    match_tags: string[];
    travel_fit: number | null;
    source_label: string;
    source_url: string | null;
    reviewer: string;
    reviewed_at: string;
  }>;
}

export interface Homestay {
  id: number;
  destination_id: number;
  name: string;
  village: string;
  nightly_min: number | null;
  nightly_max: number | null;
  currency: string | null;
  public_contact: string | null;
  booking_url: string | null;
  amenities: string[];
  source_label: string;
  source_url: string | null;
  reviewer: string;
  reviewed_at: string;
}

export interface MockInventoryDay {
  homestay_id: number;
  date: string;
  total_units: number;
  available_units: number;
  inventory_mode: "demo_mock";
  source_label: string;
  reviewed_at: string;
}

export interface MockInventoryResponse {
  homestay_id: number;
  check_in: string;
  check_out: string;
  inventory_mode: "demo_mock";
  days: MockInventoryDay[];
  warnings: string[];
}

export interface DemoBookingRequest {
  homestay_id: number;
  check_in: string;
  check_out: string;
  guest_count: number;
  client_request_id: string;
}

export interface DemoBookingReceipt {
  request_id: string;
  client_request_id: string;
  homestay_id: number;
  check_in: string;
  check_out: string;
  guest_count: number;
  status: "demo_submitted";
  inventory_mode: "demo_mock";
  non_binding: true;
  created_at: string;
}

export interface SavedStayRequest {
  type: "stay_request";
  id: string;
  saved_at: string;
  title: string;
  receipt: DemoBookingReceipt;
  stay: Homestay;
  destination: Destination;
  crowd: CrowdEstimate;
}

export interface HistoricalWeatherSignal {
  month: number;
  avg_precipitation_mm?: number;
  avg_temp_max_c?: number;
  avg_temp_min_c?: number;
  avg_cloud_cover_pct?: number;
  avg_wind_speed_kmh?: number;
  wet_day_probability?: number;
  landslide_risk_probability?: number;
  friction?: number;
  visit_tendency?: number;
  hci_score?: number;
  source?: string;
  note?: string;
}

export interface SafetyAlert {
  severity: "medium" | "high";
  landslide_risk_probability?: number;
  wet_day_probability?: number;
  message: string;
}

export interface CrowdEstimate {
  score: number;
  level: "Quiet" | "Moderate" | "Busy" | "Very busy";
  estimated: true;
  popularity: number;
  date_demand: number;
  event_pressure: number;
  weather_visit_tendency: number;
  notes: string[];
  data_mode: "curated_rule_estimate";
  reviewed_at: string;
  friction_cue?: {
    cue_type: "weather_warning" | "road_bottleneck" | "water_scarcity" | "resting";
    message: string;
    severity: "low" | "medium" | "high";
  };
  historical_weather?: HistoricalWeatherSignal;
  safety_alert?: SafetyAlert;
}

export interface RecommendationItem {
  destination: Destination;
  homestays: Homestay[];
  crowd: CrowdEstimate;
  rank_score: number;
  fits: {
    interest: number;
    quietness: number;
    travel: number;
    stay: number;
  };
  reasons: string[];
}

export interface RecommendationRequest {
  region: string;
  start_destination_id?: number;
  start_date: string;
  days: number;
  interests: string[];
  budget_per_night_max?: number;
  avoid_crowds: boolean;
  allow_broadened_search: boolean;
}

export interface RecommendationResponse {
  request_id: string;
  items: RecommendationItem[];
  warnings: string[];
}

export interface RouteEstimate {
  destination_id: number;
  origin_label: "Dehradun hub";
  destination_name: string;
  distance_meters: number;
  duration_seconds: number;
  estimated: true;
  source: "OpenRouteService";
  retrieved_at: string;
  notes: string[];
}

export interface HolidayCrowdData {
  holidayName: string;
  date: string;
  mostCrowded: string[];
  leastCrowded: string[];
  crowdCategory: string;
}

export interface MonthlyClimatology {
  destination_id: string;
  month: number;
  avg_precipitation_mm: number;
  avg_rain_mm: number;
  avg_snowfall_cm: number;
  avg_temp_max_c: number;
  avg_temp_min_c: number;
  avg_cloud_cover_pct: number;
  avg_wind_speed_kmh: number;
  wet_day_probability: number;
  landslide_risk_probability: number;
  friction: number;
  visit_tendency: number;
  hci_score: number;
  sample_days: number;
  source: string;
  note: string;
}

export interface SeasonalityData {
  month_name: string;
  month: number;
  domestic_index: number;
  foreign_index: number;
  combined_index: number;
  activity_focus: string;
  weather_condition: string;
}

export interface WeatherHistoryResponse {
  destination_id: number;
  destination_name: string;
  monthly_climatology: MonthlyClimatology[];
  seasonality: SeasonalityData[];
}

export interface ItineraryBlock {
  period: "morning" | "afternoon" | "evening";
  text: string;
}

export interface ItineraryDay {
  day_number: number;
  date: string;
  destination_id: number;
  destination_name: string;
  homestay_id: number | null;
  homestay_name: string | null;
  crowd: CrowdEstimate;
  blocks: ItineraryBlock[];
  warnings: string[];
}

export interface ItineraryResponse {
  request_id: string;
  generation_mode: "rule_fallback" | "llm_text_assisted";
  days: ItineraryDay[];
  warnings: string[];
}

export interface ItineraryRequest {
  start_date: string;
  days: number;
  destination_ids: number[];
  homestay_ids: Array<number | null>;
  budget_per_night_max?: number;
  use_llm: false;
}

export interface SavedTripRecord {
  id: string;
  saved_at: string;
  title: string;
  request: ItineraryRequest;
  itinerary: ItineraryResponse;
  destinations: Destination[];
  homestays: Homestay[];
}

export type SavedTrip = SavedTripRecord | SavedStayRequest;
