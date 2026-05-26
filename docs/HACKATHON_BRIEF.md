# DiffSentinel Hackathon Brief

## Positioning

DiffSentinel is a terminal-native performance regression guard for your current diff, with one-keystroke fixes.

It is not trying to replace broad AI code review. Copilot, Claude Code Review, CodeRabbit, and Ellipsis already review broad classes of PR issues. DiffSentinel deliberately narrows the job to high-confidence performance problems that can slip through during fast local iteration.

## Frozen MVP

- Command: `diffsentinel check`
- Input: current `git diff`
- Analysis: one OpenAI call with strict structured output, or local rules fallback
- Output: terminal UI with changed code and performance findings
- Apply: press `A` to backup the file and atomically replace the flagged line

## Demo Hook

1. Show `time.sleep(1)` inside `async def handle_request()`.
2. Run `diffsentinel check`.
3. TUI flags `CRITICAL - Blocking I/O in async context`.
4. Press `A`.
5. Show `await asyncio.sleep(1)` applied live.

## Honest Limits

- This is a fast first-pass auditor, not a profiler.
- Analysis quality depends on the diff context.
- The hackathon build targets Python async/performance samples.
- Multi-agent review, watcher mode, pre-commit hooks, and IDE plugins are post-MVP.
