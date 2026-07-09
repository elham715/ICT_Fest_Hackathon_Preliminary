# Fixed Bugs - Booking Creation

The following bugs from `issues.md` have been fixed:

1. **Past Or Immediate Starts Are Allowed**
   - **Resolution**: Removed the 5-minute grace check in `app/routers/bookings.py` and enforced `start <= now` directly.
2. **Zero Or Negative Duration Bookings Are Accepted**
   - **Resolution**: Enforced `duration_hours < MIN_DURATION_HOURS` checking in `app/routers/bookings.py` to ensure only whole hours between 1 and 8 are accepted.
3. **Back-To-Back Bookings Are Treated As Conflicts**
   - **Resolution**: Changed adjacent booking conflict logic from `<=` to `<` inside `_has_conflict` in `app/routers/bookings.py`.
