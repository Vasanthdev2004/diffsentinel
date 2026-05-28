from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .analyzer import analyze_chunk
from .diff import DiffError, get_diff_chunks
from .hooks import HookError, find_git_root
from .rules import can_auto_apply
from .scanner import ProjectScan, scan_project
from .schema import Issue


AGENT_SCHEMA_VERSION = "diffsentinel.agent.v2"


@dataclass(frozen=True)
class Finding:
    file_path: str
    issue: Issue
    excerpt: str
    apply_path: str | None = None

    @property
    def id(self) -> str:
        return f"{self.file_path}:{self.issue.line_number}:{self.issue.category}"


@dataclass(frozen=True)
class FindingSet:
    scope: str
    findings: list[Finding]
    root: Path
    files_scanned: int | None = None
    files_skipped: int | None = None


@dataclass(frozen=True)
class ApplyOutcome:
    run_id: str
    metadata_path: Path
    applied: list[dict[str, Any]]
    skipped: list[dict[str, Any]]


@dataclass(frozen=True)
class RestoreOutcome:
    run_id: str
    restored: list[dict[str, Any]]
    skipped: list[dict[str, Any]]


@dataclass(frozen=True)
class InteractiveAgentOutcome:
    first_report: dict[str, Any]
    final_report: dict[str, Any]
    applied: ApplyOutcome | None


class AgentError(RuntimeError):
    """Raised when an agent-facing operation cannot complete."""


def collect_changed_findings(
    *,
    cwd: str | Path = ".",
    staged: bool = False,
    live: bool = False,
    model: str,
    timeout: float,
    reasoning_effort: str,
    enabled_rules: dict[str, bool] | None = None,
) -> FindingSet:
    try:
        git_root = find_git_root(cwd)
        chunks = get_diff_chunks(staged=staged, cwd=git_root)
    except (HookError, DiffError) as exc:
        raise AgentError(str(exc)) from exc

    findings: list[Finding] = []
    for chunk in chunks:
        result = analyze_chunk(
            chunk,
            model=model,
            timeout=timeout,
            force_cache=not live,
            reasoning_effort=reasoning_effort,
            enabled_rules=enabled_rules,
        )
        absolute_file = str((git_root / chunk.filepath).resolve())
        findings.extend(
            Finding(
                file_path=chunk.filepath,
                apply_path=absolute_file,
                issue=issue,
                excerpt=chunk.code_excerpt,
            )
            for issue in result.issues
        )
    return FindingSet(scope="changed", findings=findings, root=git_root)


def collect_project_findings(
    *,
    path: str | Path = ".",
    live: bool = False,
    model: str,
    timeout: float,
    reasoning_effort: str,
    max_files: int,
    exclude_tests: bool,
    ignore_paths: tuple[str, ...] = (),
    enabled_rules: dict[str, bool] | None = None,
) -> FindingSet:
    scan = scan_project(path, max_files=max_files, include_tests=not exclude_tests, ignore_paths=ignore_paths)
    findings: list[Finding] = []
    for chunk in scan.chunks:
        result = analyze_chunk(
            chunk,
            model=model,
            timeout=timeout,
            force_cache=not live,
            reasoning_effort=reasoning_effort,
            enabled_rules=enabled_rules,
        )
        absolute_file = str((scan.root / chunk.filepath).resolve())
        findings.extend(
            Finding(
                file_path=chunk.filepath,
                apply_path=absolute_file,
                issue=issue,
                excerpt=chunk.code_excerpt,
            )
            for issue in result.issues
        )
    return _from_scan(scan, findings)


def build_agent_report(
    finding_set: FindingSet,
    *,
    fail_on_critical: bool,
    applied: ApplyOutcome | None = None,
) -> dict[str, Any]:
    findings = finding_set.findings
    safe = [finding for finding in findings if can_auto_apply(finding.issue)]
    manual = [finding for finding in findings if not can_auto_apply(finding.issue)]
    critical = [finding for finding in findings if finding.issue.severity == "CRITICAL"]
    exit_code = 1 if fail_on_critical and critical else 0

    return {
        "schema_version": AGENT_SCHEMA_VERSION,
        "scope": finding_set.scope,
        "summary": _summary(finding_set),
        "issues": [_finding_dict(finding) for finding in findings],
        "safe_fixes": [_fix_dict(finding) for finding in safe],
        "manual_review": [_manual_dict(finding) for finding in manual],
        "blocked_reason": "critical_issues_found" if critical else None,
        "next_action": _next_action(findings, safe, manual, critical),
        "exit_policy": {
            "fail_on_critical": fail_on_critical,
            "exit_code": exit_code,
        },
        "applied": _apply_outcome_dict(applied) if applied else None,
    }


def report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2)


def print_fix_plan(report: dict[str, Any], console: Console) -> None:
    summary = report["summary"]
    console.print(
        f"[bold cyan]DiffSentinel fix plan[/bold cyan] "
        f"{summary['issues']} issues, {summary['safe_fixes']} safe fixes, "
        f"{summary['manual_review']} manual review"
    )
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Mode", no_wrap=True)
    table.add_column("Location", no_wrap=True)
    table.add_column("Severity", no_wrap=True)
    table.add_column("Fix")

    for item in report["safe_fixes"]:
        table.add_row("safe", f"{item['file_path']}:{item['line_number']}", item["severity"], item["optimized_code"])
    for item in report["manual_review"]:
        table.add_row("manual", f"{item['file_path']}:{item['line_number']}", item["severity"], item["reason"])
    console.print(table)
    console.print(f"Next action: [bold]{report['next_action']}[/bold]")


def run_interactive_agent(
    finding_set: FindingSet,
    *,
    console: Console,
    auto_yes: bool = False,
    quiet: bool = False,
    fail_on_critical: bool = True,
    rerun: bool = True,
    live: bool = False,
    model: str,
    timeout: float,
    reasoning_effort: str,
    enabled_rules: dict[str, bool] | None = None,
) -> InteractiveAgentOutcome:
    if not quiet:
        console.print(Panel("DiffSentinel Agent", subtitle="inspect -> plan -> apply -> verify", border_style="cyan"))
        console.print(f"[dim]Scope:[/dim] {finding_set.scope}    [dim]Root:[/dim] {finding_set.root}")
    first_report = build_agent_report(finding_set, fail_on_critical=fail_on_critical)
    if not quiet:
        print_fix_plan(first_report, console)

    safe_count = len(first_report["safe_fixes"])
    if safe_count == 0:
        if not quiet:
            console.print("[bold green]No safe fixes to apply.[/bold green]")
        return InteractiveAgentOutcome(first_report=first_report, final_report=first_report, applied=None)

    if not auto_yes and not _confirm(console, f"Apply {safe_count} safe fixes?"):
        if not quiet:
            console.print("[bold yellow]No changes applied.[/bold yellow]")
        return InteractiveAgentOutcome(first_report=first_report, final_report=first_report, applied=None)

    if not quiet:
        console.print("[bold cyan]Applying safe fixes...[/bold cyan]")
    applied = apply_safe_fixes(finding_set.findings, root=finding_set.root)
    if not quiet:
        console.print(
            f"[bold green]Applied {len(applied.applied)} safe fixes[/bold green] "
            f"(run: {applied.run_id})"
        )

    if not rerun:
        final_report = build_agent_report(finding_set, fail_on_critical=fail_on_critical, applied=applied)
        return InteractiveAgentOutcome(first_report=first_report, final_report=final_report, applied=applied)

    if not quiet:
        console.print("[bold cyan]Rerunning guard...[/bold cyan]")
    final_set = _rerun_finding_set(
        finding_set,
        live=live,
        model=model,
        timeout=timeout,
        reasoning_effort=reasoning_effort,
        enabled_rules=enabled_rules,
    )
    final_report = build_agent_report(final_set, fail_on_critical=fail_on_critical, applied=applied)
    if not quiet:
        _print_final_status(final_report, console)
    return InteractiveAgentOutcome(first_report=first_report, final_report=final_report, applied=applied)


def apply_safe_fixes(findings: list[Finding], *, root: str | Path = ".") -> ApplyOutcome:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root_path = Path(root).resolve()
    runs_dir = root_path / ".diffsentinel" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    grouped: dict[Path, list[Finding]] = {}
    seen: set[tuple[str, int]] = set()
    for finding in findings:
        target = Path(finding.apply_path or finding.file_path).resolve()
        key = (str(target), finding.issue.line_number)
        if key in seen:
            skipped.append({"id": finding.id, "reason": "duplicate_line"})
            continue
        seen.add(key)
        if not can_auto_apply(finding.issue):
            skipped.append({"id": finding.id, "reason": "manual_review_required"})
            continue
        grouped.setdefault(target, []).append(finding)

    for target, target_findings in grouped.items():
        try:
            file_applied = _apply_file_fixes(target, target_findings, run_id)
        except Exception as exc:
            skipped.extend({"id": finding.id, "reason": str(exc)} for finding in target_findings)
            continue
        applied.extend(file_applied)

    metadata = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "applied": applied,
        "skipped": skipped,
    }
    metadata_path = runs_dir / f"{run_id}.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (runs_dir / "latest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return ApplyOutcome(run_id=run_id, metadata_path=metadata_path, applied=applied, skipped=skipped)


def restore_run(*, root: str | Path = ".", run_id: str | None = None) -> RestoreOutcome:
    root_path = Path(root).resolve()
    runs_dir = root_path / ".diffsentinel" / "runs"
    metadata_path = runs_dir / (f"{run_id}.json" if run_id else "latest.json")
    if not metadata_path.exists():
        raise AgentError(f"No DiffSentinel run metadata found at {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    actual_run_id = str(metadata.get("run_id", run_id or "latest"))
    restored: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    restored_files: set[str] = set()
    for item in metadata.get("applied", []):
        file_path = str(item["absolute_path"])
        if file_path in restored_files:
            continue
        backup_path = Path(item["backup_path"])
        target = Path(file_path)
        if not backup_path.exists():
            skipped.append({"file_path": file_path, "reason": "backup_missing"})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, target)
        restored_files.add(file_path)
        restored.append({"file_path": file_path, "backup_path": str(backup_path)})

    return RestoreOutcome(run_id=actual_run_id, restored=restored, skipped=skipped)


def outcome_json(outcome: ApplyOutcome | RestoreOutcome) -> str:
    return json.dumps(outcome.__dict__, default=str, indent=2)


def interactive_outcome_json(outcome: InteractiveAgentOutcome) -> str:
    return json.dumps(
        {
            "first_report": outcome.first_report,
            "final_report": outcome.final_report,
            "applied": _apply_outcome_dict(outcome.applied) if outcome.applied else None,
        },
        indent=2,
    )


def _from_scan(scan: ProjectScan, findings: list[Finding]) -> FindingSet:
    return FindingSet(
        scope="project",
        findings=findings,
        root=scan.root,
        files_scanned=scan.files_scanned,
        files_skipped=scan.files_skipped,
    )


def _summary(finding_set: FindingSet) -> dict[str, int | str]:
    findings = finding_set.findings
    summary: dict[str, int | str] = {
        "issues": len(findings),
        "critical": sum(1 for finding in findings if finding.issue.severity == "CRITICAL"),
        "warnings": sum(1 for finding in findings if finding.issue.severity == "WARNING"),
        "safe_fixes": sum(1 for finding in findings if can_auto_apply(finding.issue)),
        "manual_review": sum(1 for finding in findings if not can_auto_apply(finding.issue)),
    }
    if finding_set.files_scanned is not None:
        summary["files_scanned"] = finding_set.files_scanned
    if finding_set.files_skipped is not None:
        summary["files_skipped"] = finding_set.files_skipped
    return summary


def _finding_dict(finding: Finding) -> dict[str, Any]:
    return {
        "id": finding.id,
        "file_path": finding.file_path,
        **({"absolute_path": finding.apply_path} if finding.apply_path else {}),
        "auto_applyable": can_auto_apply(finding.issue),
        **finding.issue.model_dump(),
    }


def _fix_dict(finding: Finding) -> dict[str, Any]:
    issue = finding.issue
    return {
        "id": finding.id,
        "file_path": finding.file_path,
        **({"absolute_path": finding.apply_path} if finding.apply_path else {}),
        "line_number": issue.line_number,
        "severity": issue.severity,
        "category": issue.category,
        "optimized_code": issue.optimized_code,
        "confidence": issue.confidence,
    }


def _manual_dict(finding: Finding) -> dict[str, Any]:
    issue = finding.issue
    return {
        "id": finding.id,
        "file_path": finding.file_path,
        **({"absolute_path": finding.apply_path} if finding.apply_path else {}),
        "line_number": issue.line_number,
        "severity": issue.severity,
        "category": issue.category,
        "reason": "manual_review_required",
        "explanation": issue.explanation,
        "impact": issue.impact,
    }


def _next_action(findings: list[Finding], safe: list[Finding], manual: list[Finding], critical: list[Finding]) -> str:
    if not findings:
        return "continue"
    if critical and safe:
        return "apply_safe_fixes_then_rerun"
    if critical:
        return "manual_review_required"
    if safe:
        return "apply_safe_fixes"
    if manual:
        return "review_warnings"
    return "continue"


def _apply_outcome_dict(outcome: ApplyOutcome) -> dict[str, Any]:
    return {
        "run_id": outcome.run_id,
        "metadata_path": str(outcome.metadata_path),
        "applied": outcome.applied,
        "skipped": outcome.skipped,
    }


def _apply_file_fixes(target: Path, findings: list[Finding], run_id: str) -> list[dict[str, Any]]:
    if not target.exists():
        raise AgentError(f"File does not exist: {target}")

    original = target.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    backup_path = target.with_name(f"{target.name}.diffsentinel.{run_id}.bak")
    shutil.copy2(target, backup_path)

    for finding in sorted(findings, key=lambda item: item.issue.line_number, reverse=True):
        index = finding.issue.line_number - 1
        if index < 0 or index >= len(lines):
            raise AgentError(f"Line {finding.issue.line_number} is outside {target}")
        newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
        lines[index] = finding.issue.optimized_code + newline

    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write("".join(lines))
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

    return [
        {
            "id": finding.id,
            "file_path": finding.file_path,
            "absolute_path": str(target),
            "backup_path": str(backup_path),
            "line_number": finding.issue.line_number,
            "category": finding.issue.category,
            "optimized_code": finding.issue.optimized_code,
        }
        for finding in findings
    ]


def _confirm(console: Console, prompt: str) -> bool:
    response = console.input(f"[bold yellow]{prompt}[/bold yellow] [Y/n] ").strip().lower()
    return response in {"", "y", "yes"}


def _rerun_finding_set(
    finding_set: FindingSet,
    *,
    live: bool,
    model: str,
    timeout: float,
    reasoning_effort: str,
    enabled_rules: dict[str, bool] | None,
) -> FindingSet:
    if finding_set.scope == "project":
        return collect_project_findings(
            path=finding_set.root,
            live=live,
            model=model,
            timeout=timeout,
            reasoning_effort=reasoning_effort,
            max_files=finding_set.files_scanned or 500,
            exclude_tests=False,
            ignore_paths=(),
            enabled_rules=enabled_rules,
        )
    return collect_changed_findings(
        cwd=finding_set.root,
        live=live,
        model=model,
        timeout=timeout,
        reasoning_effort=reasoning_effort,
        enabled_rules=enabled_rules,
    )


def _print_final_status(report: dict[str, Any], console: Console) -> None:
    summary = report["summary"]
    if summary["critical"] == 0:
        console.print("[bold green]Clean. You can continue or commit.[/bold green]")
        return
    console.print(
        f"[bold red]Still blocked:[/bold red] {summary['critical']} critical issues remain. "
        f"Next action: {report['next_action']}"
    )
