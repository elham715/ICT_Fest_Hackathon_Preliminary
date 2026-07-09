# Fixed Bugs - Auth

The following bugs from `issues.md` have been fixed:

1. **Access Token Expiry Is 15 Hours**
   - **Resolution**: Updated `create_access_token` in `app/auth.py` to use `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)` instead of `* 60` minutes.
2. **Logout Blacklist Stores `jti` But Validation Checks `sub`**
   - **Resolution**: Updated `get_token_payload` in `app/auth.py` to correctly check if `payload["jti"]` is in `_revoked_tokens` instead of `payload.get("sub")`.
3. **Refresh Tokens Are Not Single-Use**
   - **Resolution**: Added a thread-safe `_revoked_refresh_tokens` registry and helpers. In `/auth/refresh`, the presented token's `jti` is verified and immediately blacklisted.
4. **Duplicate Registration Returns Existing User**
   - **Resolution**: Updated `register` endpoint in `app/routers/auth.py` to raise `AppError(409, "USERNAME_TAKEN", ...)` if the username already exists in the organization.
5. **Malformed Token Subject Can Become A 500**
   - **Resolution**: Protected user queries in `get_current_user` and `/refresh` from `ValueError`/`KeyError` when parsing token subjects, raising a clean `401` if malformed.
6. **Concurrent Registration Can Raise a 500 Server Error**
   - **Resolution**: Caught database `IntegrityError` during register commits and raised `409 USERNAME_TAKEN`.
7. **Tokens Without `jti` Can Bypass Revocation Rules**
   - **Resolution**: Required access and refresh tokens to include a `jti` claim before protected-route access or refresh rotation. Refresh tokens are now consumed atomically so two simultaneous refresh attempts cannot both pass the single-use check.
