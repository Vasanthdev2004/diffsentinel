from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .patcher import PatchError, apply_issue
from .rules import can_auto_apply
from .schema import Issue


@dataclass(frozen=True)
class IssueTarget:
    file_path: str
    issue: Issue
    excerpt: str


def show_review(targets: list[IssueTarget], *, console: Console | None = None) -> int:
    console = console or Console()
    if not targets:
        console.print("[bold green]DiffSentinel[/bold green] No performance issues found.")
        return 0

    if not sys.stdin.isatty():
        _print_noninteractive(console, targets)
        return len(targets)

    selected = 0
    while True:
        console.clear()
        _render(console, targets, selected)
        key = _read_key()
        if key in {"q", "Q", "\x1b"}:
            return len(targets)
        if key == "up":
            selected = (selected - 1) % len(targets)
        elif key == "down":
            selected = (selected + 1) % len(targets)
        elif key in {"a", "A"}:
            target = targets[selected]
            try:
                result = apply_issue(target.file_path, target.issue)
            except PatchError as exc:
                console.print(f"[bold red]Apply failed:[/bold red] {exc}")
                _wait_for_key()
                continue
            console.clear()
            console.print(
                Panel(
                    f"Applied line {result.line_number} in {result.file_path}\n"
                    f"Backup: {result.backup_path}",
                    title="[bold green]Fix Applied[/bold green]",
                    border_style="green",
                )
            )
            _wait_for_key()
            return len(targets)


def _render(console: Console, targets: list[IssueTarget], selected: int) -> None:
    target = targets[selected]
    issue = target.issue

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(Layout(name="code"), Layout(name="issues"))

    header = Text()
    header.append("DiffSentinel ", style="bold cyan")
    header.append("* cache-safe local diff audit", style="green")
    header.append(f"   File: {target.file_path}", style="white")
    header.append(f"   Issues: {len(targets)}", style="bold white")
    layout["header"].update(Panel(header, box=box.SQUARE, style="white on #0d1117"))

    layout["code"].update(
        Panel(
            _excerpt_text(target.excerpt, issue.line_number),
            title="Changed Code",
            border_style="cyan",
            box=box.SQUARE,
        )
    )
    layout["issues"].update(
        Panel(
            _issue_table(targets, selected),
            title="Performance Issues",
            border_style="red" if issue.severity == "CRITICAL" else "yellow",
            box=box.SQUARE,
        )
    )

    footer = Align.center("[A] Apply safe fix    [Up/Down] Navigate    [Q] Quit", vertical="middle")
    layout["footer"].update(Panel(footer, box=box.SQUARE, style="white on #0d1117"))
    console.print(layout)


def _excerpt_text(excerpt: str, selected_line: int) -> Text:
    text = Text()
    for raw_line in excerpt.splitlines():
        style = ""
        if raw_line.strip().startswith(str(selected_line)):
            style = "bold white on red"
        elif "*" in raw_line[:6]:
            style = "bold yellow"
        text.append(raw_line + "\n", style=style)
    return text


def _issue_table(targets: list[IssueTarget], selected: int) -> Group:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    for index, target in enumerate(targets):
        issue = target.issue
        pointer = ">" if index == selected else " "
        severity_style = "bold red" if issue.severity == "CRITICAL" else "bold yellow"
        row = Text()
        row.append(f"{pointer} {issue.severity}", style=severity_style)
        row.append(f" line {issue.line_number}\n", style="bold white")
        row.append(f"{issue.explanation}\n", style="white")
        row.append(f"Impact: {issue.impact}\n", style="dim")
        if can_auto_apply(issue):
            row.append("Safe auto-fix:\n", style="bold green")
        else:
            row.append("Manual review suggestion:\n", style="bold yellow")
        row.append(issue.optimized_code, style="green")
        table.add_row(Panel(row, border_style="red" if issue.severity == "CRITICAL" else "yellow"))
    return Group(table)


def _print_noninteractive(console: Console, targets: list[IssueTarget]) -> None:
    for target in targets:
        issue = target.issue
        style = "bold red" if issue.severity == "CRITICAL" else "bold yellow"
        console.print(f"[{style}]{issue.severity}[/{style}] {target.file_path}:{issue.line_number} {issue.explanation}")
        console.print(f"Impact: {issue.impact}")
        console.print(f"Fix: [green]{issue.optimized_code}[/green]")


def _read_key() -> str:
    if os.name == "nt":
        import msvcrt

        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            second = msvcrt.getwch()
            return {"H": "up", "P": "down"}.get(second, second)
        return key

    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
        if key == "\x1b" and sys.stdin.read(1) == "[":
            return {"A": "up", "B": "down"}.get(sys.stdin.read(1), key)
        return key
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _wait_for_key() -> None:
    if sys.stdin.isatty():
        _read_key()
