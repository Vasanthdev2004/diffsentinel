from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agent import (
    AgentError,
    ApplyOutcome,
    FindingSet,
    apply_safe_fixes,
    build_agent_report,
    collect_changed_findings,
    collect_project_findings,
    print_fix_plan,
    report_json,
    restore_run,
)
from .hooks import HookError, find_git_root
from .onboarding import print_doctor, run_doctor
from .sarif import sarif_json
from .settings import load_settings


LOGO = r"""
██████╗ ███████╗███████╗
██╔══██╗██╔════╝██╔════╝
██║  ██║█████╗  ███████╗
██║  ██║██╔══╝  ╚════██║
██████╔╝██║     ███████║
╚═════╝ ╚═╝     ╚══════╝
"""


@dataclass
class ShellState:
    root: Path
    last_finding_set: FindingSet | None = None
    last_report: dict | None = None
    last_apply: ApplyOutcome | None = None


def run_shell(*, root: str | Path = ".", console: Console | None = None, input_func: Callable[[str], str] | None = None) -> int:
    console = console or Console()
    state = ShellState(root=Path(root).resolve())
    _print_welcome(console, state)
    input_func = input_func or console.input

    while True:
        try:
            command = input_func("[bold cyan]dfs >[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Exiting DiffSentinel shell.[/dim]")
            return 0

        if not command:
            continue
        if not command.startswith("/"):
            console.print("[yellow]Use slash commands. Try /help.[/yellow]")
            continue

        name, _, rest = command[1:].partition(" ")
        name = name.lower()
        args = rest.split() if rest else []

        if name in {"exit", "quit"}:
            console.print("[green]Session closed.[/green]")
            return 0
        if name == "help":
            _print_help(console)
        elif name == "status":
            _print_status(console, state)
        elif name == "doctor":
            print_doctor(run_doctor(state.root), console)
        elif name == "guard":
            _run_guard(console, state, project="--project" in args)
        elif name == "scan":
            _run_guard(console, state, project=True)
        elif name == "plan":
            _print_last_plan(console, state)
        elif name == "apply":
            _apply_last(console, state, dry_run="--dry-run" in args)
        elif name == "restore":
            _restore_last(console, state)
        elif name == "json":
            _print_last_json(console, state)
        elif name == "sarif":
            _print_last_sarif(console, state)
        elif name == "clear":
            console.clear()
            _print_welcome(console, state)
        else:
            console.print(f"[red]Unknown command:[/red] /{name}. Try /help.")


def _print_welcome(console: Console, state: ShellState) -> None:
    console.print(f"[cyan]{LOGO}[/cyan]")
    console.print(
        Panel(
            f"Safety layer for AI-generated code\nProject: {state.root}\nType /help to see commands.",
            title="DiffSentinel Agent Shell",
            border_style="cyan",
        )
    )


def _print_help(console: Console) -> None:
    table = Table(title="Slash commands", box=box.SIMPLE_HEAVY)
    table.add_column("Command")
    table.add_column("Action")
    rows = [
        ("/status", "Show project, git, config, and last report state"),
        ("/guard", "Audit current git diff"),
        ("/scan", "Audit whole project"),
        ("/plan", "Show fix plan from last report"),
        ("/apply", "Apply safe fixes from last report"),
        ("/apply --dry-run", "Preview safe fixes without writing"),
        ("/restore", "Restore latest safe-apply run"),
        ("/doctor", "Run setup diagnostics"),
        ("/json", "Print last agent JSON"),
        ("/sarif", "Print last report as SARIF"),
        ("/clear", "Clear screen"),
        ("/exit", "Exit shell"),
    ]
    for command, action in rows:
        table.add_row(command, action)
    console.print(table)


def _print_status(console: Console, state: ShellState) -> None:
    settings = load_settings(state.root)
    try:
        git_root = find_git_root(state.root)
    except HookError:
        git_root = None
    table = Table(title="Session status", box=box.SIMPLE_HEAVY)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("project", str(state.root))
    table.add_row("git_root", str(git_root) if git_root else "not a git repository")
    table.add_row("config", str(settings.config_path) if settings.config_path else "defaults")
    table.add_row("model", settings.openai_model)
    table.add_row("last_report", "yes" if state.last_report else "none")
    table.add_row("last_apply", state.last_apply.run_id if state.last_apply else "none")
    console.print(table)


def _run_guard(console: Console, state: ShellState, *, project: bool) -> None:
    settings = load_settings(state.root)
    try:
        if project:
            finding_set = collect_project_findings(
                path=state.root,
                live=settings.scan_live,
                model=settings.openai_model,
                timeout=10.0,
                reasoning_effort=settings.reasoning_effort,
                max_files=settings.scan_max_files,
                exclude_tests=settings.scan_exclude_tests,
                ignore_paths=settings.ignore_paths,
                enabled_rules=settings.rules,
            )
        else:
            finding_set = collect_changed_findings(
                cwd=state.root,
                live=False,
                model=settings.openai_model,
                timeout=10.0,
                reasoning_effort=settings.reasoning_effort,
                enabled_rules=settings.rules,
            )
    except AgentError as exc:
        console.print(f"[red]Guard failed:[/red] {exc}")
        return

    report = build_agent_report(finding_set, fail_on_critical=True)
    state.last_finding_set = finding_set
    state.last_report = report
    print_fix_plan(report, console)


def _print_last_plan(console: Console, state: ShellState) -> None:
    if not state.last_report:
        console.print("[yellow]No report yet. Run /guard or /scan first.[/yellow]")
        return
    print_fix_plan(state.last_report, console)


def _apply_last(console: Console, state: ShellState, *, dry_run: bool) -> None:
    if not state.last_finding_set:
        console.print("[yellow]No findings yet. Run /guard or /scan first.[/yellow]")
        return
    outcome = apply_safe_fixes(state.last_finding_set.findings, root=state.last_finding_set.root, dry_run=dry_run)
    if not dry_run:
        state.last_apply = outcome
    label = "Would apply" if dry_run else "Applied"
    console.print(f"[green]{label} {len(outcome.applied)} safe fixes.[/green]")
    if outcome.skipped:
        console.print(f"[yellow]Skipped {len(outcome.skipped)} findings.[/yellow]")


def _restore_last(console: Console, state: ShellState) -> None:
    try:
        outcome = restore_run(root=state.root)
    except AgentError as exc:
        console.print(f"[red]Restore failed:[/red] {exc}")
        return
    console.print(f"[green]Restored {len(outcome.restored)} files from run {outcome.run_id}.[/green]")


def _print_last_json(console: Console, state: ShellState) -> None:
    if not state.last_report:
        console.print("[yellow]No report yet. Run /guard or /scan first.[/yellow]")
        return
    console.print_json(report_json(state.last_report))


def _print_last_sarif(console: Console, state: ShellState) -> None:
    if not state.last_report:
        console.print("[yellow]No report yet. Run /guard or /scan first.[/yellow]")
        return
    console.print(json.dumps(json.loads(sarif_json(state.last_report)), indent=2))
