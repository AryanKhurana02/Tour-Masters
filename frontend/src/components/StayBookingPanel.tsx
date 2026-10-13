import { CalendarDays, LoaderCircle, UsersRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMockInventory, submitDemoBooking } from "../services/api";
import { saveTrip } from "../services/offlineStore";
import type { CrowdEstimate, Destination, Homestay, MockInventoryResponse, SavedStayRequest } from "../types/api";
import { formatDate } from "../utils/presentation";

interface Props {
  stay: Homestay;
  destination: Destination;
  crowd: CrowdEstimate;
  initialCheckIn: string;
  initialNights: number;
}

function addDays(value: string, days: number): string {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function StayBookingPanel({
  stay,
  destination,
  crowd,
  initialCheckIn,
  initialNights,
}: Props) {
  const navigate = useNavigate();
  const [checkIn, setCheckIn] = useState(initialCheckIn);
  const [nights, setNights] = useState(Math.min(Math.max(initialNights, 1), 30));
  const [guests, setGuests] = useState(2);
  const [inventory, setInventory] = useState<MockInventoryResponse>();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const clientRequestId = useMemo(() => crypto.randomUUID(), []);
  const checkOut = checkIn ? addDays(checkIn, nights) : "";

  useEffect(() => {
    if (!checkIn || nights < 1 || nights > 30) return;
    let active = true;
    setLoading(true);
    setError("");
    setInventory(undefined);
    getMockInventory(stay.id, checkIn, checkOut)
      .then((result) => { if (active) setInventory(result); })
      .catch((cause: unknown) => {
        if (active) {
          setInventory(undefined);
          setError(cause instanceof Error ? cause.message : "Availability could not be loaded.");
        }
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [checkIn, checkOut, nights, stay.id]);

  const expectedDates = Array.from({ length: nights }, (_, index) => addDays(checkIn, index));
  const inventoryByDate = new Map((inventory?.days ?? []).map((day) => [day.date, day]));
  const datesCovered = expectedDates.every((date) => inventoryByDate.has(date));
  const hasUnits = datesCovered && expectedDates.every(
    (date) => (inventoryByDate.get(date)?.available_units ?? 0) > 0,
  );

  async function submitRequest() {
    setSubmitting(true);
    setError("");
    try {
      const receipt = await submitDemoBooking({
        homestay_id: stay.id,
        check_in: checkIn,
        check_out: checkOut,
        guest_count: guests,
        client_request_id: clientRequestId,
      });
      const saved: SavedStayRequest = {
        type: "stay_request",
        id: receipt.request_id,
        saved_at: receipt.created_at,
        title: `${stay.name} · ${formatDate(receipt.check_in)}`,
        receipt,
        stay,
        destination,
        crowd,
      };
      await saveTrip(saved);
      navigate(`/saved/${saved.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The request could not be sent.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="booking-panel" aria-label={`Stay request for ${stay.name}`}>
      <div className="booking-panel-heading">
        <p>Check dates and send a request. A request is not a confirmed booking.</p>
      </div>
      <div className="booking-fields">
        <label>
          <span><CalendarDays size={16} /> Check in</span>
          <input type="date" value={checkIn} min={new Date().toISOString().slice(0, 10)} onChange={(event) => setCheckIn(event.target.value)} />
        </label>
        <label>
          <span><CalendarDays size={16} /> Nights</span>
          <select value={nights} onChange={(event) => setNights(Number(event.target.value))}>
            {Array.from({ length: 7 }, (_, index) => index + 1).map((count) => (
              <option key={count} value={count}>{count} {count === 1 ? "night" : "nights"}</option>
            ))}
          </select>
        </label>
        <label>
          <span><UsersRound size={16} /> Guests</span>
          <select value={guests} onChange={(event) => setGuests(Number(event.target.value))}>
            {Array.from({ length: 8 }, (_, index) => index + 1).map((count) => (
              <option key={count} value={count}>{count} {count === 1 ? "guest" : "guests"}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="inventory-status" role="status" aria-live="polite">
        {loading ? "Checking availability…" : error ? "Availability could not be checked." : !datesCovered ? "No sample data for every night. Try another date." : hasUnits ? "Units shown for these dates." : "No units available for at least one night."}
      </div>
      {inventory?.days.length ? (
        <ul className="inventory-days">
          {expectedDates.map((day) => {
            const row = inventoryByDate.get(day);
            return (
              <li key={day}>
                <span>{formatDate(day)}</span>
                <strong>{row ? `${row.available_units} unit${row.available_units === 1 ? "" : "s"}` : "Not listed"}</strong>
              </li>
            );
          })}
        </ul>
      ) : null}
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-primary" type="button" disabled={loading || submitting || !hasUnits} onClick={() => void submitRequest()}>
        {submitting ? <><LoaderCircle size={17} className="spin" /> Sending…</> : "Send request"}
      </button>
      <p className="booking-privacy-note">No personal details collected.</p>
    </section>
  );
}