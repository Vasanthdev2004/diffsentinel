from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from .analyzer import analyze_chunk
from .agent import apply_safe_fixes, build_agent_report, collect_changed_findings, restore_run
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


@dataclass(frozen=True)
class AgentDemoResult:
    workspace: Path
    first_report: dict[str, Any]
    clean_report: dict[str, Any]
    applied_count: int
    restored_count: int
    target_file: Path


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


def run_agent_demo(*, path: Path | None = None, restore_after: bool = True, console: Console | None = None) -> AgentDemoResult:
    console = console or Console()
    workspace = _prepare_workspace(path)
    target_file = workspace / "service.py"

    _run(["git", "init"], cwd=workspace)
    target_file.write_text(GOOD_SAMPLE, encoding="utf-8")
    _run(["git", "add", "service.py"], cwd=workspace)
    _run(
        ["git", "-c", "user.name=DiffSentinel", "-c", "user.email=demo@diffsentinel.local", "commit", "-m", "baseline"],
        cwd=workspace,
    )
    target_file.write_text(BAD_SAMPLE, encoding="utf-8")

    console.print(Panel(f"Workspace: {workspace}", title="Agent Demo", border_style="cyan"))
    _step(console, "1", "Coding agent introduces a latency regression")
    console.print(Syntax(target_file.read_text(encoding="utf-8"), "python", theme="monokai", line_numbers=True))

    _step(console, "2", "DiffSentinel guard audits the changed diff")
    finding_set = collect_changed_findings(
        cwd=workspace,
        live=False,
        model="gpt-5.5",
        timeout=10.0,
        reasoning_effort="low",
    )
    first_report = build_agent_report(finding_set, fail_on_critical=True)
    _print_report_summary(console, first_report)

    _step(console, "3", "Safe fixes are applied with rollback metadata")
    outcome = apply_safe_fixes(finding_set.findings, root=workspace)
    console.print(
        Panel(
            f"Applied: {len(outcome.applied)}\n"
            f"Skipped: {len(outcome.skipped)}\n"
            f"Run id: {outcome.run_id}\n"
            f"Metadata: {outcome.metadata_path}",
            title="Safe Apply",
            border_style="green",
        )
    )
    console.print(Syntax(target_file.read_text(encoding="utf-8"), "python", theme="monokai", line_numbers=True))

    _step(console, "4", "Guard reruns and clears the change")
    clean_set = collect_changed_findings(
        cwd=workspace,
        live=False,
        model="gpt-5.5",
        timeout=10.0,
        reasoning_effort="low",
    )
    clean_report = build_agent_report(clean_set, fail_on_critical=True)
    _print_report_summary(console, clean_report)

    restored_count = 0
    if restore_after:
        _step(console, "5", "Restore proves safe apply is reversible")
        restore = restore_run(root=workspace)
        restored_count = len(restore.restored)
        console.print(
            Panel(
                f"Restored: {restored_count}\nSkipped: {len(restore.skipped)}\nRun id: {restore.run_id}",
                title="Rollback",
                border_style="yellow",
            )
        )

    return AgentDemoResult(
        workspace=workspace,
        first_report=first_report,
        clean_report=clean_report,
        applied_count=len(outcome.applied),
        restored_count=restored_count,
        target_file=target_file,
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


def _step(console: Console, number: str, label: str) -> None:
    console.print(f"\n[bold cyan]Step {number}[/bold cyan] {label}")


def _print_report_summary(console: Console, report: dict[str, Any]) -> None:
    summary = report["summary"]
    table = Table(title="Agent JSON v2 Summary")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("schema_version", report["schema_version"])
    table.add_row("issues", str(summary["issues"]))
    table.add_row("critical", str(summary["critical"]))
    table.add_row("safe_fixes", str(summary["safe_fixes"]))
    table.add_row("blocked_reason", str(report["blocked_reason"]))
    table.add_row("next_action", report["next_action"])
    table.add_row("exit_code", str(report["exit_policy"]["exit_code"]))
    console.print(table)
