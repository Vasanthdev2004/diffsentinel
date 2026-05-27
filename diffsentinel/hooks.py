from __future__ import annotations

import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path


HOOK_MARKER = "# diffsentinel-managed-hook"
DEFAULT_HOOK_COMMAND = "diffsentinel check --staged --exit-on-critical --no-tui --force-cache"


class HookError(RuntimeError):
    """Raised when DiffSentinel cannot safely manage a git hook."""


@dataclass(frozen=True)
class HookResult:
    git_root: Path
    hook_path: Path
    backup_path: Path | None = None


def install_pre_commit_hook(
    *,
    cwd: str | Path = ".",
    command: str = DEFAULT_HOOK_COMMAND,
    force: bool = False,
) -> HookResult:
    git_root = find_git_root(cwd)
    hook_path = _hook_path(git_root)
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    backup_path: Path | None = None
    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8", errors="replace")
        if HOOK_MARKER not in existing:
            if not force:
                raise HookError(
                    f"Existing pre-commit hook found at {hook_path}. "
                    "Use --force to back it up and replace it."
                )
            backup_path = _next_backup_path(hook_path)
            hook_path.replace(backup_path)

    hook_path.write_text(_hook_script(command), encoding="utf-8", newline="\n")
    _make_executable(hook_path)
    return HookResult(git_root=git_root, hook_path=hook_path, backup_path=backup_path)


def uninstall_pre_commit_hook(*, cwd: str | Path = ".", restore_backup: bool = True) -> HookResult:
    git_root = find_git_root(cwd)
    hook_path = _hook_path(git_root)
    if not hook_path.exists():
        return HookResult(git_root=git_root, hook_path=hook_path)

    existing = hook_path.read_text(encoding="utf-8", errors="replace")
    if HOOK_MARKER not in existing:
        raise HookError(f"Pre-commit hook is not managed by DiffSentinel: {hook_path}")

    hook_path.unlink()
    backup_path = _latest_backup_path(hook_path)
    if restore_backup and backup_path is not None:
        backup_path.replace(hook_path)
        _make_executable(hook_path)
        return HookResult(git_root=git_root, hook_path=hook_path, backup_path=backup_path)
    return HookResult(git_root=git_root, hook_path=hook_path, backup_path=backup_path)


def find_git_root(cwd: str | Path = ".") -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise HookError(message or "Not inside a git repository")
    return Path(completed.stdout.strip()).resolve()


def _hook_path(git_root: Path) -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks/pre-commit"],
        cwd=git_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise HookError(message or "Could not resolve git hook path")
    hook_path = Path(completed.stdout.strip())
    if not hook_path.is_absolute():
        hook_path = git_root / hook_path
    return hook_path.resolve()


def _hook_script(command: str) -> str:
    return f"""#!/bin/sh
{HOOK_MARKER}
set -eu

echo "DiffSentinel: auditing staged changes..."
{command}
"""


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _next_backup_path(hook_path: Path) -> Path:
    candidate = hook_path.with_name(f"{hook_path.name}.diffsentinel.bak")
    if not candidate.exists():
        return candidate
    index = 1
    while True:
        candidate = hook_path.with_name(f"{hook_path.name}.diffsentinel.bak.{index}")
        if not candidate.exists():
            return candidate
        index += 1


def _latest_backup_path(hook_path: Path) -> Path | None:
    backups = sorted(hook_path.parent.glob(f"{hook_path.name}.diffsentinel.bak*"))
    if not backups:
        return None
    return backups[-1]
