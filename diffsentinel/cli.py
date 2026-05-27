from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from rich.console import Console

from .analyzer import analyze_chunk
from .demo import run_demo
from .diff import DiffError, get_diff_chunks
from .patcher import PatchError, apply_issue
from .rules import can_auto_apply
from .schema import Issue
from .tui import IssueTarget, show_review


@dataclass(frozen=True)
class IssueRecord:
    file_path: str
    issue: Issue
    excerpt: str


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "check":
        return run_check(args)
    if args.command == "demo":
        return run_demo_command(args)
    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="diffsentinel",
        description="Terminal-native local code change performance auditor.",
    )
    subparsers = parser.add_subparsers(dest="command")
    check = subparsers.add_parser("check", help="Audit the current git diff")
    check.add_argument("--staged", action="store_true", help="Analyze staged changes with git diff --cached")
    check.add_argument("--json", action="store_true", help="Print JSON instead of launching the terminal UI")
    check.add_argument("--no-tui", action="store_true", help="Print issues without interactive controls")
    check.add_argument("--apply-first", action="store_true", help="Apply the highest-confidence safe fix and exit")
    check.add_argument("--exit-on-critical", action="store_true", help="Exit 1 if any CRITICAL issue is found")
    check.add_argument("--force-cache", action="store_true", help="Skip OpenAI and use the local demo cache")
    check.add_argument("--model", default="gpt-5-mini", help="OpenAI model to use when OPENAI_API_KEY is set")
    check.add_argument("--timeout", type=float, default=10.0, help="OpenAI request timeout in seconds")

    demo = subparsers.add_parser("demo", help="Run a self-contained DiffSentinel demo")
    demo.add_argument("--path", help="Optional empty directory to use for the demo repo")
    demo.add_argument("--no-apply", action="store_true", help="Show the finding without applying the safe fix")
    return parser


def run_check(args: argparse.Namespace) -> int:
    console = Console()
    try:
        chunks = get_diff_chunks(staged=args.staged)
    except DiffError as exc:
        console.print(f"[bold red]DiffSentinel:[/bold red] {exc}")
        console.print("Run this inside a git repository with a changed Python file.")
        return 2

    if not chunks:
        console.print("[bold yellow]DiffSentinel:[/bold yellow] No git diff found.")
        return 0

    records: list[IssueRecord] = []
    for chunk in chunks:
        result = analyze_chunk(
            chunk,
            model=args.model,
            timeout=args.timeout,
            force_cache=args.force_cache,
        )
        records.extend(
            IssueRecord(file_path=chunk.filepath, issue=issue, excerpt=chunk.code_excerpt)
            for issue in result.issues
        )

    if args.json:
        print(_json_records(records))
        return _exit_code(records, args.exit_on_critical)

    if args.apply_first:
        _apply_first(records, console)
        return _exit_code(records, args.exit_on_critical)

    targets = [
        IssueTarget(file_path=record.file_path, issue=record.issue, excerpt=record.excerpt)
        for record in records
    ]
    if args.no_tui:
        show_review(targets, console=console)
        return _exit_code(records, args.exit_on_critical)

    show_review(targets, console=console)
    return _exit_code(records, args.exit_on_critical)


def run_demo_command(args: argparse.Namespace) -> int:
    console = Console()
    try:
        run_demo(
            path=Path(args.path) if args.path else None,
            apply_fix=not args.no_apply,
            console=console,
        )
    except Exception as exc:
        console.print(f"[bold red]DiffSentinel demo failed:[/bold red] {exc}")
        return 2
    return 0


def _json_records(records: list[IssueRecord]) -> str:
    payload = {
        "issues": [
            {
                "file_path": record.file_path,
                "auto_applyable": can_auto_apply(record.issue),
                **record.issue.model_dump(),
            }
            for record in records
        ]
    }
    return json.dumps(payload, indent=2)


def _apply_first(records: list[IssueRecord], console: Console) -> None:
    safe_records = [record for record in records if can_auto_apply(record.issue)]
    if not safe_records:
        console.print("[bold yellow]DiffSentinel:[/bold yellow] No safe auto-fix available.")
        return
    record = sorted(safe_records, key=lambda item: item.issue.confidence, reverse=True)[0]
    try:
        result = apply_issue(record.file_path, record.issue)
    except PatchError as exc:
        console.print(f"[bold red]Apply failed:[/bold red] {exc}")
        return
    console.print(
        f"[bold green]Applied[/bold green] {record.file_path}:{result.line_number} "
        f"(backup: {result.backup_path})"
    )


def _exit_code(records: list[IssueRecord], exit_on_critical: bool) -> int:
    if exit_on_critical and any(record.issue.severity == "CRITICAL" for record in records):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
