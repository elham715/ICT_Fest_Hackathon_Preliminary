# Cancellation And Refund Bugs

## Start Here

Find bugs by creating bookings at specific future notice windows, then cancelling as owner, same-org admin, another member, and cross-org users.

## Contract Rules

- Only the booking owner or same-org admin may cancel.
- Cancelling an already cancelled booking returns `409 ALREADY_CANCELLED`.
- Notice >= 48 hours gives 100 percent refund.
- Notice >= 24 hours and < 48 hours gives 50 percent refund.
- Notice < 24 hours gives 0 percent refund.
- Half-cents round up.
- A cancelled booking has exactly one `RefundLog`.
- Cancel response amount equals the stored `RefundLog` amount.

## Files To Inspect

- `app/routers/bookings.py`
- `app/services/refunds.py`
- `app/models.py`
- `app/serializers.py`
- `app/errors.py`

## Tests To Add Or Run

- Cancel 49-hour-notice booking and expect 100 percent refund.
- Cancel 25-hour-notice booking and expect 50 percent refund.
- Cancel 23-hour-notice booking and expect 0 percent refund.
- Cancel booking priced at `1001` cents with 50 percent refund and expect `501`.
- Cancel twice and expect second call to return `409 ALREADY_CANCELLED`.
- Verify only one refund log exists.
- Verify owner and same-org admin can cancel.
- Verify another member gets `404 BOOKING_NOT_FOUND`.

## Common Failure Signs

- Refund calculation uses floor rounding.
- Cancellation creates multiple refund logs.
- Admin cancellation is allowed across organizations.
- Cancel response uses calculated amount while database stores another amount.

