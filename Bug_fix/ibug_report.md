# CoWork API - Complete Bug Report

This document outlines all **26 bugs** identified and fixed in the CoWork Multi-Tenant Coworking Space Booking API.

---

## 1. Token Revocation Check (User ID vs. Token ID Mismatch)
* **File & Lines:** `app/auth.py`
* **The Bug:** `get_token_payload` checked if the user ID (`payload.get("sub")`) was in `_revoked_tokens`. However, `revoke_access_token` added the token's unique ID (`payload["jti"]`) to the set.
* **Why it caused incorrect behavior:** Logout was ineffective because the verification checked the user ID against the token ID list.
* **How it was fixed:** Replaced `_revoked_tokens` with a lock-guarded, thread-safe `_invalidated_jtis` set and updated `get_token_payload` to check `is_jti_invalidated(payload.get("jti"))`.

---

## 2. Incorrect Access Token Lifetime
* **File & Lines:** `app/auth.py`
* **The Bug:** Access token expiration calculation was `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 60)`. Since `ACCESS_TOKEN_EXPIRE_MINUTES` is `15`, this evaluated to 900 minutes (15 hours) instead of 15 minutes.
* **Why it caused incorrect behavior:** Tokens lasted for 15 hours instead of the strictly required 900 seconds.
* **How it was fixed:** Corrected the calculation to `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)`.

---

## 3. Malformed Token Subject (sub) Can Become A 500
* **File & Lines:** `app/auth.py` & `app/routers/auth.py`
* **The Bug:** `int(payload["sub"])` in `get_current_user` and `/auth/refresh` raised `ValueError` or `KeyError` if the subject was missing or malformed.
* **Why it caused incorrect behavior:** Bad subject format in JWTs returned a 500 error instead of a 401.
* **How it was fixed:** Wrapped the parsing in `try-except` blocks, raising `AppError(401, "UNAUTHORIZED", ...)` on failure.

---

## 4. Missing Duplicate Username Validation
* **File & Lines:** `app/routers/auth.py`
* **The Bug:** Registration returned existing user info on duplicate usernames instead of raising a conflict error.
* **Why it caused incorrect behavior:** Violates registration uniqueness rules.
* **How it was fixed:** Added a check that raises `AppError(409, "USERNAME_TAKEN", ...)` on duplicate same-org username registration.

---

## 5. Concurrent Registration IntegrityError (500 Server Error)
* **File & Lines:** `app/routers/auth.py`
* **The Bug:** Concurrent duplicate username registrations could both pass the existence check, causing one to fail on database commit with an `IntegrityError`.
* **Why it caused incorrect behavior:** Raised unhandled 500 errors during concurrent duplicate creations.
* **How it was fixed:** Wrapped commits in registration with `try-except IntegrityError` to roll back and raise `409 USERNAME_TAKEN`.

---

## 6. Single-Use Refresh Token Reuse Allowed
* **File & Lines:** `app/routers/auth.py`
* **The Bug:** `/auth/refresh` did not revoke old refresh tokens or check for their reuse.
* **Why it caused incorrect behavior:** Old refresh tokens could be reused indefinitely.
* **How it was fixed:** Validated if the refresh token JTI is in the `_invalidated_jtis` set and marked it invalid upon successful rotation.

---

## 7. Past-Booking Start Time Grace Window Allowed
* **File & Lines:** `app/routers/bookings.py`
* **The Bug:** Allowed bookings starting up to 5 minutes in the past.
* **Why it caused incorrect behavior:** Violates the rule that bookings must start in the future.
* **How it was fixed:** Checked `if start <= now: raise AppError(...)`.

---

## 8. Invalid Datetime Strings Cause 500 Errors
* **File & Lines:** `app/timeutils.py` & `app/routers/bookings.py`
* **The Bug:** Passing invalid datetime strings triggered a `ValueError` inside `fromisoformat()`.
* **Why it caused incorrect behavior:** Caused 500 server errors on invalid date inputs.
* **How it was fixed:** Caught errors in `parse_input_datetime` and raised `AppError(400, "INVALID_BOOKING_WINDOW")`.

---

## 9. Zero, Negative, or Invalid Booking Durations Allowed
* **File & Lines:** `app/routers/bookings.py`
* **The Bug:** Did not check if `end_time` was after `start_time` or enforce the 1-hour minimum.
* **Why it caused incorrect behavior:** Allowed zero or negative duration bookings with zero or negative prices.
* **How it was fixed:** Enforced `end > start` and validated that duration is an integer between 1 and 8 hours.

---

## 10. Overlap Logic Blocked Back-to-Back Bookings
* **File & Lines:** `app/routers/bookings.py`
* **The Bug:** Overlap checks used inclusive comparisons (`<=` and `>=`).
* **Why it caused incorrect behavior:** Blocked adjacent back-to-back bookings.
* **How it was fixed:** Changed comparison operators to strict `<` checks.

---

## 11. Stale Reports Cache (Cache Invalidation Missing on Booking)
* **File & Lines:** `app/routers/bookings.py`
* **The Bug:** Booking creation failed to invalidate the usage report cache.
* **Why it caused incorrect behavior:** Served stale reports immediately after booking.
* **How it was fixed:** Added `cache.invalidate_report(user.org_id)` to the booking creation flow.

---

## 12. Stale Reports Cache (Cache Invalidation Missing on Room Creation)
* **File & Lines:** `app/routers/rooms.py`
* **The Bug:** Room creation failed to invalidate the report cache.
* **Why it caused incorrect behavior:** Reports did not show newly created rooms.
* **How it was fixed:** Added `cache.invalidate_report(admin.org_id)` to the room creation flow.

---

## 13. Stale Availability Cache on Cancellation
* **File & Lines:** `app/routers/bookings.py`
* **The Bug:** Cancellation failed to invalidate the availability cache.
* **Why it caused incorrect behavior:** Stale availability results showed the room as busy after cancellation.
* **How it was fixed:** Added `cache.invalidate_availability(...)` in the cancellation handler.

---

## 14. Booking List Ordering, Pagination, and Hardcoded Limits
* **File & Lines:** `app/routers/bookings.py`
* **The Bug:**
  - Sorted bookings descending by `start_time`.
  - Offset calculation was `page * limit` instead of `(page - 1) * limit`.
  - Hardcoded limit to 10.
* **Why it caused incorrect behavior:** Broke listing navigation and ignored query limits.
* **How it was fixed:** Sorted by `start_time.asc()`, computed `offset = (page - 1) * limit`, and used `.limit(limit)`.

---

## 15. Booking Detail Visibility Leaked to Non-Owners
* **File & Lines:** `app/routers/bookings.py`
* **The Bug:** Members could view details of any booking in their organization.
* **Why it caused incorrect behavior:** Allowed unauthorized access to other members' bookings.
* **How it was fixed:** Added ownership verification in `get_booking`.

---

## 16. Booking Detail Overwrote Start Time with Creation Time
* **File & Lines:** `app/routers/bookings.py`
* **The Bug:** `/bookings/{booking_id}` set `response["start_time"] = iso_utc(booking.created_at)`.
* **Why it caused incorrect behavior:** Displayed creation time as start time.
* **How it was fixed:** Removed the overwrite line.

---

## 17. Erroneous Cancellation Notice Tier and Refund Percentages
* **File & Lines:** `app/routers/bookings.py`
* **The Bug:**
  - If notice was exactly 48 hours, it gave a 50% refund.
  - If notice was under 24 hours, it gave a 50% refund.
* **Why it caused incorrect behavior:** Caused incorrect refund policy calculations.
* **How it was fixed:** Reimplemented tiers using strict `timedelta(hours=48)` and `timedelta(hours=24)` checks.

---

## 18. Inconsistent Refund Log Cent Rounding
* **File & Lines:** `app/services/refunds.py` & `app/routers/bookings.py`
* **The Bug:** Cancel endpoint rounded using banker's rounding (`round()`), but the refund ledger truncated values (`int()`).
* **Why it caused incorrect behavior:** Created discrepancies between response and DB logs.
* **How it was fixed:** Applied the integer rounding formula `(price * percent + 50) // 100` to both.

---

## 19. Non-Atomic Cancellation Commit (Partial Commits)
* **File & Lines:** `app/services/refunds.py` & `app/routers/bookings.py`
* **The Bug:** `log_refund` executed a database commit internally before the booking status was updated.
* **Why it caused incorrect behavior:** Allowed database states with a logged refund but no cancellation update if a crash occurred.
* **How it was fixed:** Removed internal commits in `log_refund` and let `cancel_booking` commit both atomically.

---

## 20. Notification Lock Order Deadlock
* **File & Lines:** `app/services/notifications.py`
* **The Bug:** `notify_created` locked email then audit, while `notify_cancelled` locked audit then email.
* **Why it caused incorrect behavior:** Simultaneous creates and cancels caused deadlocks.
* **How it was fixed:** Unnested the locks to acquire them sequentially.

---

## 21. Non-Thread-Safe Sequential Reference Codes
* **File & Lines:** `app/services/reference.py`
* **The Bug:** Parallel requests reading `_counter["value"]` simultaneously received duplicate codes.
* **Why it caused incorrect behavior:** Produced duplicate reference codes.
* **How it was fixed:** Guarded reference code generation with `_counter_lock`.

---

## 22. Reference Codes Repeat After Server Restart
* **File & Lines:** `app/services/reference.py`
- **The Bug:** The counter was process-local and reset to `1000` on startup.
- **Why it caused incorrect behavior:** Restarts caused reference codes to duplicate existing database records.
- **How it was fixed:** Lazy-initialized the counter from the database on first write.

---

## 23. Room Stats Loss on Server Restart & Thread-Safety
* **File & Lines:** `app/services/stats.py`
* **The Bug:** Room booking count and revenue stats were stored in-memory and lost on restart.
* **Why it caused incorrect behavior:** Restarts reset stats to 0.
* **How it was fixed:** Added a lock and enabled lazy-loading stats from the database on first call.

---

## 24. Cross-Org CSV Export Leaks
* **File & Lines:** `app/services/export.py` & `app/routers/admin.py`
* **The Bug:** Export endpoints did not verify room ownership, and the export generator bypassed organization scoping.
* **Why it caused incorrect behavior:** Leaked cross-organization bookings.
* **How it was fixed:** Checked room ownership in the router (returning 404 if invalid) and scoped exports to the admin's organization.

---

## 25. Timezone normalization conversion error
* **File & Lines:** `app/timeutils.py`
* **The Bug:** timezone offsets were stripped directly using `.replace(tzinfo=None)` without converting.
* **Why it caused incorrect behavior:** Did not convert inputs to UTC correctly.
- **How it was fixed:** Corrected to use `.astimezone(timezone.utc).replace(tzinfo=None)`.

---

## 26. SQLite Concurrency Locking (Race Conditions)
* **File & Lines:** `app/database.py`
* **The Bug:** Defaulted to `DEFERRED` transaction mode.
* **Why it caused incorrect behavior:** Caused concurrency overlaps and SQLite locking errors.
* **How it was fixed:** Enabled WAL mode and set database connection to start with `BEGIN IMMEDIATE` transactions.
