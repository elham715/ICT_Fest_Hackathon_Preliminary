# Multi-Tenancy Issues

## 1. Same-Org Members Can Read Each Other's Booking Details

**Files/lines:**

- `app/routers/bookings.py:156`

**Expected:** Members may read only their own bookings. Same-org admins may read any same-org booking. Unauthorized booking IDs should return `404 BOOKING_NOT_FOUND`.

**Likely bug:** `get_booking()` filters by booking id and room org, then returns the booking without checking `booking.user_id == user.id` for non-admin users.

**Suggested tests:**

- Create org admin, member A, and member B.
- Member A creates a booking.
- Member B `GET /bookings/{id}` returns `404 BOOKING_NOT_FOUND`.
- Same-org admin can read it.
- Cross-org user/admin gets `404`.

## 2. Admin Export Can Leak Cross-Org Bookings

**Files/lines:**

- `app/services/export.py:48`
- `app/services/export.py:22`
- `app/routers/admin.py:72`

**Expected:** Admins only act inside their own organization. Cross-org room IDs should behave as not found or produce no cross-org data.

**Likely bug:** `generate_export()` uses `fetch_bookings_raw()` when `include_all=true` and `room_id` is supplied. That query filters only by `Booking.room_id`, without scoping to the caller's org.

**Suggested tests:**

- Create Org A admin and Org B room with a booking.
- Org A admin calls `/admin/export?include_all=true&room_id=<org_b_room_id>`.
- Assert Org B booking is not included.
- Verify same-org room export still works.

