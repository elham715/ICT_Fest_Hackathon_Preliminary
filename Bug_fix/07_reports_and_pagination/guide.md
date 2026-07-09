# Reports, Availability, Stats, And Pagination Bugs

## Start Here

Find bugs by creating a controlled set of rooms and bookings, then checking reads immediately after booking and cancellation operations.

## Contract Rules

- `GET /bookings` returns caller's own bookings only.
- Default page is 1 and default limit is 10.
- Limit max is 100.
- Bookings are sorted by `start_time` ascending, then `id` ascending.
- Sequential pages must not skip or repeat items.
- Response includes `total`.
- Usage report includes all same-org rooms, including rooms with zero bookings.
- Usage report counts confirmed bookings starting in `[from, to]` UTC inclusive.
- Availability returns confirmed busy intervals starting on the UTC date.
- Room stats reflect current confirmed booking count and revenue.
- Reports, availability, and stats reflect current state immediately.

## Files To Inspect

- `app/routers/bookings.py`
- `app/routers/admin.py`
- `app/routers/rooms.py`
- `app/services/stats.py`
- `app/services/export.py`
- `app/cache.py`
- `app/serializers.py`

## Tests To Add Or Run

- Create 12 bookings and verify page 1/page 2 order and `total`.
- Create same-time bookings and verify `id` tie-break ordering.
- Verify another member's bookings do not appear in member list.
- Verify admin usage report includes zero-booking rooms.
- Cancel a booking and verify stats and reports update immediately.
- Verify availability excludes cancelled bookings.
- Verify usage report does not include cross-org rooms.
- Verify export CSV header is exact.

## Common Failure Signs

- Cached reports are stale after booking or cancellation.
- Usage report excludes rooms with zero bookings.
- Pagination sorts only by `id` or only by `created_at`.
- Availability uses local dates instead of UTC dates.
- Stats include cancelled bookings.

