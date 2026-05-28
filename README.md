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
- Whole-project Python scanning with `diffsentinel scan`
- Agent Guard Mode with `diffsentinel guard`
- Interactive agent loop with `diffsentinel agent`
- Interactive `dfs` shell with slash commands
- Autopilot and PR review report commands
- OpenAI Structured Outputs when `OPENAI_API_KEY` is set
- Offline local rules engine when no API key is available
- Rich terminal UI with severity colors and safe apply
- Agent-friendly `--json` output for scripts and coding agents
- `fix-plan`, `apply-safe`, and `restore` for reversible safe fixes
- `--apply-first` for deterministic demos
- `--exit-on-critical` for CI-style checks
- `install-hook` to block critical staged regressions before commit
- `demo-agent` for a full coding-agent guardrail story
- SARIF output for GitHub code scanning
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

The CLI installs both commands:

```powershell
diffsentinel --help
dfs --help
```

Use `dfs` for faster demos.

Run `dfs` with no subcommand to open the interactive shell:

```powershell
dfs
```

Inside the shell:

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
/exit
```

## First Run Onboarding

Initialize a project with DiffSentinel config, safe environment examples, and coding-agent instructions:

```powershell
diffsentinel init
diffsentinel doctor
```

`diffsentinel init` creates:

- `.diffsentinel.toml` for model and scan defaults
- `.env.example` with placeholder environment variables
- `.gitignore` entries for `.env` and backups
- `AGENTS.md` instructions so CLI coding agents know to run DiffSentinel after edits

DiffSentinel does **not** store your real API key in project files.

Optional live OpenAI analysis:

```powershell
$env:OPENAI_API_KEY = "<your-openai-api-key>"
diffsentinel scan . --live --model gpt-5.5 --json
```

The default live model is `gpt-5.5`, with `--reasoning-effort low` for fast audits. You can override this per command or with:

```powershell
$env:DIFFSENTINEL_MODEL = "gpt-5.5"
$env:DIFFSENTINEL_REASONING_EFFORT = "medium"
```

Without `OPENAI_API_KEY`, DiffSentinel still works through the local rules engine.

## Demo From Scratch

Fastest path:

```powershell
diffsentinel demo
```

That command creates a temporary git repo, introduces the async blocking bug, detects it, applies the safe fix, and prints the before/after code.

For the full agent story:

```powershell
diffsentinel demo-agent
```

That command simulates a coding agent introducing a latency regression, runs Agent Guard Mode, applies a safe fix with rollback metadata, reruns guard to prove the code is clean, and demonstrates restore.

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
dfs
dfs agent --yes
dfs demo-agent
dfs autopilot --apply-safe --markdown
dfs review-pr --markdown
diffsentinel init
diffsentinel doctor
diffsentinel scan .
diffsentinel agent --yes
diffsentinel guard --changed --json --fail-on-critical
diffsentinel guard --project --sarif --fail-on-critical
diffsentinel fix-plan --changed
diffsentinel apply-safe --changed
diffsentinel apply-safe --changed --dry-run
diffsentinel restore
diffsentinel demo-agent
diffsentinel check --json
diffsentinel scan . --json --exit-on-critical
diffsentinel scan . --live --model gpt-5.5 --reasoning-effort low --json
diffsentinel check --no-tui
diffsentinel check --apply-first
diffsentinel check --exit-on-critical
diffsentinel check --staged --exit-on-critical
diffsentinel install-hook
diffsentinel uninstall-hook
```

The installed pre-commit hook runs:

```powershell
diffsentinel check --staged --exit-on-critical --no-tui --force-cache
```

Use `diffsentinel install-hook --live` if you want the hook to use live OpenAI analysis when `OPENAI_API_KEY` is available.

## Real Project And Agent Usage

Run against any Python project, even when there is no git diff:

```powershell
cd path\to\your\project
diffsentinel scan .
```

Coding agents and CI can consume a stable JSON contract:

```powershell
diffsentinel guard --changed --json --fail-on-critical
```

The v2 JSON payload includes `summary`, `issues`, `safe_fixes`, `manual_review`, `blocked_reason`, `next_action`, and `exit_policy`. This lets CLI coding agents call DiffSentinel after they modify code and decide whether to patch, ask the user, or stop.

To apply only high-confidence safe fixes:

```powershell
diffsentinel apply-safe --changed
diffsentinel restore
```

`apply-safe` writes run metadata to `.diffsentinel/runs/`, and `restore` rolls back the latest safe-apply run.

For higher-accuracy live audits:

```powershell
diffsentinel scan . --live --model gpt-5.5 --reasoning-effort medium --json
```

For coding-agent workflows, keep this command in your agent instructions:

```powershell
diffsentinel guard --changed --json --fail-on-critical
```

For Claude Code/Codex-style interactive usage:

```powershell
diffsentinel agent
```

It inspects changed code, prints a fix plan, asks before applying safe fixes, reruns guard, and gives a final recommendation. Use `--yes` for non-interactive demo runs and `--json` for machine-readable output.

For autonomous PR-style review:

```powershell
dfs autopilot --apply-safe --markdown
dfs review-pr --markdown
```

These commands inspect changed code, optionally apply safe fixes, rerun guard, and write a markdown report under `.diffsentinel/reports/`.

## Safe By Default

- `diffsentinel apply-safe --dry-run` previews changes without writing files.
- Only high-confidence single-line fixes are auto-applied.
- Manual-review findings are never mutated.
- Safe apply writes rollback metadata under `.diffsentinel/runs/`.
- `diffsentinel restore` restores the latest safe-apply run.
- `.diffsentinel.toml` supports ignored paths and rule toggles.
- `--sarif` output works with GitHub code scanning.

Copy the GitHub Actions example from:

```text
examples/github-action/diffsentinel.yml
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
