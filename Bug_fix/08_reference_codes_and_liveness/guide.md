# Reference Codes And Liveness Bugs

## Start Here

Find bugs by stressing code generation and failure paths. This lane catches issues that may not show up in happy-path smoke tests.

## Contract Rules

- Every booking reference code is unique.
- Uniqueness must hold under concurrent creation.
- The service must respond to all endpoints at all times.
- No combination of concurrent valid requests may hang the service.

## Files To Inspect

- `app/services/reference.py`
- `app/routers/bookings.py`
- `app/database.py`
- `app/models.py`
- `app/main.py`
- `app/errors.py`

## Tests To Add Or Run

- Create many bookings and assert all reference codes are unique.
- Create bookings concurrently and assert no duplicate reference codes.
- Force or simulate reference collision and verify retry behavior if supported.
- Hit `/health` during concurrent booking and cancellation load.
- Verify error handlers return responses instead of hanging or leaking raw exceptions.

## Common Failure Signs

- Reference codes are based only on timestamp or predictable short random values.
- Database model lacks uniqueness for `reference_code`.
- Collision handling is absent.
- Global locks are held while doing slow work.
- Exceptions escape without application error formatting where the contract requires a code.

