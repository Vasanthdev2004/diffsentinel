from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from rich.console import Console

from .analyzer import analyze_chunk
from .diff import DiffChunk, DiffError, get_diff_chunks
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
    check.add_argument("--force-cache", action="store_true", help="Skip OpenAI and use the local demo cache")
    check.add_argument("--model", default="gpt-5-mini", help="OpenAI model to use when OPENAI_API_KEY is set")
    check.add_argument("--timeout", type=float, default=10.0, help="OpenAI request timeout in seconds")
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
        return 0

    targets = [
        IssueTarget(file_path=record.file_path, issue=record.issue, excerpt=record.excerpt)
        for record in records
    ]
    if args.no_tui:
        show_review(targets, console=console)
        return 0

    return 0 if show_review(targets, console=console) >= 0 else 1


def _json_records(records: list[IssueRecord]) -> str:
    payload = {
        "issues": [
            {
                "file_path": record.file_path,
                **record.issue.model_dump(),
            }
            for record in records
        ]
    }
    return json.dumps(payload, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
