# Fix Script: Multi-Tenancy

## Goal

Ensure every route scopes data to the caller's organization and member visibility rules.

## Files To Edit

- `app/routers/bookings.py`
- `app/services/export.py`
- `app/routers/admin.py`

## Steps

1. Fix booking detail visibility.
   - Same-org admins may read any same-org booking.
   - Members may read only their own bookings.
   - Unauthorized member access returns `404 BOOKING_NOT_FOUND`, not `403`.

2. Fix export scoping.
   - Every export path must join through `Room` and filter by `Room.org_id == admin.org_id`.
   - `include_all=true&room_id=<id>` must not bypass org scoping.

3. Recheck room and booking lookup paths.
   - Cross-org room id should return `404 ROOM_NOT_FOUND`.
   - Cross-org booking id should return `404 BOOKING_NOT_FOUND`.

## Required Tests

- Same-org member cannot read another member's booking.
- Same-org admin can read another member's booking.
- Cross-org user cannot read booking or room data.
- Admin export cannot include another org's bookings.

## Acceptance

- No response schema changes.
- Unauthorized resource IDs behave as non-existent.

