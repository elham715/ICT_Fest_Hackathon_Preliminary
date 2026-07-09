# Collaboration Guide

This repository is for the IUT 12th ICT Fest preliminary challenge: fixing the CoWork multi-tenant booking API.

The grader is black-box. It will call the API and compare behavior against the contract in `README.md`. Collaborators must preserve the public API exactly.

## Ground Rules

- Do not change endpoint paths.
- Do not rename request or response fields.
- Do not change documented status codes or error codes.
- Do not rewrite unrelated code.
- Do not introduce new external services.
- Keep fixes small, testable, and tied to one business rule.
- Add or update tests for each confirmed bug.
- Keep `bug report.md` updated as bugs are found and fixed.

## Recommended Workflow

1. Read `README.md` and the relevant file under `Bug_fix/`.
2. Reproduce the suspected bug with a test or API request.
3. Make the smallest code change that fixes the behavior.
4. Run `pytest -q`.
5. Record the bug, location, fix, and verification in `bug report.md`.
6. Commit only the related files.

For implementation work, read the lane's `guide.md`, `issues.md`, and `fix_script.md` before editing code.

## Collaboration Channels

Use the `Bug_fix/` files as work lanes. Each AI agent or human collaborator should claim one lane at a time:

- `Bug_fix/01_datetime/`
- `Bug_fix/02_auth/`
- `Bug_fix/03_multi_tenancy/`
- `Bug_fix/04_booking_creation/`
- `Bug_fix/05_rate_limit_and_concurrency/`
- `Bug_fix/06_cancellation_refunds/`
- `Bug_fix/07_reports_and_pagination/`
- `Bug_fix/08_reference_codes_and_liveness/`

## Handoff Format

When handing off work, leave a short note with:

- Files inspected
- Bugs confirmed
- Fixes applied
- Tests added or run
- Remaining risks

## Definition Of Done

A fix is done when:

- The failing behavior is reproduced.
- The API response matches the contract.
- Existing tests pass.
- New focused tests cover the fixed behavior.
- `bug report.md` contains the finding if it may matter for tie-breaking.
