# Rate Limit And Concurrency Issues

## 1. Rate Limiter Loses Concurrent Requests

**Rating:** Hard, valid.

**Files/lines:**

- `app/services/ratelimit.py:18`
- `app/services/ratelimit.py:22`

**Expected:** `POST /bookings` allows at most 20 requests per rolling 60 seconds per user; all attempts count.

**Likely bug:** `_buckets` is a global dict with no lock. Concurrent calls can read the same bucket and overwrite each other, undercounting bursts.

**Reason this is valid:** The rate-limit contract explicitly says it must hold under concurrent requests. The artificial sleep between bucket filtering and append widens the race window and makes the read/write race easier to trigger.

**Suggested tests:**

- Fire 25 parallel valid booking-create requests as one user and assert excess requests return `429 RATE_LIMITED`.
- Repeat with invalid or conflicting booking requests and assert failed attempts still count.

## 2. Room Conflict Check Is Check-Then-Insert

**Rating:** Hard, valid.

**Files/lines:**

- `app/routers/bookings.py:42`

**Expected:** Overlapping confirmed bookings for the same room must be rejected under concurrent requests.

**Likely bug:** `_has_conflict()` reads existing rows, then insertion happens later without atomic protection.

**Suggested tests:**

- Submit two parallel identical bookings for the same room and interval.
- Assert one succeeds, one returns `409 ROOM_CONFLICT`, and only one confirmed row exists.

## 3. Quota Check Can Be Bypassed Concurrently

**Rating:** Hard, valid.

**Files/lines:**

- `app/routers/bookings.py:55`

**Expected:** A member may hold at most 3 confirmed bookings in `(now, now + 24h]`, including under concurrent creation.

**Likely bug:** `_check_quota()` counts rows before insertion. Multiple concurrent requests can all observe count below 3 and commit.

**Suggested tests:**

- Pre-create 2 qualifying bookings, send 2 parallel qualifying creates, and assert only one succeeds.
- Send 5 parallel qualifying creates from zero and assert final count never exceeds 3.

## 4. Reference Codes Are Not Unique Under Concurrency

**Rating:** Hard, valid.

**Files/lines:**

- `app/services/reference.py:17`
- `app/models.py:55`

**Expected:** Every `reference_code` is unique, including under concurrent creation.

**Likely bug:** Counter read/sleep/write has no lock, and `reference_code` is indexed but not unique.

**Suggested tests:**

- Create many bookings concurrently across different rooms/times and assert all reference codes are unique.

## 5. Concurrent Cancellation Can Create Multiple Refund Logs

**Rating:** Hard, valid.

**Files/lines:**

- `app/routers/bookings.py:178`
- `app/services/refunds.py:24`

**Expected:** Concurrent cancellation of the same booking produces exactly one successful cancellation and one `RefundLog`.

**Likely bug:** Cancellation checks status, logs refund, and only later marks the booking cancelled.

**Suggested tests:**

- Send parallel `POST /bookings/{id}/cancel` requests.
- Assert exactly one `200`, the rest `409 ALREADY_CANCELLED`, and exactly one refund row exists.

## 6. Stats Side Effects Are Race-Prone

**Rating:** Medium to hard, valid.

**Files/lines:**

- `app/services/stats.py:22`

**Expected:** Room stats stay derivable from confirmed bookings after concurrent create/cancel operations.

**Likely bug:** Global stats updates use read/sleep/write without locking, so increments/decrements can be lost.

**Suggested tests:**

- Run parallel successful creates and compare `/rooms/{id}/stats` to DB-derived confirmed count and revenue.
- Run parallel cancellations and assert stats decrement only once.

## Cross-Lane Note

Puku also flagged synchronous sleeps in booking creation and notification side effects. Those are strongest when evaluated under the liveness lane because they can delay unrelated endpoints during concurrent valid requests.
