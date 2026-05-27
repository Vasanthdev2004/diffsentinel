# DiffSentinel v0.6.0 Release Notes

## Highlights

- Added `diffsentinel demo-agent`.
- The demo simulates a coding agent introducing a latency regression.
- It runs Agent Guard Mode, shows Agent JSON v2 summary, applies safe fixes, reruns guard, and demonstrates restore.
- This gives DiffSentinel a one-command product story for checkpoint videos and final launch demos.

## Run It

```powershell
diffsentinel demo-agent
```

## Demo Story

1. Agent changes code and introduces `time.sleep(1)` inside `async def`.
2. DiffSentinel guard finds a `CRITICAL` latency issue.
3. DiffSentinel applies the safe fix.
4. Guard reruns and reports `continue`.
5. Restore proves the safe-apply path is reversible.
