import { AlertTriangle } from "lucide-react";

import type { SafetyAlert } from "../types/api";
import "./SafetyAlertCard.css";

interface SafetyAlertCardProps {
  alert: SafetyAlert;
}

/**
 * Travel-safety advisory derived from real 5-year weather signals
 * (wet-day probability and landslide-risk rainfall days).
 */
export function SafetyAlertCard({ alert }: SafetyAlertCardProps) {
  const severe = alert.severity === "high";

  return (
    <div
      className={`safety-alert ${severe ? "safety-alert--high" : "safety-alert--medium"}`}
      role="status"
      aria-live="polite"
    >
      <span className="safety-alert__icon" aria-hidden="true">
        <AlertTriangle size={18} />
      </span>
      <div className="safety-alert__body">
        <span className="safety-alert__title">
          {severe ? "High weather risk" : "Weather caution"}
        </span>
        <p className="safety-alert__message">{alert.message}</p>
        <div className="safety-alert__metrics">
          {alert.landslide_risk_probability != null && (
            <span>Landslide-risk days: {(alert.landslide_risk_probability * 100).toFixed(1)}%</span>
          )}
          {alert.wet_day_probability != null && (
            <span>Wet days: {(alert.wet_day_probability * 100).toFixed(0)}%</span>
          )}
        </div>
      </div>
    </div>
  );
}
