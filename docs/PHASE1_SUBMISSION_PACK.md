# Phase 1 Submission Pack

## Required Items

### 1. MVP With Main Features Working

Status: ready

Proof:

- GitHub repo: https://github.com/Vasanthdev2004/diffsentinel
- Latest release: https://github.com/Vasanthdev2004/diffsentinel/releases/tag/v0.7.0
- CI passing on Python 3.11 and 3.12
- Tests: `32 passed`

Core demo command:

```powershell
diffsentinel demo-agent
```

### 2. Clear User Flow / Product Journey

1. Developer or coding agent changes backend code.
2. DiffSentinel runs locally in the terminal.
3. It audits the current git diff or project.
4. It detects performance and latency risks.
5. It separates safe fixes from manual-review issues.
6. It applies safe fixes with rollback metadata.
7. It reruns guard and gives a continue/block recommendation.

### 3. Four-Slide Pitch Deck

File:

```text
docs/PHASE1_PITCH_DECK.md
```

Slides:

1. Problem / pain point
2. Solution and key features
3. Tools / tech stack
4. ICP / target audience

### 4. Daily Progress Form Copy

What have you done today?

```text
Today I moved DiffSentinel from a simple CLI demo into an agentic code safety layer. The project now has Agent Guard Mode, a v2 JSON contract for coding agents, safe apply with rollback metadata, restore support, onboarding with init/doctor, and an interactive `diffsentinel agent` flow that inspects changed code, plans safe fixes, applies them, reruns guard, and gives a final recommendation. I also added `diffsentinel demo-agent`, which shows the full story in one command: an AI/coding agent introduces a latency bug, DiffSentinel catches it, applies a safe fix, reruns clean, and demonstrates rollback. The repo is public, CI is green, and tests are passing.
```

Working proof:

```text
https://github.com/Vasanthdev2004/diffsentinel
```

Working document:

```text
https://github.com/Vasanthdev2004/diffsentinel/blob/main/docs/PHASE1_SUBMISSION_PACK.md
```

Build in public post draft:

```text
Day 3 update for the #OpenAIHackathon:

DiffSentinel is now moving from "performance CLI" to "agentic code safety layer."

New flow:
diffsentinel agent

It inspects changed code, explains latency risks, shows a safe-fix plan, applies safe fixes, reruns guard, and gives a final continue/block recommendation.

We also added:
- Agent JSON v2
- reversible safe apply
- restore from last run
- demo-agent command
- onboarding with init/doctor
- CI passing with 32 tests

The story is simple: coding agents can write code fast, but DiffSentinel checks whether their changes introduce latency regressions before commit.

Repo: https://github.com/Vasanthdev2004/diffsentinel

#OpenAIHackathon
```

Blockers:

```text
No major blocker. Phase 1 MVP and pitch materials are ready. Remaining work is to record a short proof video/GIF and polish final launch assets.
```
