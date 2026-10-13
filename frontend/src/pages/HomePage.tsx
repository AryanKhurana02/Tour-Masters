import { ArrowDown, ArrowRight, Leaf, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { LandingStayExample } from "../components/LandingStayExample";
import { TripRequestForm } from "../components/TripRequestForm";
import type { RecommendationRequest, RecommendationResponse } from "../types/api";

export function HomePage() {
  const navigate = useNavigate();

  function showResults(request: RecommendationRequest, response: RecommendationResponse) {
    navigate("/results", { state: { request, response } });
  }

  return (
    <div className="home-page">
      <section className="hero-section">
        <div className="hero-copy">
          <div className="hero-kicker"><span /> FOR THE HILLS</div>
          <h1>Stay on the<br />quieter <em>side.</em></h1>
          <p className="hero-intro">Find local homestays near calmer places. See the crowd estimate and sample dates, then send a non-binding demo request.</p>
          <a className="hero-scroll" href="#trip-planner"><span className="scroll-icon"><ArrowDown size={15} /></span> Find a homestay</a>
          <div className="hero-trust">
            <span><ShieldCheck size={16} /> Crowd estimates shown clearly</span>
            <span><Leaf size={16} /> Local stays, sample inventory</span>
          </div>
        </div>
        <LandingStayExample />
      </section>
      <section className="planner-section" id="trip-planner">
        <div className="planner-aside">
          <span className="eyebrow">Stay somewhere quieter</span>
          <h2>Start with your trip.<br />Find a local stay.</h2>
          <p>Choose a place, dates and interests. We’ll show quieter matches and the stays listed for them.</p>
          <div className="step-list">
            <div><span>01</span><p><strong>Choose your dates</strong><small>Keep the trip form you already know.</small></p></div>
            <div><span>02</span><p><strong>Compare local stays</strong><small>See backend-ranked quieter matches.</small></p></div>
            <div><span>03</span><p><strong>Send a demo request</strong><small>Sample inventory is not a reservation.</small></p></div>
          </div>
        </div>
        <div className="planner-card"><TripRequestForm onResults={showResults} /></div>
      </section>
      <section className="how-section" id="how-it-works">
        <div><span className="eyebrow">A little more care</span><h2>Stay curious. Travel gently.</h2></div>
        <div className="how-grid">
          <article><span className="how-number">01</span><h3>Estimates, not live counts</h3><p>The backend estimates crowd levels for your date and shows the number, level and data notes.</p></article>
          <article><span className="how-number">02</span><h3>Sample dates, not availability</h3><p>Inventory is illustrative. A demo request does not reserve a room or reduce sample units.</p></article>
          <article><span className="how-number">03</span><h3>Keep your details private</h3><p>The demo request asks for dates and guest count only. It collects no contact or payment details.</p></article>
        </div>
      </section>
      <section className="closing-note">
      <span>Find a local stay. Leave a little room to breathe.</span>
      <a className="button button-primary" href="#trip-planner">Plan a trip <ArrowRight size={15} aria-hidden="true" /></a>
      </section>
    </div>
  );
}
