<!-- diffsentinel:start -->
## DiffSentinel Guardrail

After making code changes, run:

```powershell
diffsentinel scan . --json --exit-on-critical
```

If the command reports `CRITICAL` issues, fix safe items first or explain why manual review is required. Use:

```powershell
diffsentinel check --json --exit-on-critical
```

when only the current git diff should be audited.
<!-- diffsentinel:end -->
