# DiffSentinel - Phase 1 Pitch Deck

## Slide 1 - Problem: AI-Generated Code Can Ship Latency Bugs

Developers and coding agents move fast, but performance regressions are easy to miss before commit.

Pain points:

- Blocking calls sneak into async handlers.
- Missing `await` silently breaks async behavior.
- Copies and inefficient loops add avoidable latency.
- Most AI code review happens later, around PRs or CI.
- Local coding agents can generate code faster than humans can review it.

The core problem:

> AI can write code quickly, but teams still need a local safety layer that checks whether the generated change introduces latency risk.

## Slide 2 - Solution: DiffSentinel Agent Guard

DiffSentinel is a terminal-native performance and latency guardrail for local code changes.

Main flow:

1. A developer or coding agent changes code.
2. DiffSentinel audits the current diff or project.
3. It flags critical performance issues.
4. It separates safe fixes from manual-review items.
5. It can apply safe fixes and rerun the guard.
6. It can block risky commits through a pre-commit hook.

Key commands:

```powershell
diffsentinel agent
diffsentinel guard --changed --json --fail-on-critical
diffsentinel apply-safe --changed
diffsentinel restore
diffsentinel demo-agent
```

Why it is different:

> DiffSentinel is not trying to be a general coding agent. It is the safety layer that checks what coding agents changed.

## Slide 3 - Tools, Tech Stack, and Current MVP

Tech stack:

- Python CLI
- Rich terminal UI
- Pydantic structured result schema
- OpenAI API with `gpt-5.5` live mode
- Local rules fallback for offline demos
- Git diff and pre-commit hook integration
- GitHub Actions CI

Current MVP is working:

- `diffsentinel init` onboarding
- `diffsentinel doctor` setup checks
- `diffsentinel check` for current git diff
- `diffsentinel scan` for whole-project Python scan
- `diffsentinel guard` for coding-agent JSON workflow
- `diffsentinel agent` for inspect, plan, apply, verify loop
- `diffsentinel demo-agent` for the full demo story
- Safe apply with rollback metadata
- Releases through `v0.7.0`
- 32 passing tests

## Slide 4 - ICP: Who Needs DiffSentinel?

Ideal Customer Profile:

- Backend/API developers using async Python services.
- AI-assisted developers using Codex, Claude Code, Gemini CLI, or similar tools.
- Hackathon builders shipping fast with AI-generated code.
- Small engineering teams that want local guardrails before PR review.

Primary user:

> A developer who asks an AI coding agent to modify backend code, then wants a fast local check before committing.

Why now:

- Coding agents are becoming normal in developer workflows.
- Generated code can be correct-looking but performance-risky.
- Teams need local guardrails that are faster than PR review and lighter than full profiling.

Expansion path:

- JavaScript/TypeScript checks
- GitHub Action
- SARIF output
- MCP or agent-tool integration
- More advanced AST-backed analysis
