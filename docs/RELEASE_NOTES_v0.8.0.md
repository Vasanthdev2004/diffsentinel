# DiffSentinel v0.8.0 Release Notes

## Highlights

- Added `dfs` as a short command alias for `diffsentinel`.
- Added `apply-safe --dry-run`.
- Added `agent --dry-run`.
- Added SARIF output with `guard --sarif` and `fix-plan --sarif`.
- Added configurable ignored paths in `.diffsentinel.toml`.
- Added configurable local rule toggles.
- Added GitHub Actions code scanning example.
- Added README "Safe By Default" trust section.

## Useful Commands

```powershell
diffsentinel apply-safe --changed --dry-run
diffsentinel agent --yes --dry-run
diffsentinel guard --project --sarif --fail-on-critical
dfs demo-agent
```
