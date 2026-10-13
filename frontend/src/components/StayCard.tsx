import { ArrowRight, BedDouble, MapPin } from "lucide-react";
import { Link } from "react-router-dom";

import type { CrowdEstimate, Destination, Homestay, RecommendationRequest } from "../types/api";

interface Props {
  stay: Homestay;
  destination: Destination;
  crowd: CrowdEstimate;
  request: RecommendationRequest;
  rankScore: number;
}

export function StayCard({ stay, destination, crowd, request, rankScore }: Props) {
  const price = stay.nightly_min === null
    ? "Price not listed"
    : `${stay.currency ?? ""} ${stay.nightly_min}${stay.nightly_max !== null ? `–${stay.nightly_max}` : "+"} per night`;

  return (
    <article className="stay-card">
      <div className="stay-card-heading">
        <div><span className="eyebrow"><MapPin size={13} /> {stay.village || destination.district}</span><h3>{stay.name}</h3></div>
        <span className="mock-tag"><BedDouble size={13} /> Sample stay</span>
      </div>
      <p className="stay-facts">{price} <span aria-hidden="true">·</span> {stay.amenities.length ? stay.amenities.join(" · ") : "Amenities not listed"}</p>
      <p className="stay-score-line">Match {Math.round(rankScore)} <span aria-hidden="true">·</span> Estimated {crowd.score} · {crowd.level}</p>
      <Link
        className="button button-primary"
        to={`/place/${destination.id}`}
        state={{ destination, stay, crowd, request }}
      >
        View stay and sample dates <ArrowRight size={16} />
      </Link>
    </article>
  );
}
