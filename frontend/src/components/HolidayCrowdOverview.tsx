import { useEffect, useState } from 'react';
import type { HolidayCrowdData } from '../types/api';
import './HolidayCrowdOverview.css';

interface HolidayCrowdOverviewProps {
  holidays: HolidayCrowdData[];
  showAlternatives?: boolean;
}

export function HolidayCrowdOverview({ holidays, showAlternatives = true }: HolidayCrowdOverviewProps) {
  const [expanded, setExpanded] = useState(new Set<number>());

  const getBadgeClass = (category: string) => {
    const lower = category.toLowerCase();
    if (lower.includes('winter') || lower.includes('snow')) return 'winter';
    if (lower.includes('religious') || lower.includes('pilgrimage')) return 'religious';
    if (lower.includes('festival') || lower.includes('season')) return 'festival';
    if (lower.includes('monsoon') || lower.includes('extended')) return 'monsoon';
    if (lower.includes('year-end') || lower.includes('choke')) return 'year-end';
    return 'general';
  };

  return (
    <div className="holiday-overview">
      <div className="holiday-heading">
        <span className="eyebrow">Holiday Calendar</span>
        <h2>Peak Crowd Dates</h2>
      </div>
      <div className="holiday-list">
        {holidays.map((holiday, idx) => {
          const badgeClass = getBadgeClass(holiday.crowdCategory);
          const isExpanded = expanded.has(idx);
          return (
            <div key={idx} className="holiday-item">
              <div
                className="holiday-header"
                onClick={() => setExpanded((prev) => {
                  const next = new Set(prev);
                  if (next.has(idx)) {
                    next.delete(idx);
                  } else {
                    next.add(idx);
                  }
                  return next;
                })}
              >
                <span className="holiday-name">{holiday.holidayName}</span>
                <span className="holiday-date">{holiday.date}</span>
                <span className={`holiday-badge holiday-badge--${badgeClass}`}>
                  {holiday.crowdCategory}
                </span>
              </div>
              {isExpanded && showAlternatives && (
                <div className="holiday-details">
                  <div className="crowded-destinations">
                    <strong>Busy:</strong>
                    <span>{holiday.mostCrowded.join(", ")}</span>
                  </div>
                  <div className="alternative-destinations">
                    <strong>Quieter:</strong>
                    <span>{holiday.leastCrowded.join(", ")}</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}