# Fix Plan

This plan ranks the bug lanes by dependency and hidden-grader risk. The 8 folders are the right collaboration structure; the PDF has 16 business rules, but many rules overlap in implementation.

## Why 8 Folders Are Better Than 16

- Several rules share the same code path.
- Splitting into 16 folders would duplicate work across booking creation, concurrency, and reporting.
- The 8 lanes map cleanly to modules and ownership boundaries.
- Agents can work independently without constantly touching the same files.

## Highest Priority Order

1. `01_datetime`
2. `02_auth`
3. `03_multi_tenancy`
4. `04_booking_creation`
5. `06_cancellation_refunds`
6. `07_reports_and_pagination`
7. `05_rate_limit_and_concurrency`
8. `08_reference_codes_and_liveness`

## Why This Order

- Datetime bugs affect bookings, refunds, availability, and reports.
- Auth bugs affect every protected endpoint.
- Multi-tenancy bugs are high-risk because hidden tests often probe cross-org access.
- Booking creation rules define most core data.
- Cancellation and reports depend on bookings being correct.
- Concurrency and liveness are hardest, so they should be fixed after deterministic behavior is correct.

## Puku CLI Triage Rules

- Add findings marked hard and contract-backed.
- Keep lower-priority risks only when they can affect hidden tests.
- Do not add notes that the contract explicitly allows, such as `+00:00` datetime output.
- Do not fix style, validation, or security concerns unless the PDF requires them.

## Confirmed Puku Additions

- Duplicate same-org registration returns success instead of `409 USERNAME_TAKEN`.
- Malformed signed token subject can raise a server error instead of `401`.
- Cancellation does not invalidate availability cache.
- Notification lock order can deadlock.
- Rate-limit sleep widens the concurrency race.
- Reference-code uniqueness needs both runtime safety and database defense.

