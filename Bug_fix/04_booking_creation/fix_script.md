# Fix Script: Booking Creation

## Goal

Fix deterministic booking creation rules before attempting concurrency fixes.

## Files To Edit

- `app/routers/bookings.py`
- `app/timeutils.py`

## Steps

1. Reuse the datetime fixes from `01_datetime`.
2. Enforce strictly future `start_time`.
3. Enforce `end_time > start_time`.
4. Enforce whole-hour duration.
5. Enforce duration between 1 and 8 hours.
6. Fix overlap logic to allow back-to-back bookings.
7. Verify price is `hourly_rate_cents * duration_hours`.

## Required Tests

- 1-hour price equals hourly rate.
- 8-hour booking succeeds.
- 9-hour booking fails.
- Zero, negative, and fractional durations fail.
- Back-to-back bookings succeed.
- Partial overlaps fail with `409 ROOM_CONFLICT`.

## Acceptance

- Booking response shape stays exact.
- Invalid windows return `400 INVALID_BOOKING_WINDOW`.

