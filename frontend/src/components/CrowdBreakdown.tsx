import { CircleHelp, CloudSun, CalendarDays, UsersRound } from "lucide-react";
import type { CrowdEstimate } from "../types/api";
import { CrowdDial } from "./CrowdDial";

export function CrowdBreakdown({ crowd, animate = true }: { crowd: CrowdEstimate; animate?: boolean }) {
  const factors = [
    { label: "Popularity", value: crowd.popularity, icon: UsersRound },
    { label: "Date demand", value: crowd.date_demand, icon: CalendarDays },
    { label: "Event activity", value: crowd.event_pressure, icon: CircleHelp },
    { label: "Weather (HCI)", value: crowd.weather_visit_tendency, icon: CloudSun },
  ];
  return (
    <section className="crowd-panel" aria-label="Estimated crowd level">
      <CrowdDial crowd={crowd} animate={animate} />
      <div className="crowd-details">
        <div className="eyebrow">Crowd outlook <span>· estimated</span></div>
        <div className="factor-list">
          {factors.map(({ label, value, icon: Icon }) => (
            <div className="factor-row" key={label}>
              <span><Icon size={14} aria-hidden="true" /> {label}</span>
              <span className="factor-track" aria-hidden="true"><i style={{ width: `${value}%` }} /></span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
        {crowd.notes.length > 0 && (
          <ul className="note-list">
            {crowd.notes.map((note) => <li key={note}>{note}</li>)}
          </ul>
        )}
        <p className="data-footnote">
          Rule-based estimate · curated record dated {crowd.reviewed_at}
        </p>
      </div>
    </section>
  );
}
