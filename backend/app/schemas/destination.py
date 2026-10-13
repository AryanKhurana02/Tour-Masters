from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class DestinationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    name: str
    district: str
    region: str
    description: str
    tags: list[str]
    best_months: list[int] = Field(max_length=12)
    popularity_score: int | None = Field(default=None, ge=0, le=100)
    source_label: str
    source_url: str | None
    reviewer: str
    reviewed_at: date


class HomestayRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    destination_id: int = Field(gt=0)
    name: str
    village: str
    nightly_min: int | None = Field(default=None, ge=0)
    nightly_max: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    public_contact: str | None = None
    booking_url: str | None = None
    amenities: list[str]
    source_label: str
    source_url: str | None
    reviewer: str
    reviewed_at: date


class AlternativeRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: DestinationRead
    match_tags: list[str]
    travel_fit: int | None = Field(default=None, ge=0, le=100)
    source_label: str
    source_url: str | None
    reviewer: str
    reviewed_at: date


class DestinationDetail(DestinationRead):
    alternatives: list[AlternativeRead]
