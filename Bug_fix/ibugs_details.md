# CoWork API - Comprehensive Bug Analysis & Fix Details

This document contains a complete breakdown of all **26 bugs** discovered and resolved in the CoWork multi-tenant coworking space booking API.

---

## 1. Token Revocation Check (User ID vs. Token ID Mismatch)
- **File & Lines:** `app/auth.py`
- **Root Cause:** `get_token_payload` checked if the user ID (`payload.get("sub")`) was in the `_revoked_tokens` set. However, `revoke_access_token` added the token's unique ID (`payload["jti"]`) to the set.
- **Impact:** Revoked access tokens could still be used until their expiration, meaning logout was ineffective.
- **Resolution:** Replaced `_revoked_tokens` with a lock-guarded, thread-safe `_invalidated_jtis` set and updated `get_token_payload` to check `is_jti_invalidated(payload.get("jti"))`.

---

## 2. Incorrect Access Token Lifetime
- **File & Lines:** `app/auth.py`
- **Root Cause:** The access token lifetime calculation was using `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 60)`. Since `ACCESS_TOKEN_EXPIRE_MINUTES` is `15`, this evaluated to 900 minutes (15 hours).
- **Impact:** Tokens lasted for 15 hours instead of the strictly required 900 seconds (15 minutes).
- **Resolution:** Corrected to `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)`.

---

## 3. Malformed Token Subject (sub) Can Become A 500
- **File & Lines:** `app/auth.py` & `app/routers/auth.py`
- **Root Cause:** In `get_current_user` and `/auth/refresh`, calling `int(payload["sub"])` raised a `ValueError` or `KeyError` if `sub` was missing, non-numeric, or malformed.
- **Impact:** An invalid or malformed JWT payload returned a 500 Server Error instead of the expected `401` unauthorized code.
- **Resolution:** Wrapped `sub` parsing in a `try-except` block, raising `AppError(401, "UNAUTHORIZED", ...)` if parsing fails.

---

## 4. Missing Duplicate Username Validation
- **File & Lines:** `app/routers/auth.py`
- **Root Cause:** In registration, if a username already existed within the requested organization, the route returned the user details instead of raising a conflict error.
- **Impact:** Allowed duplicate usernames inside the same organization, violating the rule: *"A duplicate username within the org -> 409 USERNAME_TAKEN"*.
- **Resolution:** Raised `AppError(409, "USERNAME_TAKEN", ...)` if an existing user with the same username is found in the organization.

---

## 5. Concurrent Registration IntegrityError (500 Server Error)
- **File & Lines:** `app/routers/auth.py`
- **Root Cause:** Concurrent registration requests checked user existence first, then wrote to the database. If two identical requests passed the check, one succeeded and the other threw a database `IntegrityError` on the `uq_user_org_username` constraint.
- **Impact:** Concurrent registrations caused unhandled 500 errors.
- **Resolution:** Wrapped database commits in registration with `try-except IntegrityError` blocks to roll back and return a clean `409 USERNAME_TAKEN` instead of a 500.

---

## 6. Single-Use Refresh Token Reuse Allowed
- **File & Lines:** `app/routers/auth.py`
- **Root Cause:** The refresh endpoint `/auth/refresh` did not verify if a refresh token was previously used and did not invalidate the presented token.
- **Impact:** Refresh tokens could be reused indefinitely to generate new access tokens.
- **Resolution:** Added a check to verify if the refresh token's JTI is in the `_invalidated_jtis` set (raising `401` on reuse) and calls `invalidate_jti(jti)` to mark it as consumed.

---

## 7. Past-Booking Start Time Grace Window Allowed
- **File & Lines:** `app/routers/bookings.py`
- **Root Cause:** The check `start <= now - timedelta(seconds=300)` allowed starting bookings up to 5 minutes in the past.
- **Impact:** Allowed retrospective bookings, violating the rule: *"start_time must be strictly in the future - no grace window."*
- **Resolution:** Enforced strict future start times using `if start <= now: raise AppError(...)`.

---

## 8. Invalid Datetime Strings Cause 500 Errors
- **File & Lines:** `app/timeutils.py` & `app/routers/bookings.py`
- **Root Cause:** Passing an invalid datetime format (e.g., `"not-a-date"`) to `/bookings` caused `datetime.fromisoformat()` to throw a `ValueError` which went uncaught.
- **Impact:** Invalid formats returned 500 Internal Server Errors instead of `400 INVALID_BOOKING_WINDOW`.
- **Resolution:** Wrapped `fromisoformat()` in `parse_input_datetime` inside a `try-except` block, raising `AppError(400, "INVALID_BOOKING_WINDOW")` on error.

---

## 9. Zero, Negative, or Invalid Booking Durations Allowed
- **File & Lines:** `app/routers/bookings.py`
- **Root Cause:** The duration validation did not check if `end_time` was after `start_time` or check the minimum duration of 1 hour.
- **Impact:** Allows negative/fractional duration bookings (e.g. `end_time` before `start_time` bypassed duration checks).
- **Resolution:** Added check `if end <= start` and validated that duration is an integer multiple of 1 hour and falls between 1 and 8 hours.

---

## 10. Overlap Logic Blocked Back-to-Back Bookings
- **File & Lines:** `app/routers/bookings.py`
- **Root Cause:** The overlap helper used `<=` and `>=` checks (`b.start_time <= end and start <= b.end_time`) which blocked back-to-back bookings.
- **Impact:** Back-to-back bookings (one starting exactly when another ends) were incorrectly blocked.
- **Resolution:** Changed to strict `<` comparisons: `b.start_time < end and start < b.end_time`.

---

## 11. Stale Reports Cache (Cache Invalidation Missing on Booking)
- **File & Lines:** `app/routers/bookings.py`
- **Root Cause:** Creating a booking did not invalidate the organization's cached usage report.
- **Impact:** Pulled reports served stale data, violating: *"The report must reflect the current state immediately."*
- **Resolution:** Added `cache.invalidate_report(user.org_id)` to the booking creation flow.

---

## 12. Stale Reports Cache (Cache Invalidation Missing on Room Creation)
- **File & Lines:** `app/routers/rooms.py`
- **Root Cause:** Creating a room did not invalidate the usage report cache.
- **Impact:** Stale report outputs where newly created rooms were omitted.
- **Resolution:** Added `cache.invalidate_report(admin.org_id)` to the room creation flow.

---

## 13. Stale Availability Cache on Cancellation
- **File & Lines:** `app/routers/bookings.py`
- **Root Cause:** Cancelling a booking did not invalidate the room's availability cache.
- **Impact:** Stale availability lookup returned old busy intervals for the cancelled booking.
- **Resolution:** Added `cache.invalidate_availability(booking.room_id, booking.start_time.date().isoformat())` inside the cancellation handler.

---

## 14. Booking List Ordering, Pagination, and Hardcoded Limits
- **File & Lines:** `app/routers/bookings.py`
- **Root Cause:**
  1. Sorted bookings descending by `start_time` instead of ascending.
  2. Offset calculation was `page * limit` instead of `(page - 1) * limit`.
  3. Hardcoded `.limit(10)` regardless of the user-provided `limit` query parameter.
- **Impact:** Caused navigation issues, skipped items, and ignored query limits.
- **Resolution:** Sorted by `start_time.asc()`, computed `offset = (page - 1) * limit`, and used `.limit(limit)`.

---

## 15. Booking Detail Visibility Leaked to Non-Owners
- **File & Lines:** `app/routers/bookings.py`
- **Root Cause:** Members could view details of any booking in their organization because the ownership constraint was missing.
- **Impact:** Leaked booking info to non-owners within the same tenant org, violating visibility rules.
- **Resolution:** Added check `if user.role != "admin" and booking.user_id != user.id: raise AppError(404, "BOOKING_NOT_FOUND", ...)` to enforce visibility rules.

---

## 16. Booking Detail Overwrote Start Time with Creation Time
- **File & Lines:** `app/routers/bookings.py`
- **Root Cause:** The `/bookings/{booking_id}` endpoint set `response["start_time"] = iso_utc(booking.created_at)`.
- **Impact:** Booking detail responses wrongly showed the booking creation timestamp as the actual booking start time.
- **Resolution:** Removed the line so the correct start time remains populated.

---

## 17. Erroneous Cancellation Notice Tier and Refund Percentages
- **File & Lines:** `app/routers/bookings.py`
- **Root Cause:**
  - If notice was exactly 48 hours, it calculated a 50% refund instead of 100%.
  - If notice was under 24 hours, it gave a 50% refund instead of 0%.
- **Impact:** Refund policy calculations were incorrect and unfair to users.
- **Resolution:** Reimplemented the comparison tiers using strict `timedelta(hours=48)` and `timedelta(hours=24)` checks.

---

## 18. Inconsistent Refund Log Cent Rounding
- **File & Lines:** `app/services/refunds.py` & `app/routers/bookings.py`
- **Root Cause:** The cancel endpoint rounded using Python's banker's rounding (`round()`), but the refund ledger truncated values (`int()`).
- **Impact:** Mismatch between the cancellation API response and the recorded RefundLog (e.g. 50% of 1001 resulted in 501 in the API but 500 in the database).
- **Resolution:** Applied the integer rounding formula `(price * percent + 50) // 100` to both calculations, ensuring perfect agreement and compliance with the "half-cents round up" rule.

---

## 19. Non-Atomic Cancellation Commit (Partial Commits)
- **File & Lines:** `app/services/refunds.py` & `app/routers/bookings.py`
- **Root Cause:** `log_refund` executed a database commit internally before the booking status was updated to cancelled in `cancel_booking`.
- **Impact:** If the server crashed or failed in between, a `RefundLog` was created without the booking status actually updating to cancelled.
- **Resolution:** Removed `db.commit()` and `db.refresh(entry)` from `log_refund`, executing a single transaction commit inside `cancel_booking` instead.

---

## 20. Notification Lock Order Deadlock
- **File & Lines:** `app/services/notifications.py`
- **Root Cause:** `notify_created` acquired `_email_lock` then `_audit_lock`, but `notify_cancelled` acquired `_audit_lock` then `_email_lock`.
- **Impact:** Simultaneous creation and cancellation requests caused threads to block each other indefinitely, deadlocking the server.
- **Resolution:** Unnested the lock scopes in both functions so `_email_lock` and `_audit_lock` are acquired sequentially instead of nested.

---

## 21. Non-Thread-Safe Sequential Reference Codes
- **File & Lines:** `app/services/reference.py`
- **Root Cause:** Under concurrent booking requests, multiple threads could read the same `_counter["value"]` before it was incremented.
- **Impact:** Created duplicate booking reference codes, violating uniqueness rules.
- **Resolution:** Guarded the reference code generation blocks with a thread lock (`_counter_lock`).

---

## 22. Reference Codes Repeat After Server Restart
- **File & Lines:** `app/services/reference.py`
- **Root Cause:** The sequential reference code counter was process-local and reset to `1000` on server startup.
- **Impact:** After a container restart, reference codes duplicated existing records already in the database.
- **Resolution:** Added lazy-initialization on first use, querying the database for the highest existing reference code number and starting from there.

---

## 23. Room Stats Loss on Server Restart & Thread-Safety
- **File & Lines:** `app/services/stats.py`
- **Root Cause:** Room booking count and revenue stats were stored strictly in-memory and lost on container restart. They also suffered from race conditions under concurrent updates.
- **Impact:** Container restart reset room stats to 0 even if bookings existed. Concurrency updates could also go out of sync.
- **Resolution:** Added a thread lock (`_stats_lock`) and modified the getter to lazy-load starting stats from the SQLite database if they are not already initialized in memory.

---

## 24. Cross-Org CSV Export Leaks
- **File & Lines:** `app/services/export.py` & `app/routers/admin.py`
- **Root Cause:** The `/admin/export` router did not verify room ownership, and the export generator used `fetch_bookings_raw(db, room_id)` which bypassed organization scoping.
- **Impact:** Violates multi-tenancy rules. Any administrator could export bookings of rooms belonging to other organizations.
- **Resolution:** Enforced cross-organization verification on the requested `room_id` inside `admin.py` (returning 404 if invalid), and updated the generator to query bookings scoped to the administrator's organization.

---

## 25. Timezone normalization conversion error
- **File & Lines:** `app/timeutils.py`
- **Root Cause:** In `parse_input_datetime`, if `dt.tzinfo` was not None, it replaced the timezone directly using `dt.replace(tzinfo=None)` without converting it to UTC first.
- **Impact:** The code stripped timezone offsets instead of converting them. E.g. `2026-07-09T18:00:00+02:00` was stored as `18:00:00` instead of `16:00:00` UTC.
- **Resolution:** Corrected to use `.astimezone(timezone.utc).replace(tzinfo=None)`.

---

## 26. SQLite Concurrency Locking (Race Conditions)
- **File & Lines:** `app/database.py`
- **Root Cause:** Transactions defaulted to `DEFERRED`, meaning SQLite did not acquire a write lock until a write operation was performed.
- **Impact:** Under concurrent requests, two threads could concurrently read the database, bypass overlap/quota checks, and then write, causing double-bookings or database locking errors.
- **Resolution:** Enabled SQLite WAL mode and listened to SQLAlchemy `begin` events to execute `BEGIN IMMEDIATE` transactions, serializing writer sessions cleanly.
