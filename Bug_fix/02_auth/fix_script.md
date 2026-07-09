# Fix Script: Auth

## Goal

Make JWT auth, logout, refresh rotation, and registration match the README contract.

## Files To Edit

- `app/auth.py`
- `app/routers/auth.py`

## Steps

1. Fix access token expiry.
   - Ensure `exp - iat == 900` seconds exactly.

2. Fix access-token revocation.
   - Store revoked access-token `jti` values.
   - Validate access tokens by checking `payload["jti"]`, not `sub`.

3. Add refresh-token single-use behavior.
   - Track used/revoked refresh-token `jti` values.
   - Reject reused refresh tokens with `401`.
   - On successful refresh, revoke the presented refresh token and return new access and refresh tokens.

4. Fix duplicate registration.
   - If username already exists in the same org, raise `409 USERNAME_TAKEN`.
   - Keep new-org first user as `admin`; existing-org new user as `member`.

5. Harden malformed signed tokens.
   - Missing or non-integer `sub` should return `401`, not `500`.

6. Handle database uniqueness conflict in registration.
   - Catch SQLAlchemy `IntegrityError` during register commits and raise `409 USERNAME_TAKEN`.

## Required Tests

- Access token lifetime is exactly 900 seconds.
- Logout invalidates the presented access token.
- Refresh token reuse returns `401`.
- Newly returned refresh token works.
- Duplicate username in same org returns `409 USERNAME_TAKEN`.
- Malformed signed token subject returns `401`.
- Concurrent registration of the same username returns `409 USERNAME_TAKEN` for the losing request.

## Acceptance

- Login and refresh response shapes remain unchanged.
- All token failures return `401`.

