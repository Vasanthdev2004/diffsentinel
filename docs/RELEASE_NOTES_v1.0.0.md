# DiffSentinel v1.0.0 Release Notes

## Highlights

- Added `dfs autopilot`.
- Added `dfs review-pr`.
- Autopilot runs inspect -> plan -> optional safe apply -> verify -> report.
- PR review mode writes markdown reports under `.diffsentinel/reports/`.
- Supports JSON, SARIF, markdown, fail-on-critical, and safe-apply workflows.

## Commands

```powershell
dfs autopilot --apply-safe --markdown
dfs autopilot --json --fail-on-critical
dfs review-pr --markdown
```

## Product Story

DiffSentinel can now act as an autonomous performance-review agent for AI-generated code changes.
