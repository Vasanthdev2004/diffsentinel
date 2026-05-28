# DiffSentinel v1.2.0 Release Notes

## Highlights

- Added `dfs github-review <PR_NUMBER>`.
- Dry-run mode generates a PR review decision and markdown body.
- `--act` posts through GitHub CLI.
- Clean PRs are approved.
- Critical PRs request changes.
- Warning/manual-review PRs receive comments unless strict mode requests changes.
- Every review body includes the watermark: `Reviewed by DiffSentinel`.
- Shell chat can trigger PR review previews with prompts like `review pr 12`.

## Commands

```powershell
dfs github-review 12
dfs github-review 12 --act
dfs github-review 12 --act --strict
dfs github-review 12 --comment-only --act
```
