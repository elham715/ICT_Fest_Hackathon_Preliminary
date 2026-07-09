# Gemini Antigravity Bug-Finding Prompt

Use this prompt with Gemini Antigravity or another AI coding agent to independently audit the CoWork API. The goal is bug discovery and validation, not broad refactoring.

```text
You are auditing a FastAPI bug-fix challenge repository named CoWork.

Repository path:
/Users/admin/Desktop/Hackathon/cowork-preliminary

Challenge type:
Black-box API grading. The grader will call HTTP endpoints and assert behavior against README.md. Preserve endpoint paths, status codes, error codes, and JSON field names exactly.

Primary contract source:
Read README.md first. Treat it as the source of truth.

Supporting files:
- COLLABORATION.md
- Bug_fix/README.md
- Bug_fix/FIX_PLAN.md
- Bug_fix/*/guide.md
- Bug_fix/*/issues.md

Your task:
Perform an independent bug-finding pass. Do not edit code unless explicitly asked later. For each suspected bug, decide whether it is a true contract violation, a concurrency/liveness risk, or a lower-priority concern.

Output format:
For each valid bug, provide:
- Lane folder
- Severity: Hard, Medium, or Low
- File/line references
- Contract rule violated
- Current behavior
- Minimal fix idea
- Suggested test case

Do not report:
- Style-only issues
- Refactors that do not affect the contract
- Security improvements not required by README.md
- `+00:00` datetime output as a bug, because README.md allows `Z` or `+00:00`
- Generic validation concerns unless the README contract requires them

High-priority areas:
1. Datetime parsing, UTC conversion, booking window validation
2. JWT access/refresh/logout behavior
3. Duplicate registration
4. Cross-org and same-org member visibility
5. Booking overlap, quota, and rate limit
6. Cancellation refund percentages, rounding, duplicate refund logs
7. Pagination, availability, stats, usage report, export
8. Reference-code uniqueness and liveness under concurrency

Important constraints:
- Keep API contract exactly the same.
- Hidden tests likely probe edge cases and concurrency.
- Do not propose replacing the stack or adding external services.
- Prefer minimal patches over architecture rewrites.
- If a fix affects multiple lanes, name the shared module and dependencies.

Final answer:
Give a concise ranked bug inventory and a recommended fix order. Mark any uncertain item clearly as "risk, not confirmed."
```

