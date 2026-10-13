import sqlite3

from tests.asgi_client import TestClient


def _add_inventory(test_client: TestClient) -> None:
    database_path = test_client.app.state.settings.database_path
    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO homestay_inventory "
            "(id, homestay_id, inventory_date, total_units, available_units, "
            "inventory_mode, source_label, reviewer, reviewed_at) "
            "VALUES (?, 1, ?, 2, ?, 'demo_mock', "
            "'DEMO MOCK INVENTORY - NOT REAL', 'fixture', '2026-10-12')",
            [
                (1, "2026-11-07", 2),
                (2, "2026-11-08", 1),
            ],
        )


def test_inventory_endpoint_returns_only_explicit_mock_dates(test_client: TestClient) -> None:
    _add_inventory(test_client)

    response = test_client.get(
        "/api/homestays/1/inventory?check_in=2026-11-07&check_out=2026-11-09"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["inventory_mode"] == "demo_mock"
    assert [day["date"] for day in result["days"]] == ["2026-11-07", "2026-11-08"]
    assert "mock inventory" in result["warnings"][0].lower()


def test_demo_request_is_non_binding_idempotent_and_does_not_decrement_inventory(
    test_client: TestClient,
) -> None:
    _add_inventory(test_client)
    payload = {
        "homestay_id": 1,
        "check_in": "2026-11-07",
        "check_out": "2026-11-09",
        "guest_count": 2,
        "client_request_id": "6f1f8f9e-5edb-4ae8-87d0-392a508fcddb",
    }

    first = test_client.post("/api/booking-requests", json=payload)
    second = test_client.post("/api/booking-requests", json=payload)

    assert first.status_code == second.status_code == 200
    receipt = first.json()
    assert receipt == second.json()
    assert receipt["status"] == "demo_submitted"
    assert receipt["inventory_mode"] == "demo_mock"
    assert receipt["non_binding"] is True
    assert "guest_name" not in receipt
    assert "contact" not in receipt
    assert "payment" not in receipt

    with sqlite3.connect(test_client.app.state.settings.database_path) as connection:
        assert connection.execute(
            "SELECT count(*) FROM booking_requests"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT available_units FROM homestay_inventory ORDER BY inventory_date"
        ).fetchall() == [(2,), (1,)]


def test_request_id_cannot_be_reused_with_different_booking_data(test_client: TestClient) -> None:
    _add_inventory(test_client)
    base = {
        "homestay_id": 1,
        "check_in": "2026-11-07",
        "check_out": "2026-11-09",
        "guest_count": 2,
        "client_request_id": "6f1f8f9e-5edb-4ae8-87d0-392a508fcddb",
    }
    assert test_client.post("/api/booking-requests", json=base).status_code == 200

    changed = {**base, "guest_count": 3}
    response = test_client.post("/api/booking-requests", json=changed)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_request_rejects_missing_or_unavailable_mock_nights(test_client: TestClient) -> None:
    _add_inventory(test_client)
    payload = {
        "homestay_id": 1,
        "check_in": "2026-11-07",
        "check_out": "2026-11-10",
        "guest_count": 2,
        "client_request_id": "6f1f8f9e-5edb-4ae8-87d0-392a508fcddb",
    }

    response = test_client.post("/api/booking-requests", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["message"] == (
        "Mock inventory is not provided for every selected night."
    )


def test_request_rejects_pii_and_payment_fields(test_client: TestClient) -> None:
    response = test_client.post(
        "/api/booking-requests",
        json={
            "homestay_id": 1,
            "check_in": "2026-11-07",
            "check_out": "2026-11-09",
            "guest_count": 2,
            "client_request_id": "6f1f8f9e-5edb-4ae8-87d0-392a508fcddb",
            "guest_email": "guest@example.invalid",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Request validation failed."
