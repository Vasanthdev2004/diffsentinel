from __future__ import annotations

import json
import os
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


UNICODE_LOGO = r"""
██████╗ ███████╗███████╗
██╔══██╗██╔════╝██╔════╝
██║  ██║█████╗  ███████╗
██║  ██║██╔══╝  ╚════██║
██████╔╝██║     ███████║
╚═════╝ ╚═╝     ╚══════╝
"""

ASCII_LOGO = r"""
 ____    _____   ____
|  _ \  |  ___| / ___|
| | | | | |_    \___ \
| |_| | |  _|    ___) |
|____/  |_|     |____/
"""


@dataclass
class ShellState:
    root: Path
    last_finding_set: FindingSet | None = None
    last_report: dict | None = None
    last_apply: ApplyOutcome | None = None
    messages: list[dict[str, str]] | None = None
    last_chat_error: str | None = None


def run_shell(*, root: str | Path = ".", console: Console | None = None, input_func: Callable[[str], str] | None = None) -> int:
    console = console or Console()
    state = ShellState(root=_resolve_shell_root(Path(root).resolve()))
    state.messages = []
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
            _reply_to_chat(console, state, command)
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
        elif name == "history":
            _print_history(console, state)
        elif name == "chat-debug":
            _print_chat_debug(console, state)
        elif name == "clear":
            console.clear()
            _print_welcome(console, state)
        else:
            console.print(f"[red]Unknown command:[/red] /{name}. Try /help.")


def _print_welcome(console: Console, state: ShellState) -> None:
    console.print(f"[cyan]{_logo_for_console(console)}[/cyan]")
    settings = load_settings(state.root)
    console.print(
        Panel(
            f"Safety layer for AI-generated code\n"
            f"Project: {state.root}\n"
            f"Model: {settings.openai_model}    Mode: {'live' if os.getenv('OPENAI_API_KEY') else 'local fallback'}\n"
            f"Try: /guard, /scan, /plan, /apply --dry-run, or ask: can I commit?",
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
        ("/history", "Show chat messages from this shell session"),
        ("/chat-debug", "Show whether live chat fell back locally"),
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
    table.add_row("chat", "live" if os.getenv("OPENAI_API_KEY") and not state.last_chat_error else "local fallback")
    table.add_row("chat_error", state.last_chat_error or "none")
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
        console.print(
            Panel(
                f"{exc}\n\n"
                "Run /scan for a whole-project audit, or start dfs inside a git repository "
                "to use /guard on changed files.",
                title="Guard unavailable",
                border_style="yellow",
            )
        )
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


def _reply_to_chat(console: Console, state: ShellState, message: str) -> None:
    state.messages = state.messages or []
    state.messages.append({"role": "user", "content": message})
    settings = load_settings(state.root)
    reply, error = _openai_shell_reply(state, message, settings.openai_model, settings.reasoning_effort)
    state.last_chat_error = error
    if reply is None:
        reply = _local_shell_reply(state, message)
    state.messages.append({"role": "assistant", "content": reply})
    console.print(Panel(reply, title="DiffSentinel", border_style="cyan"))


def _local_shell_reply(state: ShellState, message: str) -> str:
    lowered = message.lower()
    normalized = lowered.strip(" !?.")
    if normalized in {"hi", "hello", "hey", "gm", "good morning", "yo"}:
        return (
            "Hey. I am here. Run /guard to inspect your current diff, /scan for a project audit, "
            "or ask me something like `can I commit?` after a report exists."
        )
    if "help" in lowered and state.last_report is None:
        return "I can help with /guard, /scan, /plan, /apply --dry-run, /apply, /restore, /doctor, /json, and /sarif."
    if state.last_report is None:
        return (
            "I do not have a report yet. Run /guard to inspect the current diff, "
            "or /scan to inspect the whole project."
        )
    summary = state.last_report["summary"]
    if "commit" in lowered:
        if summary["critical"]:
            return (
                f"Not yet. I found {summary['critical']} critical issue(s). "
                "Run /plan to review them, then /apply or /apply --dry-run."
            )
        return "Yes, from a DiffSentinel performance-risk view, you can continue or commit."
    if "apply" in lowered or "fix" in lowered:
        if summary["safe_fixes"]:
            return f"I found {summary['safe_fixes']} safe fix(es). Run /apply --dry-run first, then /apply."
        return "I do not see any safe fixes in the last report."
    if "what" in lowered or "wrong" in lowered or "risk" in lowered:
        if summary["issues"] == 0:
            return "The last report is clean. I did not find performance issues."
        first_issue = state.last_report["issues"][0]
        return (
            f"The main risk is {first_issue['category']} in "
            f"{first_issue['file_path']}:{first_issue['line_number']}. "
            f"{first_issue['explanation']} Impact: {first_issue['impact']}"
        )
    return (
        f"Last report: {summary['issues']} issue(s), {summary['critical']} critical, "
        f"{summary['safe_fixes']} safe fix(es), {summary['manual_review']} manual review. "
        "Use /plan, /apply --dry-run, /apply, or /restore."
    )


def _openai_shell_reply(state: ShellState, message: str, model: str, reasoning_effort: str) -> tuple[str | None, str | None]:
    if not os.getenv("OPENAI_API_KEY"):
        return None, None
    try:
        from openai import OpenAI

        client = OpenAI(timeout=15)
        response = _create_chat_response(
            client,
            model=model,
            reasoning_effort=reasoning_effort,
            context=_chat_context(state, message),
            with_reasoning=True,
        )
    except Exception as first_exc:
        try:
            from openai import OpenAI

            client = OpenAI(timeout=15)
            response = _create_chat_response(
                client,
                model=model,
                reasoning_effort=reasoning_effort,
                context=_chat_context(state, message),
                with_reasoning=False,
            )
        except Exception as second_exc:
            return None, f"{type(second_exc).__name__}: {second_exc} (first attempt: {type(first_exc).__name__})"
    return getattr(response, "output_text", None), None


def _create_chat_response(client, *, model: str, reasoning_effort: str, context: str, with_reasoning: bool):
    kwargs = {
        "model": model,
        "instructions": (
            "You are DiffSentinel, a concise terminal assistant for performance-risk review. "
            "You can answer normal conversation, but stay grounded in the current project context. "
            "If the user asks you to modify files, recommend slash commands like /guard, /plan, "
            "/apply --dry-run, /apply, /restore, /scan, /doctor. Do not claim you edited files unless "
            "the session context says an apply run happened."
        ),
        "input": context,
        "store": False,
    }
    if with_reasoning:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    return client.responses.create(**kwargs)


def _chat_context(state: ShellState, message: str) -> str:
    return json.dumps(
        {
            "user_message": message,
            "project": str(state.root),
            "last_report": state.last_report,
            "last_apply": state.last_apply.__dict__ if state.last_apply else None,
            "recent_messages": (state.messages or [])[-6:],
            "available_slash_commands": [
                "/guard",
                "/scan",
                "/plan",
                "/apply --dry-run",
                "/apply",
                "/restore",
                "/doctor",
                "/json",
                "/sarif",
                "/history",
            ],
        },
        default=str,
    )


def _print_history(console: Console, state: ShellState) -> None:
    table = Table(title="Session history", box=box.SIMPLE_HEAVY)
    table.add_column("Role")
    table.add_column("Message")
    for item in state.messages or []:
        table.add_row(item["role"], item["content"])
    console.print(table)


def _print_chat_debug(console: Console, state: ShellState) -> None:
    if state.last_chat_error:
        console.print(Panel(state.last_chat_error, title="Last chat fallback reason", border_style="yellow"))
        return
    if os.getenv("OPENAI_API_KEY"):
        console.print("[green]Live chat is available. No chat error recorded.[/green]")
    else:
        console.print("[yellow]OPENAI_API_KEY is not set. Chat is using local fallback replies.[/yellow]")


def _resolve_shell_root(start: Path) -> Path:
    try:
        return find_git_root(start)
    except HookError:
        pass
    if _looks_like_project(start):
        return start
    candidates = [child for child in start.iterdir() if child.is_dir() and _looks_like_project(child)]
    if len(candidates) == 1:
        return candidates[0].resolve()
    preferred = [candidate for candidate in candidates if candidate.name.lower() == "diffsentinel"]
    if preferred:
        return preferred[0].resolve()
    return start


def _looks_like_project(path: Path) -> bool:
    return any((path / marker).exists() for marker in (".git", ".diffsentinel.toml", "pyproject.toml"))


def _logo_for_console(console: Console) -> str:
    if console.is_terminal and console.encoding and console.encoding.lower().replace("-", "") == "utf8":
        return UNICODE_LOGO
    return ASCII_LOGO
