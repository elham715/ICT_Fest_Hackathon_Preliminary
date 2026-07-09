# Datetime Bugs

## Start Here

Find bugs by comparing every datetime parse, comparison, storage value, and serialized response against the contract. Datetimes are foundational, so fix this lane before booking, reports, or refunds.

## Contract Rules

- All API datetimes are ISO 8601.
- Offset inputs must be converted to UTC before storage or comparison.
- Naive inputs are treated as UTC.
- Responses must be UTC with an explicit UTC designator.
- `start_time` must be strictly in the future.
- `end_time` must be strictly after `start_time`.
- Duration must be whole hours, minimum 1 and maximum 8.

## Files To Inspect

- `app/timeutils.py`
- `app/routers/bookings.py`
- `app/serializers.py`
- `app/schemas.py`
- `app/routers/admin.py`
- `app/routers/rooms.py`

## Tests To Add Or Run

- Offset input like `2026-07-24T10:00:00+06:00` stores and compares as UTC.
- Naive input is treated as UTC.
- Past `start_time` returns `400 INVALID_BOOKING_WINDOW`.
- `end_time <= start_time` returns `400 INVALID_BOOKING_WINDOW`.
- Non-whole-hour duration returns `400 INVALID_BOOKING_WINDOW`.
- Duration below 1 hour or above 8 hours returns `400 INVALID_BOOKING_WINDOW`.
- Response datetimes include `Z` or `+00:00`.

## Common Failure Signs

- Comparing aware and naive datetimes raises errors.
- Offset datetimes are stored without conversion.
- A grace window allows near-past bookings.
- Serialized datetimes omit UTC information.

