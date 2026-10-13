import { ArrowRight, CalendarDays, Compass, LoaderCircle } from "lucide-react";
import { useState, type FormEvent } from "react";
import { getRecommendations } from "../services/api";
import type { RecommendationRequest } from "../types/api";

interface Props {
  onResults: (request: RecommendationRequest, response: Awaited<ReturnType<typeof getRecommendations>>) => void;
}

const interestOptions = ["Nature", "Views", "Culture", "Quiet", "Slow-travel"];

export function buildRecommendationRequest(input: {
  date: string;
  days: number;
  interests: string[];
  budget: string;
  broaden: boolean;
}): RecommendationRequest {
  return {
    region: "Uttarakhand",
    start_date: input.date,
    days: input.days,
    interests: input.interests,
    ...(input.budget ? { budget_per_night_max: Number(input.budget) } : {}),
    avoid_crowds: true,
    allow_broadened_search: input.broaden,
  };
}

export function TripRequestForm({ onResults }: Props) {
  const [date, setDate] = useState(() => new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10));
  const [days, setDays] = useState(2);
  const [interests, setInterests] = useState<string[]>(["nature", "slow-travel"]);
  const [budget, setBudget] = useState("");
  const [broaden, setBroaden] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
    const request = buildRecommendationRequest({ date, days, interests, budget, broaden });
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
      <button className="button button-primary form-submit" type="submit" disabled={loading}>
        {loading ? <><LoaderCircle className="spin" size={18} /> Finding your quieter places…</> : <>Find my quieter places <ArrowRight size={17} /></>}
      </button>
      <p className="form-reassurance">No bookings, no rush. Just a considered place to begin.</p>
    </form>
  );
}
