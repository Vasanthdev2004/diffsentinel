from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .agent import build_agent_report, collect_changed_findings
from .settings import DiffSentinelSettings


WATERMARK = "\n\n---\nReviewed by DiffSentinel"


@dataclass(frozen=True)
class GitHubReviewOutcome:
    pr_number: int
    action: str
    acted: bool
    report_path: Path
    body: str
    critical: int
    warnings: int
    manual_review: int


class GitHubReviewError(RuntimeError):
    """Raised when GitHub PR review automation cannot complete."""


Runner = Callable[..., subprocess.CompletedProcess]


def review_pull_request(
    pr_number: int,
    *,
    root: str | Path = ".",
    settings: DiffSentinelSettings,
    act: bool = False,
    comment_only: bool = False,
    strict: bool = False,
    live: bool = False,
    runner: Runner = subprocess.run,
) -> GitHubReviewOutcome:
    repo_root = Path(root).resolve()
    _run_gh(["gh", "pr", "checkout", str(pr_number)], cwd=repo_root, runner=runner)
    finding_set = collect_changed_findings(
        cwd=repo_root,
        live=live,
        model=settings.openai_model,
        timeout=10.0,
        reasoning_effort=settings.reasoning_effort,
        enabled_rules=settings.rules,
    )
    report = build_agent_report(finding_set, fail_on_critical=True)
    action = _decide_action(report, comment_only=comment_only, strict=strict)
    body = _review_body(report, action=action) + WATERMARK
    report_path = _write_review_body(repo_root, pr_number, body)
    if act:
        _post_review(pr_number, action=action, body_path=report_path, runner=runner, cwd=repo_root)
    summary = report["summary"]
    return GitHubReviewOutcome(
        pr_number=pr_number,
        action=action,
        acted=act,
        report_path=report_path,
        body=body,
        critical=int(summary["critical"]),
        warnings=int(summary["warnings"]),
        manual_review=int(summary["manual_review"]),
    )


def outcome_json(outcome: GitHubReviewOutcome) -> str:
    return json.dumps(
        {
            "pr_number": outcome.pr_number,
            "action": outcome.action,
            "acted": outcome.acted,
            "report_path": str(outcome.report_path),
            "critical": outcome.critical,
            "warnings": outcome.warnings,
            "manual_review": outcome.manual_review,
        },
        indent=2,
    )


def _decide_action(report: dict, *, comment_only: bool, strict: bool) -> str:
    summary = report["summary"]
    if comment_only:
        return "comment"
    if summary["critical"] > 0:
        return "request-changes"
    if strict and summary["manual_review"] > 0:
        return "request-changes"
    if summary["manual_review"] > 0 or summary["warnings"] > 0:
        return "comment"
    return "approve"


def _review_body(report: dict, *, action: str) -> str:
    summary = report["summary"]
    lines = [
        "# DiffSentinel PR Review",
        "",
        f"Decision: **{action}**",
        "",
        "## Summary",
        "",
        f"- Issues: {summary['issues']}",
        f"- Critical: {summary['critical']}",
        f"- Warnings: {summary['warnings']}",
        f"- Safe fixes: {summary['safe_fixes']}",
        f"- Manual review: {summary['manual_review']}",
        f"- Next action: `{report['next_action']}`",
        "",
        "## Findings",
        "",
    ]
    if not report["issues"]:
        lines.append("No performance issues found.")
    for issue in report["issues"]:
        lines.extend(
            [
                f"### {issue['severity']} {issue['category']} at `{issue['file_path']}:{issue['line_number']}`",
                "",
                issue["explanation"],
                "",
                f"Impact: {issue['impact']}",
                "",
                f"Suggested fix: `{issue['optimized_code']}`" if issue["auto_applyable"] else "Manual review required.",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _write_review_body(root: Path, pr_number: int, body: str) -> Path:
    reports = root / ".diffsentinel" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / f"pr-{pr_number}-review.md"
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


def _post_review(pr_number: int, *, action: str, body_path: Path, runner: Runner, cwd: Path) -> None:
    if action == "comment":
        _run_gh(["gh", "pr", "comment", str(pr_number), "--body-file", str(body_path)], cwd=cwd, runner=runner)
        return
    event = "APPROVE" if action == "approve" else "REQUEST_CHANGES"
    _run_gh(
        ["gh", "pr", "review", str(pr_number), "--body-file", str(body_path), "--review-event", event],
        cwd=cwd,
        runner=runner,
    )


def _run_gh(args: list[str], *, cwd: Path, runner: Runner) -> subprocess.CompletedProcess:
    completed = runner(args, cwd=cwd, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise GitHubReviewError(message or f"Command failed: {' '.join(args)}")
    return completed
