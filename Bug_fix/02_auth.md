# Auth Bugs

## Start Here

Find bugs by tracing token creation, validation, refresh rotation, logout invalidation, and role checks. Auth bugs can make later tenant and booking tests misleading.

## Contract Rules

- JWT algorithm is HS256.
- Access token claims include `sub`, `org`, `role`, `jti`, `iat`, `exp`, and `type`.
- Refresh token claims include the same required fields.
- Access tokens expire in exactly 900 seconds.
- Refresh tokens expire in 7 days.
- Logout immediately invalidates the presented access token.
- Refresh tokens are single-use.
- Reusing an invalid refresh token returns `401`.
- Bad login credentials return `401 INVALID_CREDENTIALS`.

## Files To Inspect

- `app/auth.py`
- `app/routers/auth.py`
- `app/models.py`
- `app/schemas.py`
- `app/errors.py`

## Tests To Add Or Run

- Decode access and refresh tokens and verify required claims.
- Assert `exp - iat == 900` for access tokens.
- Assert refresh token lifetime is 7 days.
- Logout then reuse access token and expect `401`.
- Refresh once succeeds and returns a new refresh token.
- Refresh token reuse returns `401`.
- Bad password returns `401 INVALID_CREDENTIALS`.

## Common Failure Signs

- Missing or non-unique `jti`.
- `sub` stored as an integer instead of a string.
- Logout only returns success but does not blacklist the token.
- Refresh returns a new access token but reuses the old refresh token.

