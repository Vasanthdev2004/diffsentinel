# DiffSentinel v0.5.0 Release Notes

## Highlights

- Added `diffsentinel guard` as the main agent-facing command.
- Added Agent JSON v2 with `summary`, `safe_fixes`, `manual_review`, `blocked_reason`, `next_action`, and `exit_policy`.
- Added `diffsentinel fix-plan`.
- Added `diffsentinel apply-safe`.
- Added `diffsentinel restore`.
- Added reversible run metadata under `.diffsentinel/runs/`.
- Updated `AGENTS.md` onboarding instructions for coding-agent guardrail workflows.

## Recommended Agent Command

```powershell
diffsentinel guard --changed --json --fail-on-critical
```

## Safe Apply Flow

```powershell
diffsentinel fix-plan --changed
diffsentinel apply-safe --changed
diffsentinel restore
```
