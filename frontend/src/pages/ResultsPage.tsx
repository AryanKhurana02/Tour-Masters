import { ArrowLeft, ArrowRight, Compass, LoaderCircle, MapPin, Route, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { CrowdBreakdown } from "../components/CrowdBreakdown";
import { SafetyAlertCard } from "../components/SafetyAlertCard";
import { StayCard } from "../components/StayCard";
import { createItinerary, getRouteFromHub } from "../services/api";
import type { RecommendationRequest, RecommendationResponse, RouteEstimate } from "../types/api";
import { formatDate } from "../utils/presentation";
import { DemoNotice } from "../components/DemoNotice";

interface ResultsState {
  request: RecommendationRequest;
  response: RecommendationResponse;
}

export function ResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = location.state as ResultsState | null;
  const [creatingId, setCreatingId] = useState<number | null>(null);
  const [routeLoadingId, setRouteLoadingId] = useState<number | null>(null);
  const [routes, setRoutes] = useState<Record<number, RouteEstimate>>({});
  const [routeErrors, setRouteErrors] = useState<Record<number, string>>({});
  const [error, setError] = useState("");

  if (!routeState) {
    return <section className="page-empty"><Compass size={28} /><h1>Let's find a stay.</h1><p>Start with your trip details to see quieter places and local homestays.</p><Link className="button button-primary" to="/plan">Plan a trip <ArrowRight size={16} /></Link></section>;
  }
  const state = routeState;

  async function loadRoute(destinationId: number) {
    setRouteLoadingId(destinationId);
    setRouteErrors((current) => {
      const next = { ...current };
      delete next[destinationId];
      return next;
    });
    try {
      const route = await getRouteFromHub(destinationId);
      setRoutes((current) => ({ ...current, [destinationId]: route }));
    } catch (cause) {
      setRouteErrors((current) => ({
        ...current,
        [destinationId]: cause instanceof Error ? cause.message : "The route estimate could not be loaded.",
      }));
    } finally {
      setRouteLoadingId(null);
    }
  }

  async function planDays(destinationId: number) {
    setCreatingId(destinationId);
    setError("");
    try {
      const itinerary = await createItinerary({
        start_date: state.request.start_date,
        days: state.request.days,
        destination_ids: [destinationId],
        homestay_ids: [null],
        ...(state.request.budget_per_night_max !== undefined
          ? { budget_per_night_max: state.request.budget_per_night_max }
          : {}),
        use_llm: false,
      });
      navigate("/itinerary", {
        state: {
          request: {
            start_date: state.request.start_date,
            days: state.request.days,
            destination_ids: [destinationId],
            homestay_ids: [null],
            ...(state.request.budget_per_night_max !== undefined
              ? { budget_per_night_max: state.request.budget_per_night_max }
              : {}),
            use_llm: false as const,
          },
          resultsState: state,
          itinerary,
          destinations: state.response.items.map((item) => item.destination),
          homestays: state.response.items.flatMap((item) => item.homestays),
        },
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "We couldn't shape this itinerary.");
    } finally {
      setCreatingId(null);
    }
  }

  return (
    <div className="content-page">
      <Link className="back-link" to="/plan"><ArrowLeft size={15} /> Change your trip</Link>
      <section className="results-heading">
        <span className="eyebrow">Quieter matches · Uttarakhand</span>
        <h1>Stay a little<br className="mobile-break" /> <em>slower.</em></h1>
        <p>For {formatDate(state.request.start_date)} <span>·</span> {state.request.days} {state.request.days === 1 ? "day" : "days"} <span>·</span> Uttarakhand</p>
      </section>
      {state.response.warnings.map((warning) => <div className="warning-card" role="status" key={warning}><Sparkles size={17} />{warning}</div>)}
      {error && <div className="form-error" role="alert">{error}</div>}
      {state.response.items.length === 0 ? (
        <section className="empty-results">
          <div className="empty-icon"><MapPin size={23} /></div>
          <h2>No homestays match this search yet.</h2>
          <p>There are no stays in the current catalogue for these matches. Try another date or adjust your interests.</p>
          <Link to="/plan" className="button button-outline">Change your trip <ArrowRight size={16} /></Link>
        </section>
      ) : (
        <div className="results-list">
          {state.response.items.map((item, index) => {
            return (
              <section className="match-group" key={item.destination.id}>
                <div className="match-heading">
                  <span className="match-number">0{index + 1}</span>
                  <div>
                    <span className="eyebrow"><MapPin size={13} /> {item.destination.district}, {item.destination.region}</span>
                    <h2>{item.destination.name}</h2>
                    <p>{item.destination.description}</p>
                  </div>
                  <span className="rank-pill"><Sparkles size={13} /> Match {Math.round(item.rank_score)}</span>
                </div>
                <div className="match-estimate"><CrowdBreakdown crowd={item.crowd} animate={index === 0} /></div>
                {item.crowd.safety_alert && <SafetyAlertCard alert={item.crowd.safety_alert} />}
                <ul className="reason-list">{item.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                <section className="route-context" aria-label={`Route context for ${item.destination.name}`}>
                  {item.destination.name === "Mussoorie" && (
                    <>
                      <button
                        className="button button-outline"
                        type="button"
                        disabled={routeLoadingId === item.destination.id}
                        onClick={() => void loadRoute(item.destination.id)}
                      >
                        {routeLoadingId === item.destination.id
                          ? <><LoaderCircle size={16} className="spin" /> Checking route…</>
                          : <><Route size={16} /> Driving estimate from Dehradun</>}
                      </button>
                      {routes[item.destination.id] && (
                        <div className="route-context-result" role="status">
                          <strong>
                            {(routes[item.destination.id].distance_meters / 1000).toFixed(1)} km
                            {" · "}
                            {Math.floor(routes[item.destination.id].duration_seconds / 3600) > 0
                              ? `${Math.floor(routes[item.destination.id].duration_seconds / 3600)} hr ${Math.round((routes[item.destination.id].duration_seconds % 3600) / 60)} min`
                              : `${Math.round(routes[item.destination.id].duration_seconds / 60)} min`}
                            {" · estimated"}
                          </strong>
                          <small>{routes[item.destination.id].notes.join(" ")}</small>
                        </div>
                      )}
                      {routeErrors[item.destination.id] && (
                        <p className="form-error" role="alert">{routeErrors[item.destination.id]}</p>
                      )}
                    </>
                  )}
                </section>
                {item.homestays.length ? (
                  <div className="stay-card-list">
                    {item.homestays.map((stay) => (
                      <StayCard
                        key={stay.id}
                        stay={stay}
                        destination={item.destination}
                        crowd={item.crowd}
                        request={state.request}
                        rankScore={item.rank_score}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="no-stays">No homestays are listed for this place yet.</p>
                )}
                <div className="match-footer">
                  <span>Estimate reviewed {formatDate(item.destination.reviewed_at)}</span>
                  <button className="button button-outline" type="button" disabled={creatingId !== null} onClick={() => void planDays(item.destination.id)}>
                    {creatingId === item.destination.id ? <><LoaderCircle size={16} className="spin" /> Making outline…</> : <>Make a trip outline <ArrowRight size={16} /></>}
                  </button>
                </div>
              </section>
            );
          })}
        </div>
      )}
      <DemoNotice />
    </div>
  );
}
