import { ArrowRight, Bookmark, Clock3, MapPin, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { deleteSavedTrip, listSavedTrips } from "../services/offlineStore";
import type { SavedTrip } from "../types/api";
import { formatDate, isSavedStayRequest } from "../utils/presentation";

export function SavedTripsPage() {
  const [trips, setTrips] = useState<SavedTrip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh() {
    try {
      setTrips(await listSavedTrips());
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Saved plans couldn't be opened.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function remove(id: string) {
    try {
      await deleteSavedTrip(id);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "This saved plan couldn't be removed.");
    }
  }

  return (
    <div className="content-page saved-page">
      <section className="saved-heading">
        <span className="eyebrow"><Bookmark size={14} /> Saved on this device</span>
        <h1>Your saved<br /><em>stays.</em></h1>
        <p>Open your saved trip plans and demo requests, even when the signal wanders off.</p>
      </section>
      {error && <p className="form-error" role="alert">{error}</p>}
      {loading ? <div className="saved-empty">Opening your saved plans…</div> : trips.length === 0 ? (
        <div className="empty-results saved-empty">
          <div className="empty-icon"><Bookmark size={22} /></div>
          <h2>No saved stays yet.</h2>
          <p>Send a demo request or save a trip outline to keep it on this device.</p>
          <Link className="button button-primary" to="/plan">Plan a trip <ArrowRight size={16} /></Link>
        </div>
      ) : (
        <div className="saved-list">
          {trips.map((trip) => {
            const stayRequest = isSavedStayRequest(trip) ? trip : undefined;
            const legacyTrip = isSavedStayRequest(trip) ? undefined : trip;
            const destinationName = stayRequest?.destination.name ?? legacyTrip?.itinerary.days[0]?.destination_name ?? "Saved trip";
            const tripDate = stayRequest?.receipt.check_in ?? legacyTrip?.itinerary.days[0]?.date;
            const duration = stayRequest
              ? `${stayRequest.receipt.guest_count} ${stayRequest.receipt.guest_count === 1 ? "guest" : "guests"}`
              : `${legacyTrip?.itinerary.days.length ?? 0} days`;
            return <article className="saved-trip-card" key={trip.id}>
              <div className="saved-trip-art" aria-hidden="true"><span>PP</span><i /></div>
              <div className="saved-trip-copy">
                <span className="eyebrow"><MapPin size={13} /> {destinationName}</span>
                <h2>{trip.title}</h2>
                <p>{tripDate ? formatDate(tripDate) : "Date not available"} <span>·</span> {duration}</p>
                <small><Clock3 size={13} /> Saved {new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(trip.saved_at))}</small>
                {stayRequest && <span className="demo-inline">Demo request · not a reservation</span>}
              </div>
              <div className="saved-actions">
                <Link className="button button-primary" to={`/saved/${trip.id}`}>Open saved details <ArrowRight size={15} /></Link>
                <button className="icon-button" type="button" aria-label={`Delete ${trip.title}`} onClick={() => void remove(trip.id)}><Trash2 size={17} /></button>
              </div>
            </article>;
          })}
        </div>
      )}
    </div>
  );
}
