import { CalendarDays, CloudSun, Moon, Sun, Sunrise } from "lucide-react";
import type { ItineraryResponse } from "../types/api";
import { formatDate } from "../utils/presentation";

const periodIcon = {
  morning: Sunrise,
  afternoon: Sun,
  evening: Moon,
};

export function ItineraryView({ itinerary }: { itinerary: ItineraryResponse }) {
  return (
    <div className="itinerary-days">
      {itinerary.days.map((day) => (
        <article className="day-card" key={`${day.day_number}-${day.date}`}>
          <div className="day-rail"><span>DAY</span><strong>{String(day.day_number).padStart(2, "0")}</strong><i /></div>
          <div className="day-body">
            <div className="day-heading">
              <div><span className="eyebrow"><CalendarDays size={14} /> {formatDate(day.date)}</span><h2>{day.destination_name}</h2></div>
              <span className={`day-crowd crowd-${day.crowd.level.toLowerCase().replace(" ", "-")}`}><CloudSun size={15} /> Estimated {day.crowd.score} · {day.crowd.level}</span>
            </div>
            <div className="schedule">
              {day.blocks.map((block) => {
                const Icon = periodIcon[block.period];
                return <div className="schedule-row" key={block.period}><span className="period-icon"><Icon size={16} /></span><span className="period-label">{block.period}</span><p>{block.text}</p></div>;
              })}
            </div>
            {day.homestay_name && <div className="day-stay"><span className="stay-icon"><Moon size={15} /></span><span><strong>{day.homestay_name}</strong><small>Stay details and availability are not verified.</small></span></div>}
            {day.warnings.map((warning) => <p className="inline-warning" key={warning}>{warning}</p>)}
          </div>
        </article>
      ))}
    </div>
  );
}
