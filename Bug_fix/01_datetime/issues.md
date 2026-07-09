# Datetime Issues

## 1. Offset Inputs Are Not Converted To UTC

**Files/lines:**

- `app/timeutils.py:11`
- `app/timeutils.py:13`

**Expected:** Offset datetimes are converted to UTC before storage or comparison. Naive datetimes are treated as UTC.

**Likely bug:** `datetime.fromisoformat()` parses the offset, but `dt.replace(tzinfo=None)` drops it without converting. Example: `2026-07-24T10:00:00+06:00` becomes `10:00 UTC` instead of `04:00 UTC`.

**Suggested tests:**

- Create an offset booking and assert response times are converted to UTC.
- Create equivalent UTC and offset bookings for the same room and assert conflict.

## 2. Invalid Datetime Strings Can Raise 500s

**Files/lines:**

- `app/timeutils.py:11`
- `app/routers/bookings.py:82`
- `app/routers/bookings.py:83`

**Expected:** Invalid booking datetimes return `400 INVALID_BOOKING_WINDOW`.

**Likely bug:** `datetime.fromisoformat()` errors are not caught before route logic continues.

**Suggested tests:**

- `start_time = "not-a-date"` returns `400 INVALID_BOOKING_WINDOW`.
- Valid `start_time` with invalid `end_time` returns `400 INVALID_BOOKING_WINDOW`.

## 3. Near-Past Bookings Are Accepted

**Files/lines:**

- `app/routers/bookings.py:84`
- `app/routers/bookings.py:86`

**Expected:** `start_time` must be strictly in the future with no grace window.

**Likely bug:** The route allows starts up to 5 minutes in the past.

**Suggested tests:**

- `start_time = now - 1 second` returns `400 INVALID_BOOKING_WINDOW`.
- `start_time = now - 4 minutes` returns `400 INVALID_BOOKING_WINDOW`.

## 4. Zero, Negative, And Sub-1-Hour Durations Are Accepted

**Files/lines:**

- `app/routers/bookings.py:89`
- `app/routers/bookings.py:93`

**Expected:** `end_time` must be strictly after `start_time`; duration must be whole hours, minimum 1 and maximum 8.

**Likely bug:** There is no minimum-duration or positive-window check. Zero-hour bookings can get zero price; negative whole-hour durations can get negative price.

**Suggested tests:**

- `end_time == start_time` returns `400 INVALID_BOOKING_WINDOW`.
- `end_time < start_time` returns `400 INVALID_BOOKING_WINDOW`.
- 30-minute duration returns `400 INVALID_BOOKING_WINDOW`.
- 1-hour and 8-hour durations succeed; 9-hour duration fails.

## 5. Back-To-Back Bookings Conflict Incorrectly

**Files/lines:**

- `app/routers/bookings.py:50`

**Expected:** Overlap is `existing.start_time < new.end_time AND new.start_time < existing.end_time`; back-to-back bookings are allowed.

**Likely bug:** Inclusive comparisons treat adjacent bookings as conflicts.

**Suggested tests:**

- Existing `10:00-11:00`, new `11:00-12:00` succeeds.
- Existing `10:00-11:00`, new `09:00-10:00` succeeds.
- Existing `10:00-11:00`, new `10:30-11:30` returns `409 ROOM_CONFLICT`.

## 6. Booking Detail Overwrites `start_time`

**Files/lines:**

- `app/routers/bookings.py:165`
- `app/routers/bookings.py:166`

**Expected:** `GET /bookings/{id}` returns the booking's actual `start_time` and a separate `created_at`.

**Likely bug:** `response["start_time"]` is overwritten with `booking.created_at`.

**Suggested tests:**

- Create a future booking, fetch detail, and assert `start_time` equals the created booking start.
- Assert `created_at` remains present and UTC-designated.

## 7. Usage Report Accepts Reversed Date Ranges

**Files/lines:**

- `app/routers/admin.py:30`
- `app/routers/admin.py:36`

**Expected:** Usage report range is inclusive UTC `[from, to]`; invalid reversed ranges should be rejected.

**Likely bug:** `from > to` returns an empty report instead of an error.

**Suggested tests:**

- `/admin/usage-report?from=2026-07-25&to=2026-07-24` returns `400 INVALID_BOOKING_WINDOW`.
- Same-day range includes bookings starting on that UTC date.

