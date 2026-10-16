from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.destination import DestinationRead, HomestayRead


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: str = Field(min_length=1, max_length=120)
    start_destination_id: int | None = Field(default=None, gt=0)
    start_date: date
    days: int = Field(ge=1, le=7)
    interests: list[str] = Field(default_factory=list, max_length=8)
    budget_per_night_max: int | None = Field(default=None, ge=0, le=1_000_000)
    avoid_crowds: bool = True
    allow_broadened_search: bool = False

    @field_validator("region")
    @classmethod
    def normalize_region(cls, value: str) -> str:
        return value.strip()

    @field_validator("interests")
    @classmethod
    def normalize_interests(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().casefold() for value in values]
        if any(not value or len(value) > 40 for value in normalized):
            raise ValueError("Interests must contain 1 to 40 characters.")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Interests must be unique.")
        return normalized


class CrowdFrictionCue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cue_type: Literal["weather_warning"] | Literal["road_bottleneck"] | Literal["water_scarcity"] | Literal["resting"]
    message: str = Field(min_length=1)
    severity: Literal["low"] | Literal["medium"] | Literal["high"]


class HistoricalWeatherSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: int = Field(ge=1, le=12)
    avg_precipitation_mm: float | None = None
    avg_temp_max_c: float | None = None
    avg_temp_min_c: float | None = None
    wet_day_probability: float | None = None
    landslide_risk_probability: float | None = None
    friction: int | None = Field(default=None, ge=0, le=100)
    visit_tendency: int | None = Field(default=None, ge=0, le=100)
    hci_score: int | None = Field(default=None, ge=0, le=100)
    source: str | None = None


class SafetyAlert(BaseModel):
    """Travel-safety advisory derived from real historical weather signals."""

    model_config = ConfigDict(extra="forbid")

    severity: Literal["medium"] | Literal["high"]
    landslide_risk_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    wet_day_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    message: str = Field(min_length=1)


class CrowdEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    level: Literal["Quiet", "Moderate", "Busy", "Very busy"]
    estimated: Literal[True] = True
    popularity: int = Field(ge=0, le=100)
    date_demand: int = Field(ge=0, le=100)
    event_pressure: int = Field(ge=0, le=100)
    weather_visit_tendency: int = Field(ge=0, le=100)
    notes: list[str]
    data_mode: Literal["curated_rule_estimate"] = "curated_rule_estimate"
    reviewed_at: date
    friction_cue: Optional[CrowdFrictionCue] = None
    historical_weather: Optional[HistoricalWeatherSignal] = None
    safety_alert: Optional[SafetyAlert] = None


class RecommendationFits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interest: float = Field(ge=0, le=100)
    quietness: float = Field(ge=0, le=100)
    travel: float = Field(ge=0, le=100)
    stay: float = Field(ge=0, le=100)


class RecommendationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: DestinationRead
    homestays: list[HomestayRead]
    crowd: CrowdEstimate
    rank_score: float = Field(ge=0, le=100)
    fits: RecommendationFits
    reasons: list[str]


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    items: list[RecommendationItem]
    warnings: list[str]
