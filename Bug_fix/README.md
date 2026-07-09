# Bug Fix Work Lanes

This folder breaks the challenge into focused lanes so multiple collaborators or AI agents can work without stepping on each other.

Each lane starts with bug-finding instructions. Follow the contract in the root `README.md` as the source of truth.

## Suggested Order

1. `01_datetime/guide.md`
2. `02_auth/guide.md`
3. `03_multi_tenancy/guide.md`
4. `04_booking_creation/guide.md`
5. `05_rate_limit_and_concurrency/guide.md`
6. `06_cancellation_refunds/guide.md`
7. `07_reports_and_pagination/guide.md`
8. `08_reference_codes_and_liveness/guide.md`

## General Bug-Finding Loop

1. Read the lane file.
2. Inspect the named modules.
3. Write or run a focused test that should pass by contract.
4. Confirm the current behavior is wrong.
5. Patch the smallest amount of code.
6. Run `pytest -q`.
7. Update `bug report.md`.

## Folder Shape

Each lane folder should contain:

- `guide.md` - instructions for finding that class of bugs.
- `issues.md` - findings from code inspection and AI agent review.
- `fix_script.md` - implementation sequence for fixing that lane safely.

## Shared Planning Files

- `FIX_PLAN.md` - recommended global fix order.
- `SANITY_CHECK.md` - current confidence level and competition-readiness notes.
