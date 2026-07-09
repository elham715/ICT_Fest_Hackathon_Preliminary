# Fix Script: Reports And Pagination

## Goal

Make booking listing, usage reports, availability, stats, and exports reflect current scoped data.

## Files To Edit

- `app/routers/bookings.py`
- `app/routers/admin.py`
- `app/routers/rooms.py`
- `app/services/stats.py`
- `app/services/export.py`
- `app/cache.py`

## Steps

1. Fix booking pagination.
   - Sort by `Booking.start_time.asc(), Booking.id.asc()`.
   - Use offset `(page - 1) * limit`.
   - Use `.limit(limit)`.
   - Preserve `total`.

2. Fix report cache invalidation.
   - Invalidate org usage reports after booking creation and cancellation.

3. Fix availability cache invalidation.
   - Invalidate room/date availability after booking creation and cancellation.

4. Make stats DB-derived.
   - Query confirmed bookings for the room.
   - Return count and sum of `price_cents`.

5. Fix export scoping.
   - Ensure all export variants are org-scoped.
   - Preserve exact CSV header.

## Required Tests

- Page 1/page 2 do not skip or repeat.
- `limit` parameter is respected.
- Sorting is start time ascending, id ascending.
- Usage report updates after create/cancel.
- Availability excludes cancelled bookings.
- Stats match confirmed bookings after create/cancel.
- Export cannot leak cross-org data.

## Acceptance

- Report, availability, stats, and export response fields stay unchanged.

