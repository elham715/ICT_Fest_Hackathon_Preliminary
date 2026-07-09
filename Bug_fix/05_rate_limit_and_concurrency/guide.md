# Rate Limit And Concurrency Bugs

## Start Here

Find bugs by sending repeated or parallel requests. The contract explicitly says rate limit, booking conflict, quota, reference code creation, and cancellation must hold under concurrent requests.

## Contract Rules

- `POST /bookings` allows 20 requests per rolling 60 seconds per user.
- All booking-create requests count, successful or not.
- Excess booking-create requests return `429 RATE_LIMITED`.
- Conflict checks must hold under concurrent requests.
- Quota checks must hold under concurrent requests.
- Reference codes must be unique under concurrent creation.
- Concurrent cancellation must create exactly one refund log.

## Files To Inspect

- `app/services/ratelimit.py`
- `app/routers/bookings.py`
- `app/services/reference.py`
- `app/services/refunds.py`
- `app/database.py`
- `app/models.py`

## Tests To Add Or Run

- Send 21 booking-create requests as the same user and expect the 21st to return `429`.
- Confirm failed booking-create attempts still count toward the limit.
- Create competing bookings for the same room/time in parallel and expect only one success.
- Create multiple bookings in parallel near quota and expect no more than 3 confirmed in the window.
- Cancel the same booking in parallel and expect one success plus one refund log.

## Common Failure Signs

- In-memory rate limiter is not protected by a lock.
- Check-then-insert booking logic has no transaction or database constraint.
- Reference code generation retries are missing.
- Cancellation checks status before another request commits.

