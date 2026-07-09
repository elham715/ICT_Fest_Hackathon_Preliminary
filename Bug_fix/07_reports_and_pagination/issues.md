# Reports, Availability, Stats, Export, And Pagination Issues

## 1. Pagination Skips Rows And Ignores Requested Limit

**Files/lines:**

- `app/routers/bookings.py:137`

**Expected:** `GET /bookings` sorts by `start_time` ascending, then `id` ascending; offset is `(page - 1) * limit`; response uses requested `limit`.

**Likely bug:** Query sorts descending, uses `offset(page * limit)`, and hardcodes `.limit(10)`.

**Suggested tests:**

- Create 12 bookings with increasing `start_time`.
- Assert page 1 has the first 10 and page 2 has the remaining 2.
- Request `limit=5` and assert 5 items max.
- Create equal-start bookings and assert `id` ascending tie-break.

## 2. Usage Report Cache Is Stale After Booking Creation

**Files/lines:**

- `app/routers/admin.py:25`
- `app/routers/admin.py:61`
- `app/routers/bookings.py:120`

**Expected:** Usage reports reflect current state immediately.

**Likely bug:** Usage report results are cached, but booking creation invalidates only availability cache, not report cache.

**Suggested tests:**

- Fetch empty usage report.
- Create confirmed booking in range.
- Fetch same report again and assert count/revenue increased.

## 3. Availability Cache Is Stale After Cancellation

**Files/lines:**

- `app/routers/rooms.py:69`
- `app/routers/rooms.py:99`
- `app/routers/bookings.py:216`

**Expected:** Availability returns only current confirmed bookings and reflects cancellation immediately.

**Likely bug:** Cancellation invalidates report cache but not availability cache, so cached busy intervals can remain after cancellation.

**Suggested tests:**

- Create booking and fetch availability.
- Cancel booking.
- Fetch availability again and assert the interval is gone.

## 4. Room Stats Can Diverge From Persisted Bookings

**Files/lines:**

- `app/services/stats.py:8`
- `app/services/stats.py:15`
- `app/routers/rooms.py:110`

**Expected:** Room stats always equal confirmed booking count and summed revenue derivable from the database.

**Likely bug:** Stats are process-local incremental memory only. Existing DB bookings after restart/setup are invisible, and cancellation when `_stats` is empty can produce inconsistent values.

**Suggested tests:**

- Create or insert a confirmed booking, simulate restart or clear stats state, and assert stats still match DB.
- Cancel a persisted booking without prior in-memory create state and assert revenue is not negative.

## 5. Export Leaks Cross-Org Bookings

**Files/lines:**

- `app/services/export.py:22`
- `app/services/export.py:48`

**Expected:** Exports are scoped to the admin's organization on every path.

**Likely bug:** `include_all=true&room_id=<id>` uses a query filtered only by `Booking.room_id`, without scoping through `Room.org_id`.

**Suggested tests:**

- Create two orgs with rooms and bookings.
- As Org A admin, call `/admin/export?include_all=true&room_id=<org_b_room_id>`.
- Assert no Org B rows are returned.

