import { ArrowRight, CalendarDays, Compass, LoaderCircle, MapPin } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { getDestinations, getRecommendations } from "../services/api";
import type { Destination, RecommendationRequest } from "../types/api";

interface Props {
  onResults: (request: RecommendationRequest, response: Awaited<ReturnType<typeof getRecommendations>>) => void;
}

const interestOptions = ["Nature", "Views", "Culture", "Quiet", "Slow-travel"];

export function TripRequestForm({ onResults }: Props) {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [startId, setStartId] = useState("");
  const [date, setDate] = useState(() => new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10));
  const [days, setDays] = useState(2);
  const [interests, setInterests] = useState<string[]>(["nature", "slow-travel"]);
  const [budget, setBudget] = useState("");
  const [broaden, setBroaden] = useState(true);
  const [catalogueLoading, setCatalogueLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getDestinations()
      .then((items) => {
        if (!active) return;
        setDestinations(items);
        if (items.length > 0) setStartId(String(items[0].id));
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "The catalogue could not be loaded.");
      })
      .finally(() => { if (active) setCatalogueLoading(false); });
    return () => { active = false; };
  }, []);

  function toggleInterest(value: string) {
    const normalized = value.toLowerCase();
    setInterests((current) => current.includes(normalized)
      ? current.filter((item) => item !== normalized)
      : [...current, normalized]);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    const request: RecommendationRequest = {
      region: "Uttarakhand",
      ...(startId ? { start_destination_id: Number(startId) } : {}),
      start_date: date,
      days,
      interests,
      ...(budget ? { budget_per_night_max: Number(budget) } : {}),
      avoid_crowds: true,
      allow_broadened_search: broaden,
    };
    try {
      const response = await getRecommendations(request);
      onResults(request, response);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "We couldn't make that trip plan.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="trip-form" onSubmit={submit}>
      <div className="form-heading">
        <div className="form-icon"><Compass size={19} /></div>
        <div><span className="eyebrow">Your next exhale</span><h2>Shape a little escape</h2></div>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <label className="field-label" htmlFor="starting-point"><MapPin size={15} /> Leaving from</label>
      <select id="starting-point" value={startId} onChange={(event) => setStartId(event.target.value)} disabled={catalogueLoading || destinations.length === 0}>
        {destinations.length === 0
          ? <option value="">No curated starting places yet</option>
          : destinations.map((place) => <option key={place.id} value={place.id}>{place.name}, {place.region}</option>)}
      </select>
      {destinations.length === 0 && !catalogueLoading && (
        <p className="field-hint">The curated catalogue is empty. Add reviewed places before planning.</p>
      )}

      <div className="field-grid">
        <div>
          <label className="field-label" htmlFor="start-date"><CalendarDays size={15} /> Start date</label>
          <input id="start-date" type="date" value={date} min={new Date().toISOString().slice(0, 10)} onChange={(event) => setDate(event.target.value)} required />
        </div>
        <div>
          <label className="field-label" htmlFor="trip-days">Days away</label>
          <select id="trip-days" value={days} onChange={(event) => setDays(Number(event.target.value))}>
            {[1, 2, 3, 4, 5, 6, 7].map((number) => <option key={number} value={number}>{number} {number === 1 ? "day" : "days"}</option>)}
          </select>
        </div>
      </div>

      <fieldset className="interest-fieldset">
        <legend className="field-label">What feels like you?</legend>
        <div className="chip-list">
          {interestOptions.map((item) => {
            const selected = interests.includes(item.toLowerCase());
            return <button className={`interest-chip${selected ? " selected" : ""}`} type="button" aria-pressed={selected} key={item} onClick={() => toggleInterest(item)}>{item}</button>;
          })}
        </div>
      </fieldset>

      <label className="field-label" htmlFor="budget">A nightly budget, if you have one <span className="optional">optional</span></label>
      <div className="budget-input"><span>₹</span><input id="budget" type="number" min="0" max="1000000" step="500" placeholder="Leave blank if flexible" value={budget} onChange={(event) => setBudget(event.target.value)} /></div>
      <label className="check-row">
        <input type="checkbox" checked={broaden} onChange={(event) => setBroaden(event.target.checked)} />
        <span>Widen the search if a quieter match isn't found</span>
      </label>
      <button className="button button-primary form-submit" type="submit" disabled={loading || catalogueLoading || !startId}>
        {loading ? <><LoaderCircle className="spin" size={18} /> Finding your quieter places…</> : <>Find my quieter places <ArrowRight size={17} /></>}
      </button>
      <p className="form-reassurance">No bookings, no rush. Just a considered place to begin.</p>
    </form>
  );
}
