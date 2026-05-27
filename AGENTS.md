<!-- diffsentinel:start -->
## DiffSentinel Guardrail

After making code changes, run:

```powershell
diffsentinel guard --changed --json --fail-on-critical
```

If the command reports `CRITICAL` issues, fix safe items first or explain why manual review is required. Use:

```powershell
diffsentinel fix-plan --changed
```

For full-project audits, run:

```powershell
diffsentinel guard --project --json --fail-on-critical
```
<!-- diffsentinel:end -->
