from datetime import date, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DemoBookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    homestay_id: int = Field(gt=0)
    check_in: date
    check_out: date
    guest_count: int = Field(ge=1, le=8)
    client_request_id: UUID

    @model_validator(mode="after")
    def validate_stay_length(self) -> "DemoBookingRequest":
        nights = (self.check_out - self.check_in).days
        if not 1 <= nights <= 30:
            raise ValueError("A demo stay must be between 1 and 30 nights.")
        return self


class MockInventoryDay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    homestay_id: int = Field(gt=0)
    date: date
    total_units: int = Field(ge=0)
    available_units: int = Field(ge=0)
    inventory_mode: Literal["demo_mock"] = "demo_mock"
    source_label: str = Field(min_length=1)
    reviewed_at: date

    @model_validator(mode="after")
    def validate_available_units(self) -> "MockInventoryDay":
        if self.available_units > self.total_units:
            raise ValueError("Available mock units cannot exceed total mock units.")
        return self


class MockInventoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    homestay_id: int = Field(gt=0)
    check_in: date
    check_out: date
    inventory_mode: Literal["demo_mock"] = "demo_mock"
    days: list[MockInventoryDay]
    warnings: list[str]

    @model_validator(mode="after")
    def validate_date_range(self) -> "MockInventoryResponse":
        if not self.check_in < self.check_out:
            raise ValueError("Check-out must be after check-in.")
        if (self.check_out - self.check_in).days > 30:
            raise ValueError("Inventory lookup cannot exceed 30 nights.")
        return self


class DemoBookingReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    client_request_id: UUID
    homestay_id: int = Field(gt=0)
    check_in: date
    check_out: date
    guest_count: int = Field(ge=1, le=8)
    status: Literal["demo_submitted"] = "demo_submitted"
    inventory_mode: Literal["demo_mock"] = "demo_mock"
    non_binding: Literal[True] = True
    created_at: str
