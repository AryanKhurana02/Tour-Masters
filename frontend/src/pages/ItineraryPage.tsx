import { ArrowLeft, Bookmark, Check, LoaderCircle, Save, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ItineraryView } from "../components/ItineraryView";
import { saveTrip } from "../services/offlineStore";
import type { ItineraryRequest, ItineraryResponse, Destination, Homestay, SavedTrip } from "../types/api";
import { formatDate, isDemoRecord } from "../utils/presentation";

interface ItineraryState {
  request: ItineraryRequest;
  itinerary: ItineraryResponse;
  destinations: Destination[];
  homestays: Homestay[];
  resultsState: {
    request: import("../types/api").RecommendationRequest;
    response: import("../types/api").RecommendationResponse;
  };
}

export function ItineraryPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = location.state as ItineraryState | null;
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  if (!routeState) {
    return <section className="page-empty"><Bookmark size={28} /><h1>Your plan is ready when you are.</h1><p>Choose a place from your shortlist to shape the day-by-day outline.</p><Link to="/" className="button button-primary">Plan a trip</Link></section>;
  }
  const state = routeState;

  async function saveForOffline() {
    setSaving(true);
    setError("");
    try {
      const trip: SavedTrip = {
        id: crypto.randomUUID(),
        saved_at: new Date().toISOString(),
        title: `${state.itinerary.days[0].destination_name} · ${state.itinerary.days.length} ${state.itinerary.days.length === 1 ? "day" : "days"}`,
        request: state.request,
        itinerary: state.itinerary,
        destinations: state.destinations.filter((destination) => state.itinerary.days.some((day) => day.destination_id === destination.id)),
        homestays: state.homestays.filter((homestay) => state.itinerary.days.some((day) => day.homestay_id === homestay.id)),
      };
      await saveTrip(trip);
      setSaved(true);
      navigate(`/saved/${trip.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "This plan couldn't be saved on this device.");
    } finally {
      setSaving(false);
    }
  }

  const usesDemo = state.destinations.some((destination) => isDemoRecord(destination.source_label));
  return (
    <div className="content-page">
      <Link className="back-link" to="/results" state={state.resultsState}><ArrowLeft size={15} /> Back to places</Link>
      <section className="itinerary-intro">
        <span className="eyebrow"><Sparkles size={14} /> A gentle outline</span>
        <h1>Your days,<br /><em>unhurried.</em></h1>
        <p>{formatDate(state.itinerary.days[0].date)} <span>·</span> {state.itinerary.days.length} days <span>·</span> {state.itinerary.generation_mode === "rule_fallback" ? "Thoughtful template" : "Text-assisted outline"}</p>
        <span className="mode-label"><Check size={14} /> Place, dates and structure validated by PahadPath</span>
      </section>
      {state.itinerary.warnings.map((warning) => <div className="warning-card" role="status" key={warning}><Sparkles size={17} />{warning}</div>)}
      <ItineraryView itinerary={state.itinerary} />
      {usesDemo && <p className="inline-demo-label">Illustrative sample records are included in this plan.</p>}
      <div className="itinerary-save-panel">
        <div className="save-seal"><Bookmark size={19} /></div>
        <div><strong>Keep this plan close.</strong><p>Save it on this device and reopen it when you're offline. No booking details or live availability are implied.</p></div>
        <button className="button button-primary" type="button" disabled={saving || saved} onClick={() => void saveForOffline()}>
          {saving ? <><LoaderCircle size={16} className="spin" /> Saving…</> : saved ? <>Saved <Check size={16} /></> : <><Save size={16} /> Save for offline</>}
        </button>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <p className="itinerary-disclaimer">This is a flexible outline, not a route, booking, weather forecast or guarantee of availability. Check local conditions before travel.</p>
    </div>
  );
}
