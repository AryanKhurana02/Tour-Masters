import { ArrowRight, BedDouble, MapPin } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { CrowdDial } from "./CrowdDial";
import { Card } from "./ui/Card";
import { getRecommendations } from "../services/api";
import type { RecommendationItem } from "../types/api";

function dateInAWeek(): string {
  const date = new Date();
  date.setDate(date.getDate() + 7);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function LandingStayExample() {
  const [example, setExample] = useState<RecommendationItem>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function loadExample() {
      try {
        const response = await getRecommendations({
          region: "Uttarakhand",
          start_date: dateInAWeek(),
          days: 1,
          interests: [],
          avoid_crowds: true,
          allow_broadened_search: true,
        });
        const match = response.items.find((item) => item.homestays.length > 0);
        if (active && match) setExample(match);
      } catch (error) {
        console.error("Could not load the landing-page homestay example.", error);
        if (active) setExample(undefined);
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadExample();
    return () => { active = false; };
  }, []);

  const stay = example?.homestays[0];
  return (
    <aside className="hero-art landing-example" aria-label="Example homestay from the catalogue">
      <div className="example-art-contours" aria-hidden="true" />
      <Card className="landing-example-card">
        <div className="hero-art-label"><span>Example</span><BedDouble size={16} /></div>
        {loading ? (
          <p className="example-loading">Looking for a sample stay…</p>
        ) : example && stay ? (
          <>
            <div className="example-stay-top">
              <span className="mock-tag">Sample stay</span>
              <CrowdDial crowd={example.crowd} />
            </div>
            <span className="eyebrow"><MapPin size={13} /> {example.destination.district}, {example.destination.region}</span>
            <h2>{stay.name}</h2>
            <p>{stay.village || example.destination.name}</p>
            <span className="example-score">Estimated crowd · {example.crowd.score} · {example.crowd.level}</span>
            <Link className="button button-primary" to="/plan">Explore homestays <ArrowRight size={16} /></Link>
          </>
        ) : (
          <>
            <span className="mock-tag">Example</span>
            <h2>Local homestays</h2>
            <p>Stay cards appear when catalogue records are available.</p>
            <Link className="button button-primary" to="/plan">Plan a trip <ArrowRight size={16} /></Link>
          </>
        )}
      </Card>
    </aside>
  );
}
