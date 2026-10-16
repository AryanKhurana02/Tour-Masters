PRAGMA foreign_keys = ON;

-- Holiday Climate Index (HCI) support.
-- cloud cover and wind speed are the extra Open-Meteo variables required by
-- HCI = 4T + 2A + 3Rd + W. hci_score is the derived 0-100 weather score.
-- Legacy weather_visit_tendency is retained for backward compatibility.

ALTER TABLE weather_climatology ADD COLUMN mean_cloud_cover_pct REAL;
ALTER TABLE weather_climatology ADD COLUMN mean_wind_speed_kmh REAL;
ALTER TABLE weather_climatology ADD COLUMN hci_score INTEGER;

ALTER TABLE weather_forecasts ADD COLUMN cloud_cover_pct REAL;
ALTER TABLE weather_forecasts ADD COLUMN wind_speed_kmh REAL;
ALTER TABLE weather_forecasts ADD COLUMN hci_score INTEGER;
