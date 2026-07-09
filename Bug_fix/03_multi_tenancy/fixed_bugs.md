# Fixed Bugs - Multi-Tenancy

The following bugs from `issues.md` have been fixed:

1. **Same-Org Members Can Read Each Other's Booking Details**
   - **Resolution**: Added ownership validation in `/bookings/{booking_id}` in `app/routers/bookings.py` ensuring non-admin members can only query bookings they own, returning `404 BOOKING_NOT_FOUND` if unauthorized.
2. **Admin Export Can Leak Cross-Org Bookings**
   - **Resolution**: Verified that the requested `room_id` belongs to the admin's organization in `/admin/export` inside `app/routers/admin.py`, raising `404 ROOM_NOT_FOUND` if it belongs to another organization.
