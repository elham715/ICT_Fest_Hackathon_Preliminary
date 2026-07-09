# Auth Issues

## 1. Access Token Expiry Is 15 Hours

**Files/lines:**

- `app/auth.py:50`

**Expected:** Access token `exp - iat == 900` seconds.

**Likely bug:** `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 60)` turns `15` minutes into `900` minutes.

**Suggested tests:**

- Login, decode access token, and assert `exp - iat == 900`.

## 2. Logout Blacklist Stores `jti` But Validation Checks `sub`

**Files/lines:**

- `app/auth.py:85`
- `app/auth.py:97`

**Expected:** Logout immediately invalidates the presented access token.

**Likely bug:** `revoke_access_token()` stores `payload["jti"]`, but validation checks `payload.get("sub") in _revoked_tokens`.

**Suggested tests:**

- Login, call `/auth/logout`, then reuse the access token on a protected endpoint and expect `401`.

## 3. Refresh Tokens Are Not Single-Use

**Files/lines:**

- `app/routers/auth.py:81`
- `app/routers/auth.py:89`

**Expected:** Refreshing rotates tokens and invalidates the presented refresh token; reuse returns `401`.

**Likely bug:** Refresh endpoint verifies token type and user, then issues new tokens without revoking the old refresh token `jti`.

**Suggested tests:**

- Login and refresh once successfully.
- Refresh again with the original refresh token and expect `401`.
- Refresh with the newly returned refresh token and expect success.

## No Issue Found

- Required JWT claims appear present for both token types.
- Refresh expiry appears to be 7 days.
- Bad credentials appear to return `401 INVALID_CREDENTIALS`.

