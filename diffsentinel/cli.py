from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from rich.console import Console

from .agent import (
    AgentError,
    apply_safe_fixes,
    build_agent_report,
    collect_changed_findings,
    collect_project_findings,
    interactive_outcome_json,
    outcome_json,
    print_fix_plan,
    report_json,
    restore_run,
    run_interactive_agent,
)
from .analyzer import analyze_chunk
from .demo import run_agent_demo, run_demo
from .diff import DiffError, get_diff_chunks
from .hooks import HookError, install_pre_commit_hook, uninstall_pre_commit_hook
from .onboarding import checks_json, initialize_project, print_doctor, print_init_result, run_doctor
from .patcher import PatchError, apply_issue
from .rules import can_auto_apply
from .sarif import sarif_json
from .scanner import ProjectScan, scan_project
from .schema import Issue
from .settings import DEFAULT_OPENAI_MODEL, DEFAULT_REASONING_EFFORT, VALID_REASONING_EFFORTS, load_settings
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
    if args.command == "init":
        return run_init(args)
    if args.command == "doctor":
        return run_doctor_command(args)
    if args.command == "check":
        return run_check(args)
    if args.command == "scan":
        return run_scan(args)
    if args.command == "guard":
        return run_guard(args)
    if args.command == "agent":
        return run_agent(args)
    if args.command == "fix-plan":
        return run_fix_plan(args)
    if args.command == "apply-safe":
        return run_apply_safe(args)
    if args.command == "restore":
        return run_restore(args)
    if args.command == "demo":
        return run_demo_command(args)
    if args.command == "demo-agent":
        return run_demo_agent_command(args)
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
    init = subparsers.add_parser("init", help="Onboard a project for DiffSentinel")
    init.add_argument("path", nargs="?", default=".", help="Project directory to initialize")
    init.add_argument("--force", action="store_true", help="Overwrite existing DiffSentinel files")
    init.add_argument("--model", default=DEFAULT_OPENAI_MODEL, help="Default OpenAI model for live audits")
    init.add_argument(
        "--reasoning-effort",
        default=DEFAULT_REASONING_EFFORT,
        choices=VALID_REASONING_EFFORTS,
        help="Default reasoning effort for live audits",
    )
    init.add_argument("--no-agent-docs", action="store_true", help="Do not create/update AGENTS.md")
    init.add_argument("--no-env-example", action="store_true", help="Do not create .env.example")
    init.add_argument("--no-gitignore", action="store_true", help="Do not add .env and backups to .gitignore")

    doctor = subparsers.add_parser("doctor", help="Check DiffSentinel setup for this project")
    doctor.add_argument("path", nargs="?", default=".", help="Project directory to check")
    doctor.add_argument("--json", action="store_true", help="Print diagnostics as JSON")
    doctor.add_argument("--live", action="store_true", help="Make a live OpenAI API reachability check")

    check = subparsers.add_parser("check", help="Audit the current git diff")
    check.add_argument("--staged", action="store_true", help="Analyze staged changes with git diff --cached")
    check.add_argument("--json", action="store_true", help="Print JSON instead of launching the terminal UI")
    check.add_argument("--no-tui", action="store_true", help="Print issues without interactive controls")
    check.add_argument("--apply-first", action="store_true", help="Apply the highest-confidence safe fix and exit")
    check.add_argument("--exit-on-critical", action="store_true", help="Exit 1 if any CRITICAL issue is found")
    check.add_argument("--force-cache", action="store_true", help="Skip OpenAI and use the local demo cache")
    check.add_argument("--model", help="OpenAI model to use when OPENAI_API_KEY is set")
    check.add_argument(
        "--reasoning-effort",
        choices=VALID_REASONING_EFFORTS,
        help="Reasoning effort for Responses API live analysis",
    )
    check.add_argument("--timeout", type=float, default=10.0, help="OpenAI request timeout in seconds")

    scan = subparsers.add_parser("scan", help="Audit all Python files in a project")
    scan.add_argument("path", nargs="?", default=".", help="Project directory to scan")
    scan.add_argument("--json", action="store_true", help="Print agent-friendly JSON output")
    scan.add_argument("--no-tui", action="store_true", help="Print a non-interactive findings table")
    scan.add_argument("--exit-on-critical", action="store_true", help="Exit 1 if any CRITICAL issue is found")
    scan.add_argument("--live", action="store_true", default=None, help="Use OpenAI analysis when OPENAI_API_KEY is set")
    scan.add_argument("--model", help="OpenAI model to use with --live")
    scan.add_argument(
        "--reasoning-effort",
        choices=VALID_REASONING_EFFORTS,
        help="Reasoning effort for Responses API live analysis",
    )
    scan.add_argument("--timeout", type=float, default=10.0, help="OpenAI request timeout in seconds")
    scan.add_argument("--max-files", type=int, help="Maximum Python files to scan")
    scan.add_argument("--exclude-tests", action="store_true", default=None, help="Skip files under test/tests directories")

    guard = subparsers.add_parser("guard", help="Agent-facing guardrail for changed code or whole projects")
    _add_agent_scope_args(guard)
    guard.add_argument("--json", action="store_true", help="Print the v2 agent JSON report")
    guard.add_argument("--sarif", action="store_true", help="Print SARIF 2.1.0 for code scanning")
    guard.add_argument("--apply-safe", action="store_true", help="Apply all high-confidence safe fixes before reporting")
    guard.add_argument("--fail-on-critical", action="store_true", help="Exit 1 when CRITICAL issues are present")

    agent = subparsers.add_parser("agent", help="Interactive DiffSentinel coding-agent companion")
    _add_agent_scope_args(agent)
    agent.add_argument("--yes", action="store_true", help="Apply safe fixes without prompting")
    agent.add_argument("--dry-run", action="store_true", help="Preview safe fixes without writing files")
    agent.add_argument("--json", action="store_true", help="Print the interaction outcome as JSON")
    agent.add_argument("--no-rerun", action="store_true", help="Do not rerun guard after applying safe fixes")
    agent.add_argument("--fail-on-critical", action="store_true", help="Exit 1 if final report still has CRITICAL issues")

    fix_plan = subparsers.add_parser("fix-plan", help="Show safe fixes and manual-review items")
    _add_agent_scope_args(fix_plan)
    fix_plan.add_argument("--json", action="store_true", help="Print the v2 agent JSON report")
    fix_plan.add_argument("--sarif", action="store_true", help="Print SARIF 2.1.0 for code scanning")

    apply_safe = subparsers.add_parser("apply-safe", help="Apply all high-confidence safe fixes")
    _add_agent_scope_args(apply_safe)
    apply_safe.add_argument("--dry-run", action="store_true", help="Preview safe fixes without writing files")
    apply_safe.add_argument("--json", action="store_true", help="Print apply outcome as JSON")

    restore = subparsers.add_parser("restore", help="Restore files from a DiffSentinel safe-apply run")
    restore.add_argument("path", nargs="?", default=".", help="Project root containing .diffsentinel/runs")
    restore.add_argument("--run-id", help="Run id to restore; defaults to latest")
    restore.add_argument("--json", action="store_true", help="Print restore outcome as JSON")

    demo = subparsers.add_parser("demo", help="Run a self-contained DiffSentinel demo")
    demo.add_argument("--path", help="Optional empty directory to use for the demo repo")
    demo.add_argument("--no-apply", action="store_true", help="Show the finding without applying the safe fix")

    demo_agent = subparsers.add_parser("demo-agent", help="Run the full coding-agent guardrail demo")
    demo_agent.add_argument("--path", help="Optional empty directory to use for the demo repo")
    demo_agent.add_argument("--keep-fixed", action="store_true", help="Do not restore the original regression at the end")

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


def _add_agent_scope_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", default=".", help="Project directory")
    parser.add_argument("--changed", action="store_true", help="Audit current git diff; default unless --project is used")
    parser.add_argument("--project", action="store_true", help="Audit the whole project")
    parser.add_argument("--staged", action="store_true", help="Use staged changes for --changed mode")
    parser.add_argument("--live", action="store_true", help="Use OpenAI analysis when OPENAI_API_KEY is set")
    parser.add_argument("--model", help="OpenAI model to use with --live")
    parser.add_argument(
        "--reasoning-effort",
        choices=VALID_REASONING_EFFORTS,
        help="Reasoning effort for Responses API live analysis",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="OpenAI request timeout in seconds")
    parser.add_argument("--max-files", type=int, help="Maximum Python files to scan in --project mode")
    parser.add_argument("--exclude-tests", action="store_true", default=None, help="Skip tests in --project mode")


def run_init(args: argparse.Namespace) -> int:
    console = Console()
    result = initialize_project(
        args.path,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        force=args.force,
        agent_docs=not args.no_agent_docs,
        env_example=not args.no_env_example,
        gitignore=not args.no_gitignore,
    )
    print_init_result(result, console)
    return 0


def run_doctor_command(args: argparse.Namespace) -> int:
    checks = run_doctor(args.path, live=args.live)
    if args.json:
        print(checks_json(checks))
    else:
        print_doctor(checks, Console())
    return 1 if any(check.status == "error" for check in checks) else 0


def run_check(args: argparse.Namespace) -> int:
    console = Console()
    settings = load_settings()
    model = args.model or settings.openai_model
    reasoning_effort = args.reasoning_effort or settings.reasoning_effort
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
            model=model,
            timeout=args.timeout,
            force_cache=args.force_cache,
            reasoning_effort=reasoning_effort,
            enabled_rules=settings.rules,
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
    settings = load_settings(args.path)
    max_files = args.max_files if args.max_files is not None else settings.scan_max_files
    exclude_tests = args.exclude_tests if args.exclude_tests is not None else settings.scan_exclude_tests
    live = args.live if args.live is not None else settings.scan_live
    model = args.model or settings.openai_model
    reasoning_effort = args.reasoning_effort or settings.reasoning_effort
    try:
        scan = scan_project(
            args.path,
            max_files=max_files,
            include_tests=not exclude_tests,
            ignore_paths=settings.ignore_paths,
        )
    except (FileNotFoundError, NotADirectoryError, OSError) as exc:
        console.print(f"[bold red]DiffSentinel scan failed:[/bold red] {exc}")
        return 2

    records: list[IssueRecord] = []
    for chunk in scan.chunks:
        result = analyze_chunk(
            chunk,
            model=model,
            timeout=args.timeout,
            force_cache=not live,
            reasoning_effort=reasoning_effort,
            enabled_rules=settings.rules,
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


def run_guard(args: argparse.Namespace) -> int:
    console = Console()
    try:
        finding_set = _collect_agent_findings(args)
        applied = apply_safe_fixes(finding_set.findings, root=finding_set.root) if args.apply_safe else None
    except AgentError as exc:
        console.print(f"[bold red]DiffSentinel guard failed:[/bold red] {exc}")
        return 2
    report = build_agent_report(finding_set, fail_on_critical=args.fail_on_critical, applied=applied)
    if args.sarif:
        print(sarif_json(report))
    elif args.json:
        print(report_json(report))
    else:
        print_fix_plan(report, console)
    return int(report["exit_policy"]["exit_code"])


def run_agent(args: argparse.Namespace) -> int:
    console = Console()
    try:
        finding_set = _collect_agent_findings(args)
        settings = load_settings(args.path)
        model = args.model or settings.openai_model
        reasoning_effort = args.reasoning_effort or settings.reasoning_effort
        outcome = run_interactive_agent(
            finding_set,
            console=console,
            auto_yes=args.yes,
            quiet=args.json,
            dry_run=args.dry_run,
            fail_on_critical=args.fail_on_critical,
            rerun=not args.no_rerun,
            live=args.live,
            model=model,
            timeout=args.timeout,
            reasoning_effort=reasoning_effort,
            enabled_rules=settings.rules,
        )
    except AgentError as exc:
        console.print(f"[bold red]DiffSentinel agent failed:[/bold red] {exc}")
        return 2
    if args.json:
        print(interactive_outcome_json(outcome))
    return int(outcome.final_report["exit_policy"]["exit_code"])


def run_fix_plan(args: argparse.Namespace) -> int:
    console = Console()
    try:
        finding_set = _collect_agent_findings(args)
    except AgentError as exc:
        console.print(f"[bold red]DiffSentinel fix-plan failed:[/bold red] {exc}")
        return 2
    report = build_agent_report(finding_set, fail_on_critical=False)
    if args.sarif:
        print(sarif_json(report))
    elif args.json:
        print(report_json(report))
    else:
        print_fix_plan(report, console)
    return 0


def run_apply_safe(args: argparse.Namespace) -> int:
    console = Console()
    try:
        finding_set = _collect_agent_findings(args)
        outcome = apply_safe_fixes(finding_set.findings, root=finding_set.root, dry_run=args.dry_run)
    except AgentError as exc:
        console.print(f"[bold red]DiffSentinel apply-safe failed:[/bold red] {exc}")
        return 2
    if args.json:
        print(outcome_json(outcome))
    else:
        console.print(
            f"[bold green]{'Would apply' if args.dry_run else 'Applied'} {len(outcome.applied)} safe fixes[/bold green] "
            f"(run: {outcome.run_id}, metadata: {outcome.metadata_path})"
        )
        if outcome.skipped:
            console.print(f"[bold yellow]Skipped {len(outcome.skipped)} findings[/bold yellow]")
    return 0


def run_restore(args: argparse.Namespace) -> int:
    console = Console()
    try:
        outcome = restore_run(root=args.path, run_id=args.run_id)
    except AgentError as exc:
        console.print(f"[bold red]DiffSentinel restore failed:[/bold red] {exc}")
        return 2
    if args.json:
        print(outcome_json(outcome))
    else:
        console.print(f"[bold green]Restored {len(outcome.restored)} files[/bold green] from run {outcome.run_id}")
        if outcome.skipped:
            console.print(f"[bold yellow]Skipped {len(outcome.skipped)} files[/bold yellow]")
    return 0


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


def run_demo_agent_command(args: argparse.Namespace) -> int:
    console = Console()
    try:
        run_agent_demo(
            path=Path(args.path) if args.path else None,
            restore_after=not args.keep_fixed,
            console=console,
        )
    except Exception as exc:
        console.print(f"[bold red]DiffSentinel agent demo failed:[/bold red] {exc}")
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


def _collect_agent_findings(args: argparse.Namespace):
    settings = load_settings(args.path)
    model = args.model or settings.openai_model
    reasoning_effort = args.reasoning_effort or settings.reasoning_effort
    if args.project:
        max_files = args.max_files if args.max_files is not None else settings.scan_max_files
        exclude_tests = args.exclude_tests if args.exclude_tests is not None else settings.scan_exclude_tests
        return collect_project_findings(
            path=args.path,
            live=args.live,
            model=model,
            timeout=args.timeout,
            reasoning_effort=reasoning_effort,
            max_files=max_files,
            exclude_tests=exclude_tests,
            ignore_paths=settings.ignore_paths,
            enabled_rules=settings.rules,
        )
    return collect_changed_findings(
        cwd=args.path,
        staged=args.staged,
        live=args.live,
        model=model,
        timeout=args.timeout,
        reasoning_effort=reasoning_effort,
        enabled_rules=settings.rules,
    )


if __name__ == "__main__":
    raise SystemExit(main())
