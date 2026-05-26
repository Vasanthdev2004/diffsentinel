# DiffSentinel

[![CI](https://github.com/Vasanthdev2004/diffsentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/Vasanthdev2004/diffsentinel/actions/workflows/ci.yml)

Terminal-native performance regression guard for your current diff, with safe one-command fixes.

DiffSentinel catches obvious performance traps while the code is still local: blocking calls inside `async` functions, missing awaits, suspicious allocation inside loops, and inefficient collection use. It is intentionally narrow. Broad AI code reviewers already exist; DiffSentinel is for the fast moment before you commit, when one bad line can slip through.

## Why It Exists

Most AI review tools live around pull requests. DiffSentinel lives in the terminal and reads your current `git diff`.

The hackathon demo is simple:

```python
async def handle_request():
    time.sleep(1)
```

Run:

```powershell
diffsentinel check --force-cache
```

DiffSentinel flags the line as `CRITICAL` and offers:

```python
    await asyncio.sleep(1)
```

Press `A` in the TUI, or run:

```powershell
diffsentinel check --force-cache --apply-first
```

The original file is backed up as `<file>.diffsentinel.bak` before the fix is written.

## Features

- Local `git diff` analysis
- OpenAI Structured Outputs when `OPENAI_API_KEY` is set
- Offline local rules engine when no API key is available
- Rich terminal UI with severity colors and safe apply
- `--json` output for scripts
- `--apply-first` for deterministic demos
- `--exit-on-critical` for CI-style checks
- Backup + atomic file rewrite
- Focused test suite and GitHub Actions CI

## Install

```powershell
git clone https://github.com/Vasanthdev2004/diffsentinel.git
cd diffsentinel
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Optional live OpenAI analysis:

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

Without `OPENAI_API_KEY`, DiffSentinel still works through the local rules engine.

## Demo From Scratch

Create a tiny repo with a clean baseline:

```powershell
mkdir demo-repo
Copy-Item samples\async_blocking.py demo-repo\async_blocking.py
cd demo-repo
git init
git add async_blocking.py
git -c user.name=Demo -c user.email=demo@example.com commit -m "baseline"
```

Change `async_blocking.py` so the function contains the blocking line:

```python
async def handle_request():
    time.sleep(1)
    return {"status": "ok"}
```

Run the interactive demo:

```powershell
diffsentinel check --force-cache
```

Or run the non-interactive demo:

```powershell
diffsentinel check --force-cache --apply-first
```

## Useful Commands

```powershell
diffsentinel check
diffsentinel check --json
diffsentinel check --no-tui
diffsentinel check --apply-first
diffsentinel check --exit-on-critical
diffsentinel check --staged --exit-on-critical
```

## What It Detects Today

- `time.sleep(...)` inside `async def`
- synchronous `requests.*(...)` inside `async def`
- `subprocess.run(...)` inside `async def`
- likely missing `await` on `asyncio.*(...)`
- `.copy()` / `.clone()` inside loops as allocation warnings
- repeated list-style membership checks inside loops as collection warnings

High-confidence single-line fixes are auto-applyable. Lower-confidence warnings are shown as manual-review suggestions.

## Honest Limits

DiffSentinel is a fast first-pass auditor, not a profiler and not a proof system. It works best on small local diffs with enough surrounding context. The current hackathon build is Python-focused; broader language support belongs on the roadmap, not in the first demo.

## Tests

```powershell
python -m pytest -q
```
