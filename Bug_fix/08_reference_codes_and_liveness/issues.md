# Reference Codes And Liveness Issues

## 1. Duplicate Reference Codes Under Concurrent Creation

**Files/lines:**

- `app/services/reference.py:17`
- `app/routers/bookings.py:112`

**Expected:** Every booking `reference_code` is unique, including under concurrent creation.

**Likely bug:** `next_reference_code()` reads the counter, sleeps, then increments without a lock or database-backed atomicity.

**Suggested tests:**

- Fire concurrent valid booking requests for different non-overlapping slots.
- Assert all returned and persisted `reference_code` values are unique.

## 2. Reference Codes Can Repeat After Restart

**Files/lines:**

- `app/services/reference.py:8`
- `app/models.py:55`

**Expected:** Reference codes are globally unique for all bookings, not only within one process lifetime.

**Likely bug:** Counter is process-local and starts at `1000`; `Booking.reference_code` is indexed but not unique.

**Suggested tests:**

- Create a booking.
- Reset or reload `app.services.reference._counter`.
- Create another booking and assert the code does not duplicate persisted data.
- Inspect schema for a unique constraint on `bookings.reference_code`.

## 3. Blocking Sleeps Threaten Liveness

**Files/lines:**

- `app/services/reference.py:14`
- `app/routers/bookings.py:27`
- `app/routers/bookings.py:32`
- `app/routers/bookings.py:37`

**Expected:** The service responds to all endpoints at all times; concurrent valid requests must not hang the service.

**Likely bug:** `time.sleep()` runs in request paths. Enough concurrent booking/cancel requests can occupy the sync worker threadpool and delay unrelated endpoints such as `/health`.

**Suggested tests:**

- Start many concurrent valid booking or cancel requests.
- Repeatedly call `/health` and assert it remains fast.
- Assert all requests complete within a tight timeout.

## 4. SQLite Lock Waits Can Stall Concurrent Writes

**Files/lines:**

- `app/database.py:7`

**Expected:** No combination of concurrent valid requests may hang the service.

**Likely bug:** SQLite uses `timeout=30`, so concurrent writes can block up to 30 seconds waiting on locks. Combined with request-path sleeps and no concurrency control, valid concurrent requests may appear hung.

**Suggested tests:**

- Run concurrent valid booking creates/cancels with client timeout below 30 seconds.
- Assert no request blocks until SQLite lock timeout.
- Assert `/health` remains responsive during the write burst.

