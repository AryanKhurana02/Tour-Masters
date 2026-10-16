import { Calendar, Droplets, Thermometer, AlertTriangle, Sun, CloudRain } from "lucide-react";
import type { HistoricalWeatherSignal, SeasonalityData } from "../types/api";

interface WeatherHistorySectionProps {
  destinationName: string;
  historicalWeather?: HistoricalWeatherSignal;
  seasonality?: SeasonalityData;
  targetMonth: number;
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

export function WeatherHistorySection({
  destinationName,
  historicalWeather,
  seasonality,
  targetMonth,
}: WeatherHistorySectionProps) {
  const monthName = MONTH_NAMES[targetMonth - 1] || "Unknown";

  if (!historicalWeather && !seasonality) {
    return (
      <section className="place-weather-history" aria-label="Historical weather context">
        <div className="section-heading">
          <span className="eyebrow"><Calendar size={14} /> SEASONAL CONTEXT</span>
          <h2>How {destinationName} behaves through the year</h2>
        </div>
        <p className="quiet-note">Historical weather data is still being gathered for this destination.</p>
      </section>
    );
  }

  return (
    <section className="place-weather-history" aria-label="Historical weather context">
      <div className="section-heading">
        <span className="eyebrow"><Calendar size={14} /> SEASONAL CONTEXT</span>
        <h2>How {destinationName} behaves in {monthName}</h2>
        <p className="section-subtitle">
          5-year averages (2021–2026) from Open-Meteo + statewide arrival trends
        </p>
      </div>

      {historicalWeather && (
        <div className="weather-history-grid">
          <div className="weather-metric">
            <div className="metric-icon"><Droplets size={20} /></div>
            <div className="metric-content">
              <span className="metric-label">Avg rainfall</span>
              <span className="metric-value">
                {historicalWeather.avg_precipitation_mm?.toFixed(1) ?? "—"} mm
              </span>
              <span className="metric-detail">
                {historicalWeather.wet_day_probability != null
                  ? `· Wet days: {(historicalWeather.wet_day_probability * 100).toFixed(0)}%`
                  : ""}
              </span>
            </div>
          </div>

          <div className="weather-metric">
            <div className="metric-icon"><Thermometer size={20} /></div>
            <div className="metric-content">
              <span className="metric-label">Temp range</span>
              <span className="metric-value">
                {historicalWeather.avg_temp_min_c?.toFixed(1) ?? "—"}°
                {historicalWeather.avg_temp_max_c != null
                  ? ` – ${historicalWeather.avg_temp_max_c.toFixed(1)}°C`
                  : "°C"}
              </span>
            </div>
          </div>

          <div className="weather-metric">
            <div className="metric-icon">
              {historicalWeather.hci_score != null && historicalWeather.hci_score < 50
                ? <AlertTriangle size={20} />
                : <Sun size={20} />}
            </div>
            <div className="metric-content">
              <span className="metric-label">Weather comfort (HCI)</span>
              <span className="metric-value">
                {historicalWeather.hci_score != null ? historicalWeather.hci_score : "—"}/100
              </span>
              <span className="metric-detail">
                {historicalWeather.hci_score != null
                  ? historicalWeather.hci_score >= 75
                    ? "Ideal — clear, comfortable days"
                    : historicalWeather.hci_score >= 50
                    ? "Fair — mixed conditions"
                    : "Challenging — rain, cloud or cold"
                  : ""}
              </span>
            </div>
          </div>

          {historicalWeather.friction != null && historicalWeather.friction > 50 && (
            <div className="weather-metric">
              <div className="metric-icon"><CloudRain size={20} /></div>
              <div className="metric-content">
                <span className="metric-label">Travel friction</span>
                <span className="metric-value">{historicalWeather.friction}/100</span>
                <span className="metric-detail">
                  {historicalWeather.friction > 60
                    ? "High — expect delays & wet conditions"
                    : "Moderate — some rain likely"}
                </span>
              </div>
            </div>
          )}

          {historicalWeather.landslide_risk_probability != null &&
            historicalWeather.landslide_risk_probability > 0.01 && (
              <div className="weather-metric risk">
                <div className="metric-icon"><AlertTriangle size={20} /></div>
                <div className="metric-content">
                  <span className="metric-label">Landslide risk days</span>
                  <span className="metric-value">
                    {(historicalWeather.landslide_risk_probability * 100).toFixed(1)}%
                  </span>
                  <span className="metric-detail">Days with 40+ mm rainfall</span>
                </div>
              </div>
            )}
        </div>
      )}

      {seasonality && (
        <div className="seasonality-card">
          <div className="seasonality-header">
            <span className="seasonality-icon">
              {seasonality.combined_index >= 75 ? <CloudRain size={18} /> : <Sun size={18} />}
            </span>
            <div className="seasonality-text">
              <strong>Statewide arrival trend:</strong> {seasonality.activity_focus}
            </div>
          </div>
          <div className="seasonality-metrics">
            <div className="seasonality-metric">
              <span className="metric-label">Domestic demand</span>
              <span className="metric-value">{seasonality.domestic_index ?? "—"}/100</span>
            </div>
            <div className="seasonality-metric">
              <span className="metric-label">Foreign demand</span>
              <span className="metric-value">{seasonality.foreign_index ?? "—"}/100</span>
            </div>
            <div className="seasonality-metric highlight">
              <span className="metric-label">Combined index</span>
              <span className="metric-value">{seasonality.combined_index}/100</span>
            </div>
          </div>
          <p className="seasonality-weather">{seasonality.weather_condition}</p>
        </div>
      )}

      {historicalWeather && historicalWeather.source && (
        <p className="data-source-note">
          Source: {historicalWeather.source}. {historicalWeather.note}
        </p>
      )}
    </section>
  );
}