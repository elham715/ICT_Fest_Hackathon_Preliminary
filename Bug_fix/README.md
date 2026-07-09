# Bug Fix Work Lanes

This folder breaks the challenge into focused lanes so multiple collaborators or AI agents can work without stepping on each other.

Each lane starts with bug-finding instructions. Follow the contract in the root `README.md` as the source of truth.

## Suggested Order

1. `01_datetime.md`
2. `02_auth.md`
3. `03_multi_tenancy.md`
4. `04_booking_creation.md`
5. `05_rate_limit_and_concurrency.md`
6. `06_cancellation_refunds.md`
7. `07_reports_and_pagination.md`
8. `08_reference_codes_and_liveness.md`

## General Bug-Finding Loop

1. Read the lane file.
2. Inspect the named modules.
3. Write or run a focused test that should pass by contract.
4. Confirm the current behavior is wrong.
5. Patch the smallest amount of code.
6. Run `pytest -q`.
7. Update `bug report.md`.

