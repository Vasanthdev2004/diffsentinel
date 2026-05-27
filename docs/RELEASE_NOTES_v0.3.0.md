# DiffSentinel v0.3.0 Release Notes

## Highlights

- Upgraded live OpenAI analysis default to `gpt-5.5`.
- Added Responses API structured parsing path before Chat Completions fallback.
- Added `--reasoning-effort` for live audits.
- Added project-wide `diffsentinel scan` in the previous build cycle.
- Added agent-friendly JSON output for CLI coding agents and CI.
- Added pre-commit hook protection.
- Redesigned the terminal dashboard.

## Recommended Live Commands

```powershell
diffsentinel scan . --live --model gpt-5.5 --reasoning-effort low --json
diffsentinel check --model gpt-5.5 --reasoning-effort low
```

Note: `check` uses live mode automatically when `OPENAI_API_KEY` is set unless `--force-cache` is passed. `scan` stays local by default and uses live analysis only with `--live`.

## Offline Safety

DiffSentinel still works without an API key through the local rules engine:

```powershell
diffsentinel scan .
diffsentinel check --force-cache
```
