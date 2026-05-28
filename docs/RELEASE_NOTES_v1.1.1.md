# DiffSentinel v1.1.1 Release Notes

## Fixes

- `dfs` now auto-selects a real child project when launched from a parent workspace.
- `/guard` now gives a helpful message when no git repository is available.
- Shell logo is ASCII-safe for Windows/captured terminals.
- Prevents parent-folder scans from accidentally including stale demo repositories when a single real project folder is present.
