# DiffSentinel Phase 1 Progress

Use this as source text for the hackathon progress form. The current Phase 1 submission pack is in `docs/PHASE1_SUBMISSION_PACK.md`.

## Project Name

DiffSentinel

## One-Line Description

DiffSentinel is an agentic code safety layer that audits local changes from developers or coding agents, flags performance and latency risks, and safely applies high-confidence fixes before commit.

## Problem Statement

Developers and coding agents often introduce small performance regressions while moving fast: blocking calls inside async handlers, missing awaits, repeated object copies, or inefficient collection usage. These bugs are easy to miss locally and usually get caught late in PR review, CI, or production behavior.

## Target User

Backend/API developers, hackathon builders, and AI-assisted coders using tools like Codex, Claude Code, or Gemini CLI who want fast local feedback before committing generated code.

## Product Journey

1. Developer changes code locally.
2. Developer or coding agent runs `diffsentinel agent` or `diffsentinel guard`.
3. DiffSentinel reads the current `git diff` or scans the project.
4. It analyzes changed Python snippets through OpenAI Structured Outputs when available, or a local rules engine when offline.
5. It returns a fix plan with safe fixes and manual-review issues.
6. It can apply safe fixes, save rollback metadata, rerun guard, and recommend continue/block.

## MVP Scope

Must-have:

- Read local `git diff`.
- Detect Python async/performance issues.
- Show terminal output/UI with severity and impact.
- Offer safe one-line fixes.
- Backup the original file before applying fixes.
- Work without network through a local rules fallback.
- Provide JSON output for scripts.
- Provide agent-facing guard output.
- Apply safe fixes reversibly.

Nice-to-have:

- Richer patch preview before apply.
- Config file for thresholds and ignored paths.
- JavaScript/TypeScript support.
- Pre-commit hook installer.
- IDE extension.
- AST-backed context extraction.

## Current Progress

Completed:

- Public GitHub repo: `https://github.com/Vasanthdev2004/diffsentinel`
- Python package scaffold with CLI entry point.
- `diffsentinel check` command.
- Git diff extraction and filtering.
- Pydantic schema for structured analysis results.
- OpenAI Structured Outputs integration path.
- Offline local rules engine.
- Rich terminal UI.
- Safe apply flow with backup and atomic write.
- `--json`, `--no-tui`, `--apply-first`, and `--exit-on-critical` flags.
- Self-contained `diffsentinel demo` command for easy proof.
- Demo samples for async blocking, missing await, requests blocking, clone in loop, and nested loops.
- MIT license, roadmap, README, and GitHub Actions CI.
- CI passing on Python 3.11 and 3.12.
- Agent Guard Mode with v2 JSON.
- Interactive `diffsentinel agent` flow.
- `diffsentinel demo-agent` for the checkpoint demo.
- Phase 1 pitch deck and submission pack.

## Execution Plan

Next 24 hours:

- Record the first short demo video.
- Add a GIF or screenshot to the README.
- Rehearse the demo from a clean clone.
- Tighten the terminal UI copy for the video.

Before final submission:

- Add one polished demo recording under 90 seconds.
- Add a GitHub release tag.
- Add a final submission description and judging notes.
- Validate install and demo commands on a clean machine.

## Blockers

No major technical blockers. Remaining work is demo packaging, visual polish, and final submission assets.

## Honest Limitations

DiffSentinel is a fast first-pass auditor, not a full profiler. The hackathon build focuses on Python diffs and high-confidence performance mistakes. Broader language support, AST context extraction, and pre-commit/IDE integrations are planned after the hackathon MVP.
