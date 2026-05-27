from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .analyzer import analyze_chunk
from .diff import get_diff_chunks
from .patcher import apply_issue
from .rules import can_auto_apply
from .schema import Issue


GOOD_SAMPLE = """import asyncio
import time

async def handle_request():
    await asyncio.sleep(1)
    return {"status": "ok"}
"""

BAD_SAMPLE = """import asyncio
import time

async def handle_request():
    time.sleep(1)
    return {"status": "ok"}
"""


@dataclass(frozen=True)
class DemoResult:
    workspace: Path
    issue: Issue | None
    applied: bool
    target_file: Path
    backup_file: Path | None


def run_demo(*, path: Path | None = None, apply_fix: bool = True, console: Console | None = None) -> DemoResult:
    console = console or Console()
    workspace = _prepare_workspace(path)
    target_file = workspace / "async_blocking.py"

    _run(["git", "init"], cwd=workspace)
    target_file.write_text(GOOD_SAMPLE, encoding="utf-8")
    _run(["git", "add", "async_blocking.py"], cwd=workspace)
    _run(
        ["git", "-c", "user.name=DiffSentinel", "-c", "user.email=demo@diffsentinel.local", "commit", "-m", "baseline"],
        cwd=workspace,
    )
    target_file.write_text(BAD_SAMPLE, encoding="utf-8")

    console.print(Panel(f"Demo workspace: {workspace}", title="DiffSentinel Demo", border_style="cyan"))
    console.print("[bold]Before[/bold]")
    console.print(Syntax(target_file.read_text(encoding="utf-8"), "python", theme="monokai", line_numbers=True))

    chunks = get_diff_chunks(cwd=workspace)
    issues: list[Issue] = []
    for chunk in chunks:
        issues.extend(analyze_chunk(chunk, force_cache=True).issues)

    issue = issues[0] if issues else None
    if issue is None:
        console.print("[bold yellow]No issues detected.[/bold yellow]")
        return DemoResult(workspace=workspace, issue=None, applied=False, target_file=target_file, backup_file=None)

    console.print(
        Panel(
            f"{issue.severity}: {issue.explanation}\n\n"
            f"Impact: {issue.impact}\n\n"
            f"Suggested fix:\n{issue.optimized_code}",
            title=f"{issue.category} at line {issue.line_number}",
            border_style="red" if issue.severity == "CRITICAL" else "yellow",
        )
    )

    backup_file: Path | None = None
    applied = False
    if apply_fix and can_auto_apply(issue):
        patch = apply_issue(target_file, issue)
        backup_file = patch.backup_path
        applied = True
        console.print(f"[bold green]Applied safe fix[/bold green] (backup: {backup_file})")
        console.print("[bold]After[/bold]")
        console.print(Syntax(target_file.read_text(encoding="utf-8"), "python", theme="monokai", line_numbers=True))
    elif apply_fix:
        console.print("[bold yellow]Suggestion requires manual review, so it was not auto-applied.[/bold yellow]")

    return DemoResult(
        workspace=workspace,
        issue=issue,
        applied=applied,
        target_file=target_file,
        backup_file=backup_file,
    )


def _prepare_workspace(path: Path | None) -> Path:
    if path is None:
        return Path(tempfile.mkdtemp(prefix="diffsentinel-demo-"))
    workspace = path.resolve()
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError(f"Demo path must be empty: {workspace}")
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _run(args: list[str], *, cwd: Path) -> None:
    completed = subprocess.run(
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(message or f"Command failed: {' '.join(args)}")
