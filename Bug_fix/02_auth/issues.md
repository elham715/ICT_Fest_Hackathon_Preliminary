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

## 4. Duplicate Registration Returns Existing User

**Rating:** Hard, valid.

**Files/lines:**

- `app/routers/auth.py:32`
- `app/routers/auth.py:37`

**Expected:** A duplicate username within the same organization returns `409 USERNAME_TAKEN`.

**Likely bug:** The register endpoint returns the existing user's data instead of raising the documented application error.

**Reason this is valid:** The contract explicitly names duplicate same-org username as `409 USERNAME_TAKEN`; returning `201` with an existing user violates both status code and behavior.

**Suggested tests:**

- Register `alice` in org `acme`.
- Register `alice` again in org `acme` and expect `409 USERNAME_TAKEN`.
- Register `alice` in a different org and verify that separate-org username behavior is still allowed.

## 5. Malformed Token Subject Can Become A 500

**Rating:** Medium to hard, valid.

**Files/lines:**

- `app/auth.py:106`
- `app/routers/auth.py:86`

**Expected:** Missing, invalid, expired, or malformed tokens return `401`.

**Likely bug:** `int(payload["sub"])` can raise `KeyError` or `ValueError` for a signed token with missing/non-numeric `sub`, escaping as a server error instead of `401`.

**Reason this is valid:** The grader may generate malformed-but-signed JWTs. The contract requires token failures to be unauthorized responses, not unhandled exceptions.

**Suggested tests:**

- Create a signed access token with `sub = "not-an-int"` and expect protected endpoints to return `401`.
- Create a signed refresh token with missing `sub` and expect `/auth/refresh` to return `401`.

## 6. Concurrent Registration Can Raise a 500 Server Error

**Rating:** Hard, valid.

**Files/lines:**

- `app/routers/auth.py:51-53`
- `app/models.py:26`

**Expected:** Concurrent registration requests for the same username within the same organization return `409 USERNAME_TAKEN`.

**Likely bug:** The endpoint checks for existing user first and then creates the user. Under concurrent requests, both may pass the check, and one will trigger a database `IntegrityError` on the `uq_user_org_username` unique constraint, causing a 500 error instead of a 409.

**Suggested tests:**

- Send two duplicate registration requests in parallel.
- Assert one returns `201` (or `200` if previously registered) and the other returns `409 USERNAME_TAKEN`.

## No Issue Found

- Required JWT claims appear present for both token types.
- Refresh expiry appears to be 7 days.
- Bad credentials appear to return `401 INVALID_CREDENTIALS`.

## Rating Notes

- Puku's `+00:00` concern does not apply here and is acceptable where used for datetime output.
- The logout revocation issue is valid, but the practical bug is that logout does not revoke the access token because validation checks `sub` while storage uses `jti`.
