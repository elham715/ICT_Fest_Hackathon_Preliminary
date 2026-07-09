# Booking Creation Issues

## 1. Past Or Immediate Starts Are Allowed

**Files/lines:**

- `app/routers/bookings.py:86`

**Expected:** `start_time` must be strictly in the future with no grace window.

**Likely bug:** Code rejects only starts at or before `now - 300s`, so `now` or near-past starts can be accepted.

**Suggested tests:**

- `start_time = now` returns `400 INVALID_BOOKING_WINDOW`.
- `start_time = now - 1 second` returns `400 INVALID_BOOKING_WINDOW`.
- `start_time = now + 1 hour` succeeds.

## 2. Zero Or Negative Duration Bookings Are Accepted

**Files/lines:**

- `app/routers/bookings.py:89`
- `app/routers/bookings.py:93`
- `app/routers/bookings.py:105`

**Expected:** Duration must be whole hours, minimum 1, maximum 8, and `end_time` must be strictly after `start_time`.

**Likely bug:** Code checks whole hours and max duration only. It can create zero-price or negative-price bookings.

**Suggested tests:**

- `end_time == start_time` returns `400`.
- `end_time = start_time - 1 hour` returns `400`.
- 1-hour booking price equals hourly rate.
- 8-hour succeeds; 9-hour returns `400`.

## 3. Back-To-Back Bookings Are Treated As Conflicts

**Files/lines:**

- `app/routers/bookings.py:50`

**Expected:** Exact back-to-back bookings are allowed.

**Likely bug:** Inclusive comparisons block bookings where one starts exactly when another ends.

**Suggested tests:**

- Existing `10:00-11:00`, new `11:00-12:00` succeeds.
- Existing `10:00-11:00`, new `09:00-10:00` succeeds.
- Existing `10:00-11:00`, new `10:30-11:30` returns `409 ROOM_CONFLICT`.

## Note

Sequential quota logic appears aligned with the contract. Concurrency quota issues are tracked in `Bug_fix/05_rate_limit_and_concurrency/issues.md`.

