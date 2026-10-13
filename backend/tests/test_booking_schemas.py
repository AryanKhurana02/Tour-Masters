from datetime import date
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.booking import DemoBookingRequest, DemoBookingReceipt, MockInventoryDay


def test_demo_booking_contract_accepts_non_binding_request_without_personal_data() -> None:
    request = DemoBookingRequest(
        homestay_id=1,
        check_in=date(2026, 11, 7),
        check_out=date(2026, 11, 9),
        guest_count=2,
        client_request_id="6f1f8f9e-5edb-4ae8-87d0-392a508fcddb",
    )

    assert request.homestay_id == 1
    assert request.guest_count == 2
    assert isinstance(request.client_request_id, UUID)


@pytest.mark.parametrize(
    "changes",
    [
        {"check_out": date(2026, 11, 7)},
        {"check_out": date(2026, 12, 8)},
        {"guest_count": 0},
        {"guest_count": 9},
        {"guest_name": "A guest"},
        {"payment_token": "not accepted"},
    ],
)
def test_demo_booking_contract_rejects_invalid_or_out_of_scope_fields(
    changes: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "homestay_id": 1,
        "check_in": date(2026, 11, 7),
        "check_out": date(2026, 11, 9),
        "guest_count": 2,
        "client_request_id": "6f1f8f9e-5edb-4ae8-87d0-392a508fcddb",
    }
    payload.update(changes)

    with pytest.raises(ValidationError):
        DemoBookingRequest.model_validate(payload)


def test_mock_inventory_and_receipt_are_explicitly_demo_only() -> None:
    inventory = MockInventoryDay(
        homestay_id=1,
        date=date(2026, 11, 7),
        total_units=2,
        available_units=1,
        source_label="DEMO MOCK INVENTORY - NOT REAL",
        reviewed_at=date(2026, 10, 12),
    )
    receipt = DemoBookingReceipt(
        request_id="b7c35b9a-cba2-49eb-97c0-7f35fa520c50",
        client_request_id="6f1f8f9e-5edb-4ae8-87d0-392a508fcddb",
        homestay_id=1,
        check_in=date(2026, 11, 7),
        check_out=date(2026, 11, 9),
        guest_count=2,
        created_at="2026-10-13T00:00:00+00:00",
    )

    assert inventory.inventory_mode == "demo_mock"
    assert receipt.status == "demo_submitted"
    assert receipt.non_binding is True


def test_mock_inventory_rejects_available_count_above_total() -> None:
    with pytest.raises(ValidationError, match="Available mock units cannot exceed"):
        MockInventoryDay(
            homestay_id=1,
            date=date(2026, 11, 7),
            total_units=1,
            available_units=2,
            source_label="DEMO MOCK INVENTORY - NOT REAL",
            reviewed_at=date(2026, 10, 12),
        )
