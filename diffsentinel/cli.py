from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from rich.console import Console

from .analyzer import DEFAULT_OPENAI_MODEL, DEFAULT_REASONING_EFFORT, analyze_chunk
from .demo import run_demo
from .diff import DiffError, get_diff_chunks
from .hooks import HookError, install_pre_commit_hook, uninstall_pre_commit_hook
from .patcher import PatchError, apply_issue
from .rules import can_auto_apply
from .scanner import ProjectScan, scan_project
from .schema import Issue
from .tui import IssueTarget, show_review


@dataclass(frozen=True)
class IssueRecord:
    file_path: str
    issue: Issue
    excerpt: str
    apply_path: str | None = None


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "check":
        return run_check(args)
    if args.command == "scan":
        return run_scan(args)
    if args.command == "demo":
        return run_demo_command(args)
    if args.command == "install-hook":
        return run_install_hook(args)
    if args.command == "uninstall-hook":
        return run_uninstall_hook(args)
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
    check.add_argument("--model", default=DEFAULT_OPENAI_MODEL, help="OpenAI model to use when OPENAI_API_KEY is set")
    check.add_argument(
        "--reasoning-effort",
        default=DEFAULT_REASONING_EFFORT,
        choices=["low", "medium", "high", "xhigh"],
        help="Reasoning effort for Responses API live analysis",
    )
    check.add_argument("--timeout", type=float, default=10.0, help="OpenAI request timeout in seconds")

    scan = subparsers.add_parser("scan", help="Audit all Python files in a project")
    scan.add_argument("path", nargs="?", default=".", help="Project directory to scan")
    scan.add_argument("--json", action="store_true", help="Print agent-friendly JSON output")
    scan.add_argument("--no-tui", action="store_true", help="Print a non-interactive findings table")
    scan.add_argument("--exit-on-critical", action="store_true", help="Exit 1 if any CRITICAL issue is found")
    scan.add_argument("--live", action="store_true", help="Use OpenAI analysis when OPENAI_API_KEY is set")
    scan.add_argument("--model", default=DEFAULT_OPENAI_MODEL, help="OpenAI model to use with --live")
    scan.add_argument(
        "--reasoning-effort",
        default=DEFAULT_REASONING_EFFORT,
        choices=["low", "medium", "high", "xhigh"],
        help="Reasoning effort for Responses API live analysis",
    )
    scan.add_argument("--timeout", type=float, default=10.0, help="OpenAI request timeout in seconds")
    scan.add_argument("--max-files", type=int, default=500, help="Maximum Python files to scan")
    scan.add_argument("--exclude-tests", action="store_true", help="Skip files under test/tests directories")

    demo = subparsers.add_parser("demo", help="Run a self-contained DiffSentinel demo")
    demo.add_argument("--path", help="Optional empty directory to use for the demo repo")
    demo.add_argument("--no-apply", action="store_true", help="Show the finding without applying the safe fix")

    install_hook = subparsers.add_parser("install-hook", help="Install a DiffSentinel pre-commit hook")
    install_hook.add_argument("--force", action="store_true", help="Back up and replace an existing pre-commit hook")
    install_hook.add_argument(
        "--live",
        action="store_true",
        help="Use live OpenAI analysis when OPENAI_API_KEY is set instead of local-only rules",
    )

    uninstall_hook = subparsers.add_parser("uninstall-hook", help="Remove a DiffSentinel pre-commit hook")
    uninstall_hook.add_argument(
        "--no-restore",
        action="store_true",
        help="Do not restore a hook that DiffSentinel backed up during install",
    )
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
            reasoning_effort=args.reasoning_effort,
        )
        records.extend(
            IssueRecord(file_path=chunk.filepath, issue=issue, excerpt=chunk.code_excerpt)
            for issue in result.issues
        )

    if args.json:
        print(_json_records(records, scope="diff"))
        return _exit_code(records, args.exit_on_critical)

    if args.apply_first:
        _apply_first(records, console)
        return _exit_code(records, args.exit_on_critical)

    targets = [
        IssueTarget(file_path=record.file_path, issue=record.issue, excerpt=record.excerpt)
        for record in records
    ]
    if args.no_tui:
        show_review(targets, console=console, interactive=False)
        return _exit_code(records, args.exit_on_critical)

    show_review(targets, console=console)
    return _exit_code(records, args.exit_on_critical)


def run_scan(args: argparse.Namespace) -> int:
    console = Console()
    try:
        scan = scan_project(
            args.path,
            max_files=args.max_files,
            include_tests=not args.exclude_tests,
        )
    except (FileNotFoundError, NotADirectoryError, OSError) as exc:
        console.print(f"[bold red]DiffSentinel scan failed:[/bold red] {exc}")
        return 2

    records: list[IssueRecord] = []
    for chunk in scan.chunks:
        result = analyze_chunk(
            chunk,
            model=args.model,
            timeout=args.timeout,
            force_cache=not args.live,
            reasoning_effort=args.reasoning_effort,
        )
        absolute_file = str((scan.root / chunk.filepath).resolve())
        records.extend(
            IssueRecord(
                file_path=chunk.filepath,
                apply_path=absolute_file,
                issue=issue,
                excerpt=chunk.code_excerpt,
            )
            for issue in result.issues
        )

    if args.json:
        print(_json_records(records, scope="project", scan=scan))
        return _exit_code(records, args.exit_on_critical)

    if not records:
        console.print(
            f"[bold green]DiffSentinel[/bold green] scanned {scan.files_scanned} Python files. "
            "No performance issues found."
        )
        return 0

    targets = [
        IssueTarget(
            file_path=record.file_path,
            apply_path=record.apply_path,
            issue=record.issue,
            excerpt=record.excerpt,
        )
        for record in records
    ]
    if args.no_tui:
        show_review(targets, console=console, interactive=False)
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


def run_install_hook(args: argparse.Namespace) -> int:
    console = Console()
    command = "diffsentinel check --staged --exit-on-critical --no-tui"
    if not args.live:
        command += " --force-cache"
    try:
        result = install_pre_commit_hook(command=command, force=args.force)
    except HookError as exc:
        console.print(f"[bold red]Hook install failed:[/bold red] {exc}")
        return 2
    console.print(f"[bold green]Installed[/bold green] DiffSentinel pre-commit hook: {result.hook_path}")
    if result.backup_path is not None:
        console.print(f"Backed up existing hook: {result.backup_path}")
    return 0


def run_uninstall_hook(args: argparse.Namespace) -> int:
    console = Console()
    try:
        result = uninstall_pre_commit_hook(restore_backup=not args.no_restore)
    except HookError as exc:
        console.print(f"[bold red]Hook uninstall failed:[/bold red] {exc}")
        return 2
    console.print(f"[bold green]Removed[/bold green] DiffSentinel pre-commit hook: {result.hook_path}")
    if result.backup_path is not None and not args.no_restore:
        console.print(f"Restored previous hook from: {result.backup_path}")
    return 0


def _json_records(records: list[IssueRecord], *, scope: str, scan: ProjectScan | None = None) -> str:
    payload = {
        "schema_version": "diffsentinel.agent.v1",
        "scope": scope,
        "summary": _summary(records, scan),
        "issues": [
            {
                "file_path": record.file_path,
                **({"absolute_path": record.apply_path} if record.apply_path else {}),
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
        result = apply_issue(record.apply_path or record.file_path, record.issue)
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


def _summary(records: list[IssueRecord], scan: ProjectScan | None) -> dict[str, int]:
    summary = {
        "issues": len(records),
        "critical": sum(1 for record in records if record.issue.severity == "CRITICAL"),
        "warnings": sum(1 for record in records if record.issue.severity == "WARNING"),
        "auto_applyable": sum(1 for record in records if can_auto_apply(record.issue)),
    }
    if scan is not None:
        summary["files_scanned"] = scan.files_scanned
        summary["files_skipped"] = scan.files_skipped
    return summary


if __name__ == "__main__":
    raise SystemExit(main())
