# Fix Script: Datetime

## Goal

Make all datetime parsing, comparison, validation, and serialization match the README contract.

## Files To Edit

- `app/timeutils.py`
- `app/routers/bookings.py`
- `app/routers/admin.py`

## Steps

1. Fix `parse_input_datetime()`.
   - Parse ISO 8601 strings.
   - If timezone-aware, convert with `astimezone(timezone.utc)`.
   - Store as naive UTC by removing `tzinfo` after conversion.
   - If parsing fails, raise `AppError(400, "INVALID_BOOKING_WINDOW", ...)` or let callers translate it consistently.

2. Fix booking window validation.
   - Replace the 5-minute grace check with `start <= now`.
   - Reject `end <= start`.
   - Reject non-whole-hour durations.
   - Reject durations below 1 hour or above 8 hours.

3. Fix overlap logic.
   - Use `existing.start_time < new_end and new_start < existing.end_time`.
   - Ensure back-to-back bookings succeed.

4. Fix booking detail serialization.
   - Remove the line that overwrites `response["start_time"]` with `created_at`.

5. Decide whether reversed usage-report ranges should return `400 INVALID_BOOKING_WINDOW`.
   - If implemented, keep response shape and error code consistent.

## Required Tests

- Offset input converts to UTC.
- Invalid datetime returns `400 INVALID_BOOKING_WINDOW`.
- Past or immediate start returns `400 INVALID_BOOKING_WINDOW`.
- `end_time <= start_time` returns `400 INVALID_BOOKING_WINDOW`.
- 1-hour and 8-hour bookings succeed.
- 0-hour, 30-minute, negative, and 9-hour bookings fail.
- Back-to-back bookings succeed.
- Booking detail keeps original `start_time`.

## Acceptance

- `pytest -q` passes.
- No endpoint paths or response field names change.

