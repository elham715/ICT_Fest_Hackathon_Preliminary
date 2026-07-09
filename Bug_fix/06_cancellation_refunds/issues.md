# Cancellation And Refund Issues

## 1. Refund Tier Boundaries Are Wrong

**Files/lines:**

- `app/routers/bookings.py:198`

**Expected:** Notice `>= 48h` gives 100 percent, `>= 24h and < 48h` gives 50 percent, `< 24h` gives 0 percent.

**Likely bug:** `notice_hours > 48` excludes exactly 48h, and the final `else` returns 50 percent instead of 0 percent.

**Suggested tests:**

- Cancel at exactly 48h notice and expect 100 percent.
- Cancel at 48h30m notice and expect 100 percent.
- Cancel at 23h59m notice and expect 0 percent.

## 2. Refund Rounding Violates Half-Up Rule

**Files/lines:**

- `app/routers/bookings.py:208`
- `app/services/refunds.py:15`

**Expected:** Half-cents round up, e.g. 50 percent of 1001 cents is 501.

**Likely bug:** Endpoint uses Python `round()` and `log_refund()` floors with `int()`.

**Suggested tests:**

- Booking price `1001`, 50 percent refund, expect response and stored amount `501`.

## 3. Cancel Response Can Differ From Stored RefundLog

**Files/lines:**

- `app/routers/bookings.py:208`
- `app/routers/bookings.py:210`
- `app/services/refunds.py:17`

**Expected:** Cancel response amount equals stored `RefundLog.amount_cents`.

**Likely bug:** Response and log calculate refund independently.

**Suggested tests:**

- Booking price `1003`, 50 percent refund.
- Assert response `refund_amount_cents == RefundLog.amount_cents`.

## 4. Concurrent Cancel Can Create Duplicate Refund Logs

**Files/lines:**

- `app/routers/bookings.py:195`
- `app/routers/bookings.py:210`
- `app/routers/bookings.py:212`
- `app/models.py:62`

**Expected:** Concurrent cancel requests create exactly one refund log.

**Likely bug:** Status is checked before any atomic update, and no uniqueness constraint prevents multiple refund logs.

**Suggested tests:**

- Fire multiple parallel cancellation requests.
- Assert one success, remaining `409 ALREADY_CANCELLED`, and exactly one refund log.

## 5. Refund Log Can Commit Without Completed Cancellation

**Files/lines:**

- `app/services/refunds.py:24`
- `app/services/refunds.py:25`
- `app/routers/bookings.py:213`

**Expected:** Cancellation status and refund log are atomic.

**Likely bug:** `log_refund()` commits before booking status changes to cancelled.

**Suggested tests:**

- Simulate failure after refund logging and before final booking commit.
- Assert no refund exists unless booking status is cancelled.

