from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass

from rich import box
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .patcher import PatchError, apply_issue
from .rules import can_auto_apply
from .schema import Issue


SURFACE = "#0d1117"
MUTED = "#7d8590"
TEXT = "#f0f6fc"
CYAN = "#39c5cf"
GREEN = "#56d364"
AMBER = "#d29922"
RED = "#ff6b6b"


@dataclass(frozen=True)
class IssueTarget:
    file_path: str
    issue: Issue
    excerpt: str
    apply_path: str | None = None


def show_review(
    targets: list[IssueTarget],
    *,
    console: Console | None = None,
    interactive: bool = True,
) -> int:
    console = console or Console()
    if not targets:
        console.print(_empty_state())
        return 0

    if not interactive or not sys.stdin.isatty():
        _print_noninteractive(console, targets)
        return len(targets)

    selected = 0
    status_message = "Reviewing current diff"
    while True:
        console.clear()
        console.print(render_dashboard(targets, selected, status_message=status_message))
        key = _read_key()
        if key in {"q", "Q", "\x1b"}:
            return len(targets)
        if key == "up":
            selected = (selected - 1) % len(targets)
            status_message = "Moved to previous issue"
        elif key == "down":
            selected = (selected + 1) % len(targets)
            status_message = "Moved to next issue"
        elif key in {"a", "A"}:
            target = targets[selected]
            if not can_auto_apply(target.issue):
                status_message = "Manual review required; safe apply is disabled for this issue"
                continue
            try:
                result = apply_issue(target.apply_path or target.file_path, target.issue)
            except PatchError as exc:
                status_message = f"Apply failed: {exc}"
                continue
            console.clear()
            console.print(_applied_state(result.file_path, result.backup_path, result.line_number))
            _wait_for_key()
            return len(targets)


def render_dashboard(targets: list[IssueTarget], selected: int, *, status_message: str = "") -> Layout:
    target = targets[selected]
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=5),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="code", ratio=3, minimum_size=48),
        Layout(name="right", ratio=2, minimum_size=38),
    )
    layout["right"].split_column(
        Layout(name="issues", ratio=3, minimum_size=12),
        Layout(name="fix", ratio=2, minimum_size=10),
    )

    layout["header"].update(_header(targets, selected, status_message))
    layout["code"].update(_code_panel(target))
    layout["issues"].update(_issue_feed(targets, selected))
    layout["fix"].update(_fix_panel(target))
    layout["footer"].update(_footer(target.issue))
    return layout


def _header(targets: list[IssueTarget], selected: int, status_message: str) -> Panel:
    critical = sum(1 for target in targets if target.issue.severity == "CRITICAL")
    warnings = sum(1 for target in targets if target.issue.severity == "WARNING")
    safe = sum(1 for target in targets if can_auto_apply(target.issue))
    files = len({target.file_path for target in targets})

    grid = Table.grid(expand=True)
    grid.add_column(ratio=3)
    grid.add_column(justify="right", ratio=2)

    title = Text()
    title.append("DiffSentinel", style=f"bold {TEXT}")
    title.append(" / local performance audit", style=MUTED)
    title.append("\n")
    title.append(status_message or "Reviewing current diff", style=CYAN)

    stats = Text()
    stats.append(f"ISSUE {selected + 1}/{len(targets)}", style=f"bold {TEXT}")
    stats.append(f"   FILES {files}", style=MUTED)
    stats.append(f"   CRITICAL {critical}", style=f"bold {RED}" if critical else MUTED)
    stats.append(f"   WARNING {warnings}", style=f"bold {AMBER}" if warnings else MUTED)
    stats.append(f"   SAFE FIXES {safe}", style=f"bold {GREEN}" if safe else MUTED)

    grid.add_row(title, Align.right(stats, vertical="middle"))
    return Panel(grid, box=box.HEAVY_HEAD, border_style=CYAN, style=f"on {SURFACE}")


def _code_panel(target: IssueTarget) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(width=7, justify="right", style=MUTED, no_wrap=True)
    table.add_column(width=2, justify="center", no_wrap=True)
    table.add_column(ratio=1)

    selected_line = target.issue.line_number
    for line in _parse_excerpt(target.excerpt):
        line_style = ""
        marker_style = MUTED
        marker = ""
        if line.changed:
            marker = "+"
            marker_style = AMBER
            line_style = f"bold {TEXT}"
        if line.number == selected_line:
            marker = ">"
            marker_style = TEXT
            line_style = f"bold {TEXT} on #5a1e24"

        table.add_row(
            str(line.number),
            Text(marker, style=marker_style),
            Text(line.text, style=line_style),
        )

    return Panel(
        table,
        title=f"[bold {CYAN}]Changed Code[/bold {CYAN}] [dim]{target.file_path}[/dim]",
        subtitle="[dim]Only changed hunks and nearby context are sent for review[/dim]",
        border_style=CYAN,
        box=box.ROUNDED,
        padding=(1, 1),
    )


def _issue_feed(targets: list[IssueTarget], selected: int) -> Panel:
    feed = Table.grid(expand=True)
    feed.add_column(ratio=1)

    for index, target in enumerate(targets):
        issue = target.issue
        selected_issue = index == selected
        severity_style = RED if issue.severity == "CRITICAL" else AMBER
        border = severity_style if selected_issue else MUTED
        mode = "SAFE APPLY" if can_auto_apply(issue) else "MANUAL REVIEW"
        mode_style = GREEN if can_auto_apply(issue) else AMBER

        card = Table.grid(expand=True)
        card.add_column(ratio=1)
        heading = Text()
        heading.append(f"{index + 1:02d} ", style=MUTED)
        heading.append(issue.severity, style=f"bold {severity_style}")
        heading.append(f"  {issue.category}", style=f"bold {TEXT}")
        heading.append(f"  line {issue.line_number}", style=MUTED)
        card.add_row(heading)
        card.add_row(Text(issue.explanation, style=TEXT))
        card.add_row(Text(issue.impact, style=MUTED))
        card.add_row(Text(mode, style=f"bold {mode_style}"))

        feed.add_row(
            Panel(
                card,
                border_style=border,
                box=box.ROUNDED if selected_issue else box.SQUARE,
                padding=(0, 1),
            )
        )

    return Panel(
        feed,
        title=f"[bold {TEXT}]Issue Feed[/bold {TEXT}]",
        border_style=MUTED,
        box=box.ROUNDED,
        padding=(1, 1),
    )


def _fix_panel(target: IssueTarget) -> Panel:
    issue = target.issue
    safe = can_auto_apply(issue)
    mode = "Safe single-line replacement" if safe else "Manual review only"
    mode_style = GREEN if safe else AMBER
    syntax = Syntax(issue.optimized_code, "python", theme="monokai", word_wrap=True)

    detail = Table.grid(expand=True)
    detail.add_column(ratio=1)
    detail.add_row(Text(mode, style=f"bold {mode_style}"))
    detail.add_row(Text(f"Confidence: {issue.confidence:.2f}", style=MUTED))
    detail.add_row(syntax)

    return Panel(
        detail,
        title=f"[bold {GREEN if safe else AMBER}]Fix Preview[/bold {GREEN if safe else AMBER}]",
        border_style=GREEN if safe else AMBER,
        box=box.ROUNDED,
        padding=(1, 1),
    )


def _footer(issue: Issue) -> Panel:
    apply_label = "[A] apply safe fix" if can_auto_apply(issue) else "[A] disabled"
    text = Text()
    text.append(apply_label, style=f"bold {GREEN if can_auto_apply(issue) else MUTED}")
    text.append("    [Up/Down] navigate", style=TEXT)
    text.append("    [Q] quit", style=TEXT)
    text.append("    Backup + atomic write are always used", style=MUTED)
    return Panel(Align.center(text, vertical="middle"), box=box.SQUARE, border_style=MUTED, style=f"on {SURFACE}")


def _empty_state() -> Panel:
    text = Text()
    text.append("No performance regressions found\n", style=f"bold {GREEN}")
    text.append("DiffSentinel reviewed the current diff and found no high-confidence issues.", style=TEXT)
    return Panel(text, title=f"[bold {GREEN}]Clean Diff[/bold {GREEN}]", border_style=GREEN, box=box.ROUNDED)


def _applied_state(file_path: object, backup_path: object, line_number: int) -> Panel:
    text = Text()
    text.append("Safe fix applied\n", style=f"bold {GREEN}")
    text.append(f"File: {file_path}\n", style=TEXT)
    text.append(f"Line: {line_number}\n", style=TEXT)
    text.append(f"Backup: {backup_path}\n", style=MUTED)
    text.append("Press any key to close.", style=MUTED)
    return Panel(text, title=f"[bold {GREEN}]Fix Applied[/bold {GREEN}]", border_style=GREEN, box=box.ROUNDED)


def _print_noninteractive(console: Console, targets: list[IssueTarget]) -> None:
    table = Table(
        title="DiffSentinel Findings",
        box=box.SIMPLE_HEAVY,
        header_style=f"bold {TEXT}",
        border_style=MUTED,
        expand=True,
    )
    table.add_column("Severity", no_wrap=True)
    table.add_column("Location", no_wrap=True)
    table.add_column("Mode", no_wrap=True)
    table.add_column("Finding")
    table.add_column("Suggested Fix")

    for target in targets:
        issue = target.issue
        severity_style = RED if issue.severity == "CRITICAL" else AMBER
        mode = "safe" if can_auto_apply(issue) else "manual"
        mode_style = GREEN if can_auto_apply(issue) else AMBER
        table.add_row(
            Text(issue.severity, style=f"bold {severity_style}"),
            f"{target.file_path}:{issue.line_number}",
            Text(mode, style=f"bold {mode_style}"),
            f"{issue.explanation} Impact: {issue.impact}",
            issue.optimized_code,
        )

    console.print(table)


@dataclass(frozen=True)
class ExcerptLine:
    number: int
    text: str
    changed: bool


def _parse_excerpt(excerpt: str) -> list[ExcerptLine]:
    lines: list[ExcerptLine] = []
    for raw_line in excerpt.splitlines():
        match = re.match(r"\s*(\d+)([ *]) (.*)", raw_line)
        if not match:
            continue
        lines.append(
            ExcerptLine(
                number=int(match.group(1)),
                changed=match.group(2) == "*",
                text=match.group(3),
            )
        )
    return lines


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
