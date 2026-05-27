from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .hooks import HOOK_MARKER, HookError, find_git_root
from .settings import (
    CONFIG_NAME,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_REASONING_EFFORT,
    DiffSentinelSettings,
    default_config_text,
    load_settings,
)


AGENT_START = "<!-- diffsentinel:start -->"
AGENT_END = "<!-- diffsentinel:end -->"


@dataclass(frozen=True)
class InitResult:
    root: Path
    created: tuple[Path, ...]
    updated: tuple[Path, ...]
    skipped: tuple[Path, ...]


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


def initialize_project(
    root: str | Path = ".",
    *,
    model: str = DEFAULT_OPENAI_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    force: bool = False,
    agent_docs: bool = True,
    env_example: bool = True,
    gitignore: bool = True,
) -> InitResult:
    project_root = Path(root).resolve()
    project_root.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    updated: list[Path] = []
    skipped: list[Path] = []

    config_path = project_root / CONFIG_NAME
    _write_file(
        config_path,
        default_config_text(model=model, reasoning_effort=reasoning_effort),
        force=force,
        created=created,
        updated=updated,
        skipped=skipped,
    )

    if env_example:
        _write_file(
            project_root / ".env.example",
            _env_example_text(model=model, reasoning_effort=reasoning_effort),
            force=force,
            created=created,
            updated=updated,
            skipped=skipped,
        )

    if gitignore:
        gitignore_path = project_root / ".gitignore"
        existed = gitignore_path.exists()
        if _ensure_gitignore(gitignore_path):
            (updated if existed else created).append(gitignore_path)
        else:
            skipped.append(gitignore_path)

    if agent_docs:
        agents_path = project_root / "AGENTS.md"
        existed = agents_path.exists()
        if _upsert_agent_docs(agents_path):
            (updated if existed else created).append(agents_path)
        else:
            skipped.append(agents_path)

    return InitResult(
        root=project_root,
        created=tuple(created),
        updated=tuple(updated),
        skipped=tuple(skipped),
    )


def run_doctor(
    root: str | Path = ".",
    *,
    live: bool = False,
) -> list[DoctorCheck]:
    project_root = Path(root).resolve()
    settings = load_settings(project_root)
    checks: list[DoctorCheck] = []

    checks.append(
        DoctorCheck(
            "package",
            "ok",
            f"diffsentinel {importlib.metadata.version('diffsentinel')}",
        )
    )
    checks.append(
        DoctorCheck(
            "config",
            "ok" if settings.config_path else "warn",
            str(settings.config_path) if settings.config_path else f"No {CONFIG_NAME} found; using defaults",
        )
    )
    checks.append(
        DoctorCheck(
            "model",
            "ok",
            f"{settings.openai_model}, reasoning_effort={settings.reasoning_effort}",
        )
    )

    api_key = os.getenv("OPENAI_API_KEY")
    checks.append(
        DoctorCheck(
            "openai_api_key",
            "ok" if api_key else "warn",
            _mask_secret(api_key) if api_key else "OPENAI_API_KEY is not set; local rules fallback will be used",
        )
    )
    checks.append(
        DoctorCheck(
            "openai_sdk",
            "ok" if importlib.util.find_spec("openai") else "error",
            "installed" if importlib.util.find_spec("openai") else "missing Python package: openai",
        )
    )

    checks.extend(_git_checks(project_root))
    if live:
        checks.append(_openai_live_check(settings))
    else:
        checks.append(DoctorCheck("live_api", "skip", "Not checked; run `diffsentinel doctor --live`"))
    return checks


def print_init_result(result: InitResult, console: Console) -> None:
    table = Table(title="DiffSentinel initialized", box=box.SIMPLE_HEAVY)
    table.add_column("Action")
    table.add_column("Path")
    for path in result.created:
        table.add_row("created", str(path))
    for path in result.updated:
        table.add_row("updated", str(path))
    for path in result.skipped:
        table.add_row("skipped", str(path))
    console.print(table)
    console.print(
        Panel(
            "Next:\n"
            "1. Set OPENAI_API_KEY in your shell or secret manager.\n"
            "2. Run `diffsentinel doctor`.\n"
            "3. Run `diffsentinel scan . --json --exit-on-critical` after coding-agent edits.",
            title="Setup checklist",
            border_style="green",
        )
    )


def print_doctor(checks: list[DoctorCheck], console: Console) -> None:
    table = Table(title="DiffSentinel doctor", box=box.SIMPLE_HEAVY)
    table.add_column("Check", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Detail")
    for check in checks:
        status_style = {"ok": "green", "warn": "yellow", "error": "red", "skip": "dim"}.get(check.status, "white")
        table.add_row(check.name, f"[{status_style}]{check.status}[/{status_style}]", check.detail)
    console.print(table)


def checks_json(checks: list[DoctorCheck]) -> str:
    return json.dumps({"checks": [asdict(check) for check in checks]}, indent=2)


def _write_file(
    path: Path,
    text: str,
    *,
    force: bool,
    created: list[Path],
    updated: list[Path],
    skipped: list[Path],
) -> None:
    if path.exists() and not force:
        skipped.append(path)
        return
    existed = path.exists()
    path.write_text(text, encoding="utf-8", newline="\n")
    (updated if existed else created).append(path)


def _env_example_text(*, model: str, reasoning_effort: str) -> str:
    return f"""# Copy this file to .env for local shells that load dotenv files.
# Never commit your real API key.
OPENAI_API_KEY=your-openai-api-key-here
DIFFSENTINEL_MODEL={model}
DIFFSENTINEL_REASONING_EFFORT={reasoning_effort}
"""


def _ensure_gitignore(path: Path) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    additions = []
    for line in (".env", "*.diffsentinel.bak"):
        if line not in existing.splitlines():
            additions.append(line)
    if not additions:
        return False
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    path.write_text(existing + prefix + "\n".join(additions) + "\n", encoding="utf-8", newline="\n")
    return True


def _upsert_agent_docs(path: Path) -> bool:
    block = f"""{AGENT_START}
## DiffSentinel Guardrail

After making code changes, run:

```powershell
diffsentinel scan . --json --exit-on-critical
```

If the command reports `CRITICAL` issues, fix safe items first or explain why manual review is required. Use:

```powershell
diffsentinel check --json --exit-on-critical
```

when only the current git diff should be audited.
{AGENT_END}
"""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if AGENT_START in existing and AGENT_END in existing:
        before, rest = existing.split(AGENT_START, 1)
        _, after = rest.split(AGENT_END, 1)
        path.write_text(before.rstrip() + "\n\n" + block + after.lstrip(), encoding="utf-8", newline="\n")
        return True
    path.write_text((existing.rstrip() + "\n\n" if existing else "") + block, encoding="utf-8", newline="\n")
    return True


def _git_checks(project_root: Path) -> list[DoctorCheck]:
    try:
        git_root = find_git_root(project_root)
    except HookError:
        return [
            DoctorCheck("git_repo", "warn", "Not inside a git repository"),
            DoctorCheck("pre_commit_hook", "skip", "No git repository"),
        ]

    hook_path = git_root / ".git" / "hooks" / "pre-commit"
    hook_status = "missing"
    status = "warn"
    if hook_path.exists():
        content = hook_path.read_text(encoding="utf-8", errors="replace")
        if HOOK_MARKER in content:
            hook_status = f"installed: {hook_path}"
            status = "ok"
        else:
            hook_status = f"user hook exists but is not managed by DiffSentinel: {hook_path}"
            status = "warn"
    return [
        DoctorCheck("git_repo", "ok", str(git_root)),
        DoctorCheck("pre_commit_hook", status, hook_status),
    ]


def _openai_live_check(settings: DiffSentinelSettings) -> DoctorCheck:
    if not os.getenv("OPENAI_API_KEY"):
        return DoctorCheck("live_api", "warn", "OPENAI_API_KEY missing")
    try:
        from openai import OpenAI

        client = OpenAI(timeout=10)
        client.models.list()
    except Exception as exc:
        return DoctorCheck("live_api", "error", str(exc))
    return DoctorCheck("live_api", "ok", f"API reachable; configured model={settings.openai_model}")


def _mask_secret(value: str | None) -> str:
    if not value:
        return ""
    return "set (masked)"
