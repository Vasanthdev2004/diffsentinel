# DiffSentinel Roadmap

DiffSentinel is evolving from a Python performance CLI into an agentic code safety layer: a guardrail that runs after Codex, Claude Code, Gemini CLI, or any coding agent changes files.

## v0.5 - Agent Guard Mode

- `diffsentinel guard` for coding-agent workflows.
- `diffsentinel fix-plan` for safe-fix vs manual-review planning.
- `diffsentinel apply-safe` for high-confidence single-line fixes.
- `diffsentinel restore` for rollback from saved run metadata.
- Agent JSON v2 with `summary`, `issues`, `safe_fixes`, `manual_review`, `blocked_reason`, `next_action`, and `exit_policy`.
- Run metadata under `.diffsentinel/runs/`.

## v0.6 - Safe Fix Engine

- Batch multi-file safe apply with stronger conflict handling.
- More granular rollback by run id and file.
- Fix previews before applying in the TUI.
- Safer structured patch spans for multi-line fixes.

## v0.7 - Language Expansion

- JavaScript/TypeScript async checks.
- Go context and goroutine performance checks.
- Rust async/blocking and clone-in-loop checks.
- Keep Python as the flagship demo path.

## v0.8 - Intelligence Layer

- AST-backed context extraction for Python and JS/TS.
- OpenAI live analysis batching with `gpt-5.5`.
- Per-rule confidence scoring and false-positive suppression.
- `.diffsentinel.toml` rule toggles, severity thresholds, ignored paths, and model settings.

## v0.9 - Workflow Integrations

- GitHub Action.
- SARIF output for GitHub code scanning.
- Codex, Claude Code, and Gemini CLI adapter docs.
- MCP integration plan so agent tools can call DiffSentinel as a guardrail.

## v1.0 - Launch-Grade Product

- `pipx install diffsentinel` packaging path.
- Demo GIFs and polished docs.
- Benchmark suite with known performance regressions.
- Release automation and changelog flow.
- Final demo story: AI agent writes a regression, DiffSentinel catches it, fixes safe issues, and blocks the commit.
