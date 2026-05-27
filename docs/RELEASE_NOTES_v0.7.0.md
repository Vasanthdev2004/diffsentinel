# DiffSentinel v0.7.0 Release Notes

## Highlights

- Added `diffsentinel agent`.
- The agent command runs an inspect -> plan -> apply -> verify loop.
- It asks before applying safe fixes by default.
- `--yes` applies safe fixes without prompting for demos.
- `--json` emits pure machine-readable JSON.

## Run It

```powershell
diffsentinel agent
diffsentinel agent --yes
diffsentinel agent --yes --json
```

## Why It Matters

This gives DiffSentinel more of a coding-agent companion feel while keeping the product focused on performance and latency guardrails.
