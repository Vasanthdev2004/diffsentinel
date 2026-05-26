from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .schema import Issue


@dataclass(frozen=True)
class PatchResult:
    file_path: Path
    backup_path: Path
    line_number: int


class PatchError(RuntimeError):
    """Raised when an issue cannot be safely applied."""


def apply_issue(file_path: str | Path, issue: Issue) -> PatchResult:
    path = Path(file_path)
    if not path.exists():
        raise PatchError(f"File does not exist: {path}")
    if issue.line_number < 1:
        raise PatchError("Issue line_number must be 1-based")

    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    index = issue.line_number - 1
    if index >= len(lines):
        raise PatchError(f"Line {issue.line_number} is outside {path}")

    newline = _detect_newline(lines[index])
    replacement_lines = _replacement_lines(issue.optimized_code, newline)
    updated = lines[:index] + replacement_lines + lines[index + 1 :]

    backup_path = path.with_name(f"{path.name}.diffsentinel.bak")
    shutil.copy2(path, backup_path)

    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write("".join(updated))
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

    return PatchResult(file_path=path, backup_path=backup_path, line_number=issue.line_number)


def _detect_newline(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    return "\n"


def _replacement_lines(optimized_code: str, newline: str) -> list[str]:
    raw_lines = optimized_code.splitlines()
    if not raw_lines:
        return [newline]
    return [line + newline for line in raw_lines]
