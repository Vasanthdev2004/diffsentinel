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
- Agent Guard Mode working
- reversible safe apply and restore working
- one-command `demo-agent` story working
- interactive `diffsentinel agent` loop working
- dry-run safe apply previews
- SARIF output for GitHub code scanning
- config ignores and rule toggles
- interactive `dfs` shell with slash commands
- autonomous `dfs autopilot` and `dfs review-pr`
- natural-language chat inside the `dfs` shell
- GitHub PR review action mode with DiffSentinel watermark
- project memory via `/analyse`
- tests passing: 45
- public repo live

Repo: https://github.com/Vasanthdev2004/diffsentinel

#OpenAIHackathon

## LinkedIn Post 9

DiffSentinel now takes GitHub PR review actions.

```powershell
dfs github-review 12
dfs github-review 12 --act
```

Dry-run mode previews the decision. With `--act`, DiffSentinel uses GitHub CLI to approve, request changes, or comment based on performance-risk findings.

Every review body includes:

Reviewed by DiffSentinel

This makes the product feel like an actual PR-review agent, not just a local checker.

#OpenAIHackathon

## LinkedIn Post 8

DiffSentinel shell now accepts natural language.

You can run:

```powershell
dfs
```

Then type:

```text
can I commit?
what is the main risk?
what should I fix next?
```

It answers using the current session state: last guard report, findings, safe fixes, and apply history. Slash commands still work for actions like `/guard`, `/plan`, `/apply --dry-run`, `/apply`, and `/restore`.

The goal is a focused terminal agent for performance safety, not a generic chatbot.

#OpenAIHackathon

## LinkedIn Post 7

DiffSentinel now has autonomous PR-review style behavior:

```powershell
dfs autopilot --apply-safe --markdown
dfs review-pr --markdown
```

Autopilot runs:

1. inspect changed code
2. build a fix plan
3. optionally apply safe fixes
4. rerun guard
5. write a markdown review report

This is the product direction: a performance-review agent for AI-generated code changes.

Repo: https://github.com/Vasanthdev2004/diffsentinel

#OpenAIHackathon

## LinkedIn Post 6

DiffSentinel now has the shell experience I wanted:

```powershell
dfs
```

It opens an interactive terminal agent shell with slash commands:

- `/guard`
- `/scan`
- `/plan`
- `/apply --dry-run`
- `/apply`
- `/restore`
- `/doctor`
- `/json`
- `/sarif`

This makes DiffSentinel feel less like a one-off CLI and more like a focused coding-agent companion: inspect changed code, plan fixes, apply safely, rerun, restore if needed.

Repo: https://github.com/Vasanthdev2004/diffsentinel

#OpenAIHackathon

## LinkedIn Post 5

We added the piece that makes DiffSentinel feel more like a coding-agent companion:

```powershell
diffsentinel agent
```

It runs an inspect -> plan -> apply -> verify loop:

- inspects changed code
- explains performance risks
- shows the safe-fix plan
- asks before applying
- reruns guard after fixes
- tells you whether you can continue or commit

This keeps DiffSentinel focused: not another general coding agent, but a safety layer for AI-generated code.

Repo: https://github.com/Vasanthdev2004/diffsentinel

#OpenAIHackathon

## LinkedIn Post 4

Day 3 build update for the #OpenAIHackathon:

DiffSentinel now has a full agent demo path:

```powershell
dfs demo-agent
```

It simulates the story we want judges to understand:

1. A coding agent changes code.
2. The change introduces a latency bug.
3. DiffSentinel runs Agent Guard Mode.
4. It returns Agent JSON v2 with a blocked reason and next action.
5. It applies the safe fix.
6. Guard reruns clean.
7. Restore proves the safe fix is reversible.

This is the product direction: DiffSentinel as the safety layer for AI-generated code.

Repo: https://github.com/Vasanthdev2004/diffsentinel

#OpenAIHackathon

## Short Product Description

DiffSentinel is a terminal-native performance regression guard for your current git diff. It catches high-confidence async and hot-path mistakes before code review, shows them in a focused terminal UI, and can safely apply simple fixes with a backup.

## 30-Second Pitch

Developers move fast, and tiny performance bugs often slip into local changes: a blocking call inside an async handler, a missing await, or a copy inside a hot loop. DiffSentinel runs directly in the terminal against the current git diff, flags high-confidence performance issues, explains the impact, and can safely apply simple fixes. It is local-first, performance-only, and designed to catch problems before PR review or CI.
