# Fix Script: Cancellation And Refunds

## Goal

Make cancellation permissions, refund calculation, refund logging, and cache invalidation match the contract.

## Files To Edit

- `app/routers/bookings.py`
- `app/services/refunds.py`
- `app/models.py`
- `app/cache.py`

## Steps

1. Fix refund tiers.
   - `notice >= 48h` gives 100.
   - `24h <= notice < 48h` gives 50.
   - `notice < 24h` gives 0.
   - Compare using `timedelta`, not floored integer hours.

2. Fix half-up rounding.
   - Use integer arithmetic.
   - Example: 50 percent of 1001 cents is 501.

3. Compute refund amount once.
   - Use the same amount for response and `RefundLog`.

4. Make cancellation atomic.
   - Avoid committing refund log before booking status update.
   - Prevent duplicate refund logs under concurrent cancellation.

5. Invalidate availability after cancellation.
   - Clear room/date availability cache for the cancelled booking.
   - Keep report cache invalidation.

## Required Tests

- 48h notice gives 100 percent.
- 24h notice gives 50 percent.
- Under 24h gives 0 percent.
- Half-cent refund rounds up.
- Cancel response equals stored refund log.
- Second cancel returns `409 ALREADY_CANCELLED`.
- Concurrent cancel creates exactly one refund log.
- Availability updates after cancellation.

## Acceptance

- Cancel response shape remains exact.
- `RefundLog` count is exactly one per cancelled booking.

