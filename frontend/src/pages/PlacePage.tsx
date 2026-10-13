import { ArrowLeft, LoaderCircle, MapPin, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { CrowdBreakdown } from "../components/CrowdBreakdown";
import { LiveCrowdMeter } from "../components/LiveCrowdMeter";
import { MonthStrip } from "../components/MonthStrip";
import { StayBookingPanel } from "../components/StayBookingPanel";
import { getDestination, getHomestays } from "../services/api";
import type { CrowdEstimate, Destination, Homestay, RecommendationRequest } from "../types/api";
import { formatDate } from "../utils/presentation";

interface PlaceState {
  destination?: Destination;
  stay?: Homestay;
  crowd?: CrowdEstimate;
  request?: RecommendationRequest;
}

export function PlacePage() {
  const { id } = useParams();
  const location = useLocation();
  const routeState = location.state as PlaceState | null;
  const destinationId = Number(id);
  const [destination, setDestination] = useState<Destination | undefined>(routeState?.destination);
  const [stays, setStays] = useState<Homestay[]>(routeState?.stay ? [routeState.stay] : []);
  const [crowd] = useState(routeState?.crowd);
  const [loading, setLoading] = useState(!routeState?.destination);
  const [error, setError] = useState("");
  const checkIn = routeState?.request?.start_date
    ?? new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
  const nights = routeState?.request?.days ?? 2;

  useEffect(() => {
    if (!Number.isInteger(destinationId) || destinationId < 1) {
      setError("This place could not be found.");
      setLoading(false);
      return;
    }
    let active = true;
    Promise.all([getDestination(destinationId), getHomestays(destinationId)])
      .then(([place, homestays]) => {
        if (!active) return;
        setDestination(place);
        setStays(routeState?.stay ? [routeState.stay] : homestays);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "Place details could not be loaded.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [destinationId]);

  if (loading) return <section className="page-empty"><LoaderCircle className="spin" size={24} /> Opening stay details…</section>;
  if (error || !destination) {
    return <section className="page-empty"><h1>We couldn't open this stay.</h1><p>{error || "This place is not in the catalogue."}</p><Link className="button button-primary" to="/">Return to the trip form</Link></section>;
  }
  return (
    <div className="content-page place-page">
      <Link className="back-link" to="/results"><ArrowLeft size={15} /> Back to quieter matches</Link>
      <header className="place-heading">
        <span className="eyebrow"><MapPin size={14} /> {destination.district}, {destination.region}</span>
        <h1>{destination.name},<br /><em>unhurried.</em></h1>
        <p>{destination.description || "A place from the PahadPath catalogue."}</p>
        <div className="tag-list">{destination.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div>
      </header>
      <section className="place-months"><h2>When this place is usually listed</h2><MonthStrip months={destination.best_months} /></section>
      <section className="place-crowd">
        <h2>Estimated crowd for {formatDate(checkIn)}</h2>
        {crowd ? <CrowdBreakdown crowd={crowd} /> : <p>Choose this place from trip results to see its backend estimate for your date.</p>}
        <LiveCrowdMeter destinationId={destinationId} />
      </section>
      <section className="place-stays">
        <div className="section-heading">
          <span className="eyebrow">LOCAL HOMESTAYS</span>
          <h2>Find a gentler place to stay.</h2>
          <p>Dates and rooms shown here are mock samples. A request is not a reservation.</p>
        </div>
        {stays.length === 0 ? (
          <div className="empty-results"><Sparkles size={20} /><h3>No homestays listed yet.</h3><p>We only show stays present in the catalogue.</p></div>
        ) : stays.map((stay) => (
          <article className="stay-detail-card" key={stay.id}>
            <div className="stay-card-heading"><div><span className="eyebrow">{stay.village || destination.district}</span><h3>{stay.name}</h3></div><span className="mock-tag">Demo listing</span></div>
            <p className="stay-facts">{stay.nightly_min === null ? "Price not listed" : `${stay.currency ?? ""} ${stay.nightly_min}${stay.nightly_max !== null ? `–${stay.nightly_max}` : "+"} per night`} · {stay.amenities.length ? stay.amenities.join(" · ") : "Amenities not listed"}</p>
            {crowd && <StayBookingPanel stay={stay} destination={destination} crowd={crowd} initialCheckIn={checkIn} initialNights={nights} />}
          </article>
        ))}
      </section>
    </div>
  );
}
