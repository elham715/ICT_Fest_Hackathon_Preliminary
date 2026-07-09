# Fix Script: Rate Limit And Concurrency

## Goal

Make rate limit, conflict, quota, cancellation, reference-code, and stats behavior safe under concurrent requests.

## Files To Edit

- `app/services/ratelimit.py`
- `app/routers/bookings.py`
- `app/services/reference.py`
- `app/models.py`
- `app/services/stats.py`
- `app/services/refunds.py`

## Steps

1. Make rate limiting atomic.
   - Protect bucket read/filter/append/check with a lock.
   - Ensure failed booking attempts still count.

2. Serialize booking creation where needed.
   - Protect conflict and quota check plus insert as one critical section.
   - Keep the lock scope as small as practical.
   - Preserve error codes: `ROOM_CONFLICT`, `QUOTA_EXCEEDED`.

3. Make reference-code creation safe.
   - Lock counter updates or generate database-backed unique values.
   - Add a database uniqueness defense if compatible with current schema creation.

4. Make cancellation atomic.
   - Ensure only one cancellation succeeds.
   - Ensure exactly one refund log exists.

5. Remove or neutralize race-prone in-memory stats.
   - Prefer DB-derived stats in the stats endpoint.

## Required Tests

- 25 parallel booking creates produce rate-limit failures after 20 attempts.
- Parallel identical bookings produce one success and one `409 ROOM_CONFLICT`.
- Parallel quota attempts never exceed 3 confirmed bookings.
- Parallel reference-code creation never duplicates codes.
- Parallel cancellation creates exactly one refund log.
- Stats match DB after concurrent create/cancel.

## Acceptance

- No valid concurrent request hangs.
- `pytest -q` passes repeatedly.

