# Fixed Bugs - Datetime

The following bugs from `issues.md` have been fixed:

1. **Offset Inputs Are Not Converted To UTC**
   - **Resolution**: Updated `parse_input_datetime` in `app/timeutils.py` to normalize timezone-aware offsets to UTC via `.astimezone(timezone.utc)` before stripping `tzinfo`.
2. **Invalid Datetime Strings Can Raise 500s**
   - **Resolution**: Wrapped `fromisoformat` in a `try-except ValueError` block inside `parse_input_datetime` to raise a clean `AppError(400, "INVALID_BOOKING_WINDOW", ...)` instead of a 500.
3. **Near-Past Bookings Are Accepted**
   - **Resolution**: Replaced the 5-minute grace check in `app/routers/bookings.py` with `start <= now`.
4. **Zero, Negative, And Sub-1-Hour Durations Are Accepted**
   - **Resolution**: Enforced `duration_hours < MIN_DURATION_HOURS` checking in `app/routers/bookings.py` to ensure only whole hours between 1 and 8 are accepted.
5. **Back-To-Back Bookings Conflict Incorrectly**
   - **Resolution**: Changed adjacent booking conflict logic from `<=` to `<` inside `_has_conflict` in `app/routers/bookings.py`.
6. **Booking Detail Overwrites `start_time`**
   - **Resolution**: Removed the line in `/bookings/{booking_id}` endpoint in `app/routers/bookings.py` that overwrote `response["start_time"]` with `created_at`.
7. **Usage Report Accepts Reversed Date Ranges**
   - **Resolution**: Added validation `from_date > to_date` inside `/admin/usage-report` in `app/routers/admin.py` to reject reversed date ranges with `400`.
