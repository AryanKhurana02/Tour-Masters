from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RouteEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_id: int = Field(gt=0)
    origin_label: Literal["Dehradun hub"]
    destination_name: str
    distance_meters: int = Field(gt=0)
    duration_seconds: int = Field(ge=0)
    estimated: Literal[True] = True
    source: Literal["OpenRouteService"] = "OpenRouteService"
    retrieved_at: datetime
    notes: list[str]
