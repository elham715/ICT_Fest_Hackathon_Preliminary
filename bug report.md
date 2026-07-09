# Bug Report — CoWork API

All bugs fixed in lanes 05–08 (rate limiting & concurrency, cancellation refunds, reports & pagination, reference codes & liveness). Bugs in lanes 01–04 were already fixed by prior commits.

---

## Bug 1 — Rate limiter is not thread-safe (Hard)

**File:** `app/services/ratelimit.py` — `record_and_check()`  
**Rule:** §4 Rule 5 — Rate limit must hold under concurrent requests.  
**What was wrong:** `_buckets` (a plain dict) was read, filtered, appended and written back with no lock. Concurrent requests from the same user each read the old bucket, so all appended their timestamp independently and none would exceed the threshold — making the limit trivially bypassable under load. An artificial `time.sleep(0.1)` between the filter and the append widened the race window even further.  
**Fix:** Wrapped the entire read/filter/append/check sequence inside a new `threading.Lock`. The `_settle_pause()` sleep is kept but moved *outside* the lock so other threads are not blocked by it.

---

## Bug 2 — Reference codes are not unique under concurrent creation (Hard)

**File:** `app/services/reference.py` — `next_reference_code()`  
**File:** `app/models.py` — `Booking.reference_code`  
**Rule:** §4 Rule 7 — Every booking's reference code must be globally unique.  
**What was wrong:** The counter was read, then an artificial `time.sleep(0.12)` ran, then the counter was incremented — with no lock. Two concurrent calls would both read the same value, sleep, and produce the same code. The database column was indexed but not `unique`, so no constraint rejected duplicates. Additionally the counter reset to 1000 on restart, risking collisions with existing bookings.  
**Fix:** Added a `threading.Lock` to protect the read-increment-return sequence atomically. The `_format_pause()` sleep is moved *outside* the lock. On the first call, the counter is initialized by querying the database for the highest existing reference code so codes remain unique after restarts. Added `unique=True` to the `Booking.reference_code` column as a final database-level guard.

---

## Bug 3 — Booking conflict and quota checks bypass under concurrent creation (Hard)

**File:** `app/routers/bookings.py` — `create_booking()`  
**Rule:** §4 Rules 3 & 4 — No double-booking and quota limits must hold under concurrent requests.  
**What was wrong:** Two artificial sleeps (`_pricing_warmup` 0.12 s, `_quota_audit` 0.1 s) ran *before* acquiring `booking_write_lock`, and the reference code was generated outside the lock. This meant that while one thread slept before the lock, another could enter the lock, pass both checks, commit a booking, and release — then the first thread would enter with stale data (its SQLAlchemy session snapshot did not reflect the committed row). The `db.expire_all()` call was missing, so `_has_conflict` and `_check_quota` read a stale ORM cache.  
**Fix:** Removed both pre-lock sleeps entirely. Moved `reference.next_reference_code()` inside the lock. Added `db.expire_all()` at the top of the critical section so the session re-queries the database and sees all concurrent commits. Added `IntegrityError` handling on `db.commit()` to map unexpected constraint violations to `ROOM_CONFLICT`.

---

## Bug 4 — Concurrent cancellation creates multiple RefundLog rows (Hard)

**File:** `app/routers/bookings.py` — `cancel_booking()`  
**File:** `app/models.py` — `RefundLog.booking_id`  
**Rule:** §4 Rule 6 — A cancelled booking has exactly one RefundLog entry.  
**What was wrong:** The outer early check `if booking.status == "cancelled"` ran before acquiring `booking_write_lock`. Two concurrent cancel requests would both pass the early check, both enter the lock, and the `db.refresh(booking)` inside the lock still used the same SQLAlchemy session that did not expire, so the second request could also pass and produce a second `RefundLog`. The `RefundLog.booking_id` column had no unique constraint.  
**Fix:** Added `db.expire(booking)` before `db.refresh(booking)` inside the lock to force a fresh read from the database. Added `unique=True` to `RefundLog.booking_id` to prevent duplicate log rows at the database level. Added `IntegrityError` handling on `db.commit()` to return `ALREADY_CANCELLED` for the losing concurrent request.

---

## Bug 5 — Refund percent calculated outside the lock with stale data (Hard)

**File:** `app/routers/bookings.py` — `cancel_booking()`  
**Rule:** §4 Rule 6 — The amount returned by the cancel response must equal the amount stored in the RefundLog.  
**What was wrong:** `notice` (and therefore `refund_percent` and `refund_amount_cents`) were computed before acquiring the lock, using the ORM object's potentially stale field values. Inside the lock a `db.refresh(booking)` was called, but the already-computed refund amount was passed in — so if `booking.price_cents` had changed (or a concurrent cancel had already committed and changed `start_time`), the response amount could differ from the stored RefundLog amount.  
**Fix:** Moved all refund calculations (`notice`, `refund_percent`, `refund_amount_cents`) to *inside* the lock, after `db.expire(booking)` + `db.refresh(booking)`, guaranteeing the response and the RefundLog always use the same fresh data.

---

## Bug 6 — Refund half-up rounding violated (Hard)

**File:** `app/routers/bookings.py` — `cancel_booking()`  
**Rule:** §4 Rule 6 — Refund amount rounds to the nearest cent, half-cents rounding up.  
**What was wrong:** The previous code used `round()` (Python banker's rounding — rounds half to even, not half-up), and an earlier version used plain `int()` (floor). For example, 50% of 1001 cents should be 501, but `round(5.005)` is `5` in Python's banker's rounding.  
**Fix:** Replaced with `math.floor(price_cents * refund_percent / 100 + 0.5)` which is equivalent to ROUND_HALF_UP for positive values.

---

## Bug 7 — Availability cache not invalidated on cancellation (Hard)

**File:** `app/routers/bookings.py` — `cancel_booking()` (prior state)  
**Rule:** §4 Rule 13 — Availability must reflect current state immediately.  
**What was wrong:** The original cancellation path only invalidated the *report* cache (`cache.invalidate_report`) but not the *availability* cache, so a cancelled booking's busy interval remained visible in `/rooms/{id}/availability` until the TTL expired.  
**Fix:** Added `cache.invalidate_availability(room_id, start_date)` in `cancel_booking()` immediately after the cancellation commits (this was already added in commit `89b7a47`, retained here).

---

## Bug 8 — Room stats derived from race-prone process-local memory (Medium-Hard)

**File:** `app/services/stats.py` — `record_create()`, `record_cancel()`, `get()`  
**File:** `app/routers/rooms.py` — `room_stats()`  
**Rule:** §4 Rule 14 — Room stats must always be consistent with the bookings.  
**What was wrong:** `_stats` was a plain dict updated with read-sleep-write (no lock), so concurrent increments/decrements could be lost. On process restart the dict was empty, so stats for pre-existing bookings were wrong. A `record_cancel` while the dict was empty could produce negative revenue.  
**Fix:** Replaced the in-memory tracker calls in `record_create`/`record_cancel` with `pass`. In `rooms.py`, replaced `stats.get()` with a live `func.count` / `func.coalesce(func.sum(...), 0)` SQL query so stats always match the database.

---

## Bug 9 — Admin CSV export leaks cross-org bookings (Hard)

**File:** `app/services/export.py` — `fetch_bookings_raw()`  
**Rule:** §4 Rule 9 — Users may only read data belonging to their own organization.  
**What was wrong:** When `include_all=true&room_id=<id>` was specified, `fetch_bookings_raw` queried `Booking` filtered only by `room_id`, with no join to `Room` and no check on `Room.org_id`. An admin from Org B could supply a room ID belonging to Org A and read all of Org A's bookings.  
**Fix:** Added a `JOIN Room` and `Room.org_id == org_id` filter to `fetch_bookings_raw`. Updated the function signature to accept `org_id`.

---

## Bug 10 — Notification lock order causes deadlock (Hard / Liveness)

**File:** `app/services/notifications.py` — `notify_created()`, `notify_cancelled()`  
**Rule:** §4 Rule 16 — No combination of concurrent valid requests may hang the service.  
**What was wrong:** `notify_created()` acquired `_email_lock` then nested `_audit_lock`. `notify_cancelled()` acquired `_audit_lock` then nested `_email_lock`. A concurrent create + cancel could result in Thread A holding `_email_lock` waiting for `_audit_lock`, while Thread B holds `_audit_lock` waiting for `_email_lock` — a classic deadlock.  
**Fix:** Replaced nested locking with sequential lock acquisition in both functions (acquire and fully release one lock before acquiring the next), eliminating the circular wait condition entirely.

---

## Bug 11 — Health endpoint blocked by threadpool saturation (Medium / Liveness)

**File:** `app/routers/health.py` — `health()`  
**Rule:** §4 Rule 16 — The service must respond to all endpoints at all times.  
**What was wrong:** `def health()` (sync) is dispatched to uvicorn's sync thread pool. Under a burst of concurrent booking/cancel requests (each holding locks and sleeping), the thread pool fills up and `/health` can be delayed or timeout.  
**Fix:** Changed to `async def health()` so it runs directly on the ASGI event loop and is never queued behind blocking sync workers.

---

## Bug 12 — Blocking sleeps in request paths threaten liveness (Medium / Liveness)

**Files:** `app/routers/bookings.py` (`_pricing_warmup`, `_quota_audit`, `_settlement_pause`), `app/services/stats.py` (`_aggregate_pause`), `app/services/reference.py` (`_format_pause`), `app/services/notifications.py` (`_send_email`, `_write_audit`)  
**Rule:** §4 Rule 16 — No combination of concurrent valid requests may hang the service.  
**What was wrong:** `time.sleep()` calls totalling ~0.64 s per booking create request and ~0.34 s per cancel were embedded in the hot request path. With uvicorn's default 40 sync worker threads, just 63 concurrent bookings could saturate the pool and make the server unresponsive.  
**Fix:** Removed `_pricing_warmup`, `_quota_audit`, `_settlement_pause` entirely from the booking paths. Moved `_format_pause` (in reference.py) and `_settle_pause` (in ratelimit.py) outside their respective critical sections. The notification sleeps remain but are outside all blocking locks.
