# Booking Creation Bugs

## Start Here

Find bugs by testing booking windows, pricing, overlap detection, quota, and member/admin behavior. Use clean future datetimes and reset database state between tests.

## Contract Rules

- `price_cents = hourly_rate_cents * duration_hours`.
- Duration must be whole hours, minimum 1 and maximum 8.
- Overlap condition is `existing.start_time < new.end_time AND new.start_time < existing.end_time`.
- Back-to-back bookings are allowed.
- Overlap on confirmed bookings returns `409 ROOM_CONFLICT`.
- A member may hold at most 3 confirmed bookings with `start_time` in `(now, now + 24h]`.
- Quota violation returns `409 QUOTA_EXCEEDED`.

## Files To Inspect

- `app/routers/bookings.py`
- `app/models.py`
- `app/timeutils.py`
- `app/services/stats.py`
- `app/errors.py`

## Tests To Add Or Run

- One-hour booking price equals room hourly rate.
- Eight-hour booking is accepted.
- Nine-hour booking is rejected.
- Back-to-back bookings for the same room are accepted.
- Partially overlapping bookings are rejected.
- Cancelled bookings do not block new bookings.
- Fourth booking inside the next 24 hours returns `409 QUOTA_EXCEEDED`.
- Booking outside the next 24 hours does not count toward quota.

## Common Failure Signs

- Overlap check uses `<=` and blocks back-to-back bookings.
- Conflict query does not filter by status.
- Quota query counts all future bookings instead of the required window.
- Price calculation uses minutes or floats and rounds incorrectly.

