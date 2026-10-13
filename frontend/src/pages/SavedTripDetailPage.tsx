import { ArrowLeft, Bookmark, Clock3 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { DemoNotice } from "../components/DemoNotice";
import { CrowdBreakdown } from "../components/CrowdBreakdown";
import { ItineraryView } from "../components/ItineraryView";
import { getSavedTrip } from "../services/offlineStore";
import type { SavedTrip } from "../types/api";
import { formatDate, isDemoRecord, isSavedStayRequest } from "../utils/presentation";

export function SavedTripDetailPage() {
  const { id } = useParams();
  const [trip, setTrip] = useState<SavedTrip>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    let active = true;
    getSavedTrip(id)
      .then((saved) => { if (active) setTrip(saved); })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : "Saved plan couldn't be opened."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  if (loading) return <div className="page-empty">Opening your saved plan…</div>;
  if (error) return <div className="page-empty"><p className="form-error" role="alert">{error}</p><Link to="/saved" className="button button-outline">Saved journeys</Link></div>;
  if (!trip) return <div className="page-empty"><Bookmark size={26} /><h1>This saved plan isn't on this device.</h1><p>It may have been removed or cleared from browser storage.</p><Link to="/saved" className="button button-outline">Back to saved journeys</Link></div>;

  if (isSavedStayRequest(trip)) {
    return (
      <div className="content-page saved-detail">
        <Link className="back-link" to="/saved"><ArrowLeft size={15} /> All saved stays</Link>
        <section className="itinerary-intro">
          <span className="eyebrow"><Bookmark size={14} /> Saved on this device</span>
          <h1>{trip.destination.name},<br /><em>unhurried.</em></h1>
          <p>{trip.stay.name} <span>·</span> {formatDate(trip.receipt.check_in)} – {formatDate(trip.receipt.check_out)}</p>
          <span className="mode-label"><Clock3 size={14} /> Saved {new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(trip.saved_at))}</span>
        </section>
        <section className="saved-request-card" aria-label="Demo request status">
          <span className="mock-tag">Demo request · not a reservation</span>
          <h2>Your request is saved.</h2>
          <p>This sample request does not reserve a room. The dates and unit counts are mock data, and no host has been contacted.</p>
          <dl>
            <div><dt>Stay</dt><dd>{trip.stay.name}</dd></div>
            <div><dt>Guests</dt><dd>{trip.receipt.guest_count}</dd></div>
            <div><dt>Request status</dt><dd>Demo submitted</dd></div>
          </dl>
        </section>
        <CrowdBreakdown crowd={trip.crowd} />
      </div>
    );
  }
  const demo = trip.destinations.some((destination) => isDemoRecord(destination.source_label));
  return (
    <div className="content-page saved-detail">
      <Link className="back-link" to="/saved"><ArrowLeft size={15} /> All saved journeys</Link>
      <section className="itinerary-intro">
        <span className="eyebrow"><Bookmark size={14} /> Saved on this device</span>
        <h1>{trip.itinerary.days[0].destination_name},<br /><em>unhurried.</em></h1>
        <p>{formatDate(trip.itinerary.days[0].date)} <span>·</span> {trip.itinerary.days.length} days</p>
        <span className="mode-label"><Clock3 size={14} /> Saved {new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(trip.saved_at))}</span>
      </section>
      {trip.itinerary.warnings.map((warning) => <div className="warning-card" role="status" key={warning}>{warning}</div>)}
      <ItineraryView itinerary={trip.itinerary} />
      {demo && <p className="inline-demo-label">Illustrative sample records are included in this saved plan.</p>}
      <p className="itinerary-disclaimer">Offline snapshot saved on this device. Availability, prices, contacts and conditions may change or be unknown.</p>
    </div>
  );
}
