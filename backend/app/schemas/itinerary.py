from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.recommendation import CrowdEstimate


class ItineraryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date
    days: int = Field(ge=1, le=7)
    destination_ids: list[int] = Field(min_length=1, max_length=7)
    homestay_ids: list[int | None] = Field(default_factory=list, max_length=7)
    budget_per_night_max: int | None = Field(default=None, ge=0, le=1_000_000)
    use_llm: bool = False

    @model_validator(mode="after")
    def validate_selected_ids(self) -> "ItineraryRequest":
        if len(self.destination_ids) > self.days:
            raise ValueError("There cannot be more selected destinations than itinerary days.")
        if any(destination_id <= 0 for destination_id in self.destination_ids):
            raise ValueError("Destination IDs must be positive.")
        if len(self.destination_ids) != len(set(self.destination_ids)):
            raise ValueError("Destination IDs must be unique.")
        if self.homestay_ids and len(self.homestay_ids) != len(self.destination_ids):
            raise ValueError("Provide one homestay ID (or null) per selected destination.")
        return self


class ItineraryBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: Literal["morning", "afternoon", "evening"]
    text: str = Field(min_length=1, max_length=500)


class ItineraryDay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day_number: int = Field(ge=1, le=7)
    date: date
    destination_id: int = Field(gt=0)
    destination_name: str
    homestay_id: int | None = Field(default=None, gt=0)
    homestay_name: str | None = None
    crowd: CrowdEstimate
    blocks: list[ItineraryBlock] = Field(min_length=1, max_length=3)
    warnings: list[str]


class ItineraryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    generation_mode: Literal["rule_fallback", "llm_text_assisted"]
    days: list[ItineraryDay] = Field(min_length=1, max_length=7)
    warnings: list[str]
