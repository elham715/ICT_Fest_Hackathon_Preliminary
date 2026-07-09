# Multi-Tenancy Bugs

## Start Here

Find bugs by creating two organizations and trying to read or mutate resources across organization boundaries. Cross-org resources should behave as if they do not exist.

## Contract Rules

- Users may only read or act on data in their own organization.
- Cross-org room IDs return `404 ROOM_NOT_FOUND`.
- Cross-org booking IDs return `404 BOOKING_NOT_FOUND`.
- Admins are powerful only inside their own organization.
- Members may read and cancel only their own bookings.

## Files To Inspect

- `app/routers/rooms.py`
- `app/routers/bookings.py`
- `app/routers/admin.py`
- `app/auth.py`
- `app/models.py`

## Tests To Add Or Run

- Org A user cannot list or access Org B rooms.
- Org A user cannot create a booking for Org B room.
- Org A admin cannot cancel Org B booking.
- Member cannot read another member's booking in the same org.
- Member cannot cancel another member's booking in the same org.
- Admin can read and cancel same-org bookings.

## Common Failure Signs

- Query filters by `id` but not `org_id`.
- Admin routes assume admin means global admin.
- Booking lookups join room/user data without checking organization.
- Unauthorized same-org member access returns `403` instead of `404 BOOKING_NOT_FOUND`.

