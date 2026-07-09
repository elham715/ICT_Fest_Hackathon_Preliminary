# Sanity Check

## Are We Likely To Be Competitive?

Yes, if we fix the confirmed issues cleanly. The current inventory covers the categories most likely to score well in hidden black-box grading:

- deterministic correctness bugs
- auth lifecycle bugs
- tenant isolation bugs
- booking-window and overlap bugs
- cancellation/refund bugs
- report/cache/pagination bugs
- concurrency and liveness bugs

The strongest advantage is that we have found several **hard** bugs, not only easy one-liners. Hard bugs matter for both scoring and tie-breaking.

## Have We Found The Best Bugs?

Very likely, yes. The current list includes high-value contract violations:

- offset datetimes are not converted to UTC
- past starts are allowed
- back-to-back bookings are rejected
- duplicate registration returns success
- access token expiry is wrong
- logout and refresh invalidation are wrong
- members can read other members' bookings
- export can leak cross-org data
- refund tiers and rounding are wrong
- cancellation can create duplicate refund logs
- pagination skips items and ignores `limit`
- stats are not DB-derived
- reports and availability can be stale
- reference codes are not concurrency-safe
- notification locks can deadlock

## Have We Found All Bugs?

We should not assume all bugs are found. But the current set is broad enough to begin fixing confidently. The remaining discovery effort should focus on:

- hidden route combinations
- malformed token behavior
- exact error codes
- stale cache after every mutation
- concurrency behavior under repeated test runs
- CSV export edge cases

## Fixing Strategy

Fix deterministic behavior first, then concurrency.

Recommended sequence:

1. `01_datetime`
2. `02_auth`
3. `03_multi_tenancy`
4. `04_booking_creation`
5. `06_cancellation_refunds`
6. `07_reports_and_pagination`
7. `05_rate_limit_and_concurrency`
8. `08_reference_codes_and_liveness`

This order avoids chasing noisy failures caused by earlier foundational bugs.

## Competition Risk

The biggest risk is over-fixing. Do not redesign the app. Do not change schemas. Do not change endpoint names. Hidden tests care about API behavior, not elegance.

