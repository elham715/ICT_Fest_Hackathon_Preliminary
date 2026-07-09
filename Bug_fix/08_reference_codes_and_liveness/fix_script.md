# Fix Script: Reference Codes And Liveness

## Goal

Guarantee reference-code uniqueness and remove liveness hazards from request paths.

## Files To Edit

- `app/services/reference.py`
- `app/models.py`
- `app/services/notifications.py`
- `app/database.py`
- `app/routers/bookings.py`

## Steps

1. Make reference-code generation safe.
   - Use a lock or database-backed uniqueness.
   - Add a uniqueness defense for `Booking.reference_code` if possible.
   - Avoid duplicate codes after process restart.

2. Standardize notification lock order.
   - `notify_created()` and `notify_cancelled()` must acquire locks in the same order.

3. Reduce liveness hazards.
   - Remove unnecessary sleeps from critical request paths where safe.
   - Avoid long database lock waits causing request stalls.

4. Recheck concurrency with health checks.
   - `/health` should remain responsive during concurrent booking/cancel bursts.

## Required Tests

- Concurrent booking creation never duplicates reference codes.
- Reference codes do not repeat after counter reset/restart simulation.
- Concurrent create/cancel notification calls do not deadlock.
- `/health` remains responsive during valid concurrent requests.

## Acceptance

- Service does not hang under concurrent valid requests.
- Reference codes remain unique in persisted bookings.

