# Build In Public Drafts

## LinkedIn Post 1

Building in public for the OpenAI x Outskill AI Builders Hackathon.

Our project is DiffSentinel: a terminal-native performance regression guard for your current `git diff`.

The idea is simple: before code reaches PR review or CI, catch obvious performance traps locally:

- blocking calls inside `async` functions
- missing awaits
- object copies inside loops
- inefficient collection usage

Current progress:

- CLI works
- public GitHub repo is live
- local rules fallback works offline
- safe one-command fix flow works
- CI is passing on Python 3.11 and 3.12

Next up: record the demo, polish the terminal UI, and make the README more visual.

Repo: https://github.com/Vasanthdev2004/diffsentinel

## LinkedIn Post 2

Small hackathon lesson: narrowing the scope made the product stronger.

Instead of building a broad AI code reviewer, we focused DiffSentinel on one painful workflow:

"I just changed code locally. Did I accidentally introduce a performance bug?"

That gave us a clear MVP:

- read `git diff`
- analyze only changed code
- flag performance problems
- show impact in the terminal
- safely apply simple fixes

The current demo catches `time.sleep(1)` inside an async Python function and rewrites it to `await asyncio.sleep(1)`.

It is not trying to be a profiler. It is a fast first-pass guardrail before commit.

## Twitter/X Post

Building DiffSentinel for the OpenAI x Outskill hackathon.

A terminal-native guard for your current `git diff`:

- catches async/performance traps
- works locally/offline
- shows focused terminal output
- can safely apply simple fixes

Repo: https://github.com/Vasanthdev2004/diffsentinel

Next: demo video + README visuals.

## LinkedIn Post 3

Day 2 update for the #OpenAIHackathon:

Today we made DiffSentinel much easier to try.

New command:

```powershell
diffsentinel demo
```

It creates a temporary git repo, introduces a Python async performance bug, detects it, applies the safe fix, and prints the before/after code.

This matters because the product can now be understood in one command:

`time.sleep(1)` inside `async def` becomes `await asyncio.sleep(1)`.

Current status:

- core CLI working
- local/offline analysis working
- safe apply working
- self-contained demo working
- pre-commit hook install working
- project-wide scan working
- agent-friendly JSON output working
- onboarding and doctor commands working
- tests passing: 25
- public repo live

Repo: https://github.com/Vasanthdev2004/diffsentinel

#OpenAIHackathon

## Short Product Description

DiffSentinel is a terminal-native performance regression guard for your current git diff. It catches high-confidence async and hot-path mistakes before code review, shows them in a focused terminal UI, and can safely apply simple fixes with a backup.

## 30-Second Pitch

Developers move fast, and tiny performance bugs often slip into local changes: a blocking call inside an async handler, a missing await, or a copy inside a hot loop. DiffSentinel runs directly in the terminal against the current git diff, flags high-confidence performance issues, explains the impact, and can safely apply simple fixes. It is local-first, performance-only, and designed to catch problems before PR review or CI.
