# DiffSentinel v0.9.0 Release Notes

## Highlights

- Added interactive `dfs` shell.
- Running `dfs` with no arguments now opens a terminal agent shell.
- Added ASCII logo and slash commands.
- Added session memory for last report, last findings, and last apply run.
- Kept `diffsentinel` no-argument behavior unchanged for compatibility.

## Slash Commands

```text
/help
/status
/guard
/scan
/plan
/apply --dry-run
/apply
/restore
/doctor
/json
/sarif
/clear
/exit
```

## Run It

```powershell
dfs
```
