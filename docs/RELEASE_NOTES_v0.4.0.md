# DiffSentinel v0.4.0 Release Notes

## Highlights

- Added `diffsentinel init` onboarding.
- Added `.diffsentinel.toml` project configuration.
- Added `.env.example` generation without storing real API keys.
- Added `.gitignore` safety entries for `.env` and DiffSentinel backups.
- Added `AGENTS.md` setup so coding agents know to run DiffSentinel after edits.
- Added `diffsentinel doctor` diagnostics with optional JSON output.
- Wired config defaults into `check` and `scan`.

## New Commands

```powershell
diffsentinel init
diffsentinel doctor
diffsentinel doctor --json
diffsentinel doctor --live
```

## Recommended Agent Guardrail

Add this to coding-agent workflows:

```powershell
diffsentinel scan . --json --exit-on-critical
```
