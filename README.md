# DiffSentinel

Terminal-native performance regression guard for your current diff, with one-keystroke fixes.

DiffSentinel is a shipping-first hackathon MVP. It reads `git diff`, sends changed code to OpenAI with a strict Pydantic schema when `OPENAI_API_KEY` is available, falls back to a local demo cache when the API is unavailable, shows performance issues in a terminal UI, and lets you press `A` to apply the suggested fix.

## Scope

Built:

- `diffsentinel check`
- Python diff snippets from `git diff`
- OpenAI Structured Outputs through the Python SDK
- Pydantic validation
- Offline cache for the demo samples
- Rich terminal UI with `A` apply, arrow navigation, and `Q` quit
- Backup + atomic file rewrite

Cut for the hackathon:

- File watcher
- Pre-commit hook
- Multi-agent orchestration
- Rust rewrite
- Tree-sitter
- IDE plugins
- Team dashboards

## Install

```powershell
cd "D:\codings\GPT Hackathon\diffsentinel"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Optional live OpenAI analysis:

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

Without `OPENAI_API_KEY`, the primary demo still works through the cache.

## Demo

Use a git repo so `git diff` has a baseline:

```powershell
git init demo-repo
Copy-Item samples\async_blocking.py demo-repo\async_blocking.py
cd demo-repo
git add async_blocking.py
git -c user.name=Demo -c user.email=demo@example.com commit -m "baseline"
```

Now edit `async_blocking.py` so it contains:

```python
import asyncio
import time

async def handle_request():
    time.sleep(1)
    return {"status": "ok"}
```

Run:

```powershell
diffsentinel check --force-cache
```

The TUI shows `CRITICAL - Blocking I/O in async context`. Press `A` to rewrite the line to:

```python
    await asyncio.sleep(1)
```

DiffSentinel creates `async_blocking.py.diffsentinel.bak` before writing.

## JSON Mode For Tests

```powershell
diffsentinel check --force-cache --json
```

## Run Tests

```powershell
pytest
```
