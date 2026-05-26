# DiffSentinel Phase 1 Progress

Use this as the source text for the hackathon progress form.

## Project Name

DiffSentinel

## One-Line Description

DiffSentinel is a terminal-native performance regression guard that reviews your current `git diff`, flags async and hot-path mistakes, and can safely apply simple fixes before commit.

## Problem Statement

Developers often introduce small performance regressions while moving fast: blocking calls inside async handlers, missing awaits, repeated object copies, or inefficient collection usage. These bugs are easy to miss locally and usually get caught late in PR review, CI, or production behavior.

## Target User

Backend/API developers, hackathon builders, and AI-assisted coders who work in the terminal and want fast feedback before committing code.

## Product Journey

1. Developer changes code locally.
2. Developer runs `diffsentinel check`.
3. DiffSentinel reads the current `git diff`.
4. It analyzes changed Python snippets through OpenAI Structured Outputs when available, or a local rules engine when offline.
5. The terminal UI shows performance issues with severity, impact, and a suggested fix.
6. For high-confidence single-line fixes, the developer can press `A` or run `--apply-first`.
7. DiffSentinel creates a backup and atomically rewrites the file.

## MVP Scope

Must-have:

- Read local `git diff`.
- Detect Python async/performance issues.
- Show terminal output/UI with severity and impact.
- Offer safe one-line fixes.
- Backup the original file before applying fixes.
- Work without network through a local rules fallback.
- Provide JSON output for scripts.

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
- Demo samples for async blocking, missing await, requests blocking, clone in loop, and nested loops.
- MIT license, roadmap, README, and GitHub Actions CI.
- CI passing on Python 3.11 and 3.12.

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
