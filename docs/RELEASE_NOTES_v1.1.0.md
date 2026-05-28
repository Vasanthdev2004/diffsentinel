# DiffSentinel v1.1.0 Release Notes

## Highlights

- Added natural-language replies inside the `dfs` shell.
- Plain text input now acts like project-aware chat.
- Chat uses last guard/scan report, last apply run, and session messages.
- Added local fallback replies when no OpenAI API key is set.
- Added optional OpenAI-backed shell replies when `OPENAI_API_KEY` is available.
- Improved shell welcome panel with model/mode and suggested actions.

## Try It

```powershell
dfs
```

Then type:

```text
/guard
can I commit?
what is the main risk?
/apply --dry-run
```
