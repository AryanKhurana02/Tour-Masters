import { useEffect, useState } from 'react';
import './LiveCrowdMeter.css';

interface LiveMetric {
  live_crowd_index: number;
  data_source: string;
  timestamp: string;
  note?: string;
}

export function LiveCrowdMeter({ destinationId }: { destinationId: string | number }) {
  const [metric, setMetric] = useState<LiveMetric | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchLive = async () => {
      try {
        const res = await fetch(`/api/destinations/${destinationId}/live-metrics`);
        if (res.ok) {
          const data = await res.json();
          setMetric(data);
        }
      } catch (err) {
        console.error("Failed to fetch live metrics", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchLive();
    const interval = setInterval(fetchLive, 60000); // Poll every 60s
    return () => clearInterval(interval);
  }, [destinationId]);

  if (isLoading) return <div className="live-crowd-container">Loading live estimate…</div>;
  if (!metric) return null;

  const getBand = (score: number) => {
    if (score < 35) return { label: 'Quiet', color: 'var(--quiet-text)' };
    if (score < 60) return { label: 'Moderate', color: 'var(--moderate-text)' };
    if (score < 80) return { label: 'Busy', color: 'var(--busy-text)' };
    return { label: 'Very Busy', color: 'var(--verybusy-text)' };
  };

  const band = getBand(metric.live_crowd_index);

  return (
    <div className="live-crowd-container">
      <div className={`live-badge live-badge--${band.label.toLowerCase().replace(' ', '-')}`}>
        <span>{band.label}</span>
      </div>
      <div className="live-score">{metric.live_crowd_index}/100</div>

      <div className="meter-bar-bg">
        <div
          className="meter-bar-fill"
          style={{ width: `${metric.live_crowd_index}%`, backgroundColor: band.color }}
        ></div>
      </div>

      <p className="live-meta">
        Updated: {new Date(metric.timestamp).toLocaleTimeString()} · Source: {metric.data_source.replace('_', ' ')}
      </p>
    </div>
  );
}