import { ArrowLeft, LoaderCircle, MapPin, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { CrowdBreakdown } from "../components/CrowdBreakdown";
import { LiveCrowdMeter } from "../components/LiveCrowdMeter";
import { HolidayCrowdOverview } from "../components/HolidayCrowdOverview";
import { FrictionCueBadge } from "../components/FrictionCueBadge";
import { DataHonestyCue } from "../components/DataHonestyCue";
import { MonthStrip } from "../components/MonthStrip";
import { StayBookingPanel } from "../components/StayBookingPanel";
import { WeatherHistorySection } from "../components/WeatherHistorySection";
import { getDestination, getHomestays, getWeatherHistory } from "../services/api";
import type {
  CrowdEstimate,
  Destination,
  Homestay,
  RecommendationRequest,
  HolidayCrowdData,
  WeatherHistoryResponse,
} from "../types/api";
import { formatDate } from "../utils/presentation";

interface PlaceState {
  destination?: Destination | null;
  stay?: Homestay | null;
  crowd?: CrowdEstimate | null;
  request?: RecommendationRequest | null;
  holidays?: HolidayCrowdData[] | null;
  frictionCue?: FrictionCue | null;
}

type FrictionCue = {
  cue_type: "weather_warning" | "road_bottleneck" | "water_scarcity" | "resting";
  message: string;
  severity: "low" | "medium" | "high";
};

export function PlacePage() {
  const { id } = useParams();
  const location = useLocation();
  const routeState = location.state as PlaceState | null;
  const destinationId = Number(id);
  const [destination, setDestination] = useState<Destination | null>(routeState?.destination ?? null);
  const [stays, setStays] = useState<Homestay[] | null>(routeState?.stay ? [routeState.stay] : null);
  const [crowd, setCrowd] = useState<CrowdEstimate | null>(routeState?.crowd ?? null);
  const [loading, setLoading] = useState(!routeState?.destination);
  const [error, setError] = useState("");
  const [holidays, setHolidays] = useState<HolidayCrowdData[] | null>(null);
  const [frictionCue, setFrictionCue] = useState<FrictionCue | null>(null);
  const [weatherHistory, setWeatherHistory] = useState<WeatherHistoryResponse | null>(null);
  const checkIn = routeState?.request?.start_date
    ?? new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
  const nights = routeState?.request?.days ?? 2;

  useEffect(() => {
    const fetchHolidays = async () => {
      const sampleData: HolidayCrowdData[] = [
        {
          holidayName: "Diwali",
          date: "2026-11-07",
          mostCrowded: ["Mussoorie", "Nainital", "Rishikesh"],
          leastCrowded: ["Jageshwar", "Lohaghat", "Abbott Mount"],
          crowdCategory: "Festival Season Peak",
        },
        {
          holidayName: "Christmas",
          date: "2026-12-25",
          mostCrowded: ["Mussoorie", "Nainital", "Auli", "Rishikesh"],
          leastCrowded: ["Pauri", "Almora", "Chaukori"],
          crowdCategory: "Year-End Peak",
        },
        {
          holidayName: "Holi",
          date: "2026-03-03",
          mostCrowded: ["Nainital", "Mussoorie", "Dehradun"],
          leastCrowded: ["Pangot", "Mukteshwar", "Kanatal"],
          crowdCategory: "Long-Weekend Surge",
        },
        {
          holidayName: "Independence Day",
          date: "2026-08-15",
          mostCrowded: ["Mussoorie Mall Road", "Nainital Lake", "Rishikesh Ghats"],
          leastCrowded: ["Dhanaulti", "Bhimtal", "Ramgarh"],
          crowdCategory: "Monsoon Weekend Peak",
        },
      ];
      setHolidays(sampleData);
    };
    fetchHolidays();
  }, [destinationId]);

  useEffect(() => {
    if (crowd && crowd.score >= 60) {
      const cues: FrictionCue[] = [
        {
          cue_type: "weather_warning",
          message: "Heavy rain expected. Trail conditions may be slippery.",
          severity: "medium",
        },
        {
          cue_type: "road_bottleneck",
          message: "Access road congestion expected during peak hours.",
          severity: "low",
        },
      ];
      const severityOrder: Record<string, number> = { low: 1, medium: 2, high: 3 };
      const worst = cues.reduce(
        (worst, current) =>
          severityOrder[current.severity] > severityOrder[worst.severity]
            ? current
            : worst,
        cues[0]
      );
      setFrictionCue(worst);
    } else if (crowd && crowd.score < 35) {
      setFrictionCue({
        cue_type: "resting",
        message: "Quiet conditions ideal for meditation and nature walks.",
        severity: "low",
      });
    }
  }, [crowd]);

  useEffect(() => {
    const fetchDestination = async () => {
      try {
        const [place, homestays, weatherHist] = await Promise.all([
          getDestination(destinationId),
          getHomestays(destinationId),
          getWeatherHistory(destinationId).catch(() => null),
        ]);
        setDestination(place ?? null);
        setStays(homestays ?? []);
        setWeatherHistory(weatherHist);
      } catch (err) {
        setError("This place could not be loaded.");
        setDestination(null);
        setStays([]);
      } finally {
        setLoading(false);
      }
    };
    fetchDestination();
  }, [destinationId]);

  if (loading) {
    return (
      <div className="content-page place-page loading">
        <LoaderCircle size={32} className="spinner" />
        <p>Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="content-page place-page error">
        <p>{error}</p>
        <Link className="btn" to="/results">Back to results</Link>
      </div>
    );
  }

  const targetMonth = new Date(checkIn).getMonth() + 1;

  return (
    <div className="content-page place-page">
      <Link className="back-link" to="/results"><ArrowLeft size={15} /> Back to results</Link>

      <header className="place-heading">
        <span className="eyebrow"><MapPin size={14} /> {destination?.district}, {destination?.region}</span>
        <h1>{destination?.name}</h1>
        <p>{destination?.description ?? "Uttarakhand destination."}</p>
        <div className="tag-list">
          {destination?.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}
        </div>
      </header>

      <section className="place-crowd">
        <div className="crowd-header">
          <h2>Crowd estimate for {formatDate(checkIn)}</h2>
          <LiveCrowdMeter destinationId={destinationId} />
        </div>
        {crowd ? (
          <>
            <CrowdBreakdown crowd={crowd} />
            {frictionCue && <FrictionCueBadge cue={frictionCue} />}
          </>
        ) : (
          <p className="quiet">Select dates from trip results to see the estimate.</p>
        )}
      </section>

      {holidays && <HolidayCrowdOverview holidays={holidays} />}

      {weatherHistory && destination && (
        <WeatherHistorySection
          destinationName={destination.name}
          historicalWeather={
            crowd?.historical_weather
            ?? weatherHistory.monthly_climatology.find((m) => m.month === targetMonth)
          }
          seasonality={weatherHistory.seasonality.find((s) => s.month === targetMonth)}
          targetMonth={targetMonth}
        />
      )}

      <section className="place-stays">
        <div className="section-heading">
          <span className="eyebrow">HOMESTAYS</span>
          <h2>Places to stay</h2>
        </div>
        {!stays || stays.length === 0 ? (
          <div className="empty-results"><Sparkles size={20} /><h3>No homestays listed yet.</h3></div>
        ) : (
          stays.map((stay) => (
            <article className="stay-detail-card" key={stay.id}>
              <div className="stay-card-heading">
                <div>
                  <span className="eyebrow">
                    {stay.village || destination?.district || ""}
                  </span>
                  <h3>{stay.name}</h3>
                </div>
              </div>
              <p className="stay-facts">
                {stay.nightly_min === null
                  ? "Price on request"
                  : `${stay.currency ?? "₹"} ${stay.nightly_min}${
                      stay.nightly_max !== null ? `–${stay.nightly_max}` : "+"
                    } / night`}
                · {stay.amenities.length ? stay.amenities.join(" · ") : "Amenities not listed"}
              </p>
              {crowd && destination && (
                <StayBookingPanel
                  stay={stay}
                  destination={destination}
                  crowd={crowd}
                  initialCheckIn={checkIn}
                  initialNights={nights}
                />
              )}
            </article>
          ))
        )}
      </section>

      <DataHonestyCue reviewedAt={destination?.reviewed_at ?? new Date().toISOString().slice(0, 10)} dataMode="curated_rule_estimate" />
    </div>
  );
}