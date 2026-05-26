from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


SKIP_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".pdf",
    ".toml",
    ".yaml",
    ".yml",
}
SKIP_NAMES = {
    "package-lock.json",
    "poetry.lock",
    "pdm.lock",
    "uv.lock",
    "Pipfile.lock",
}


@dataclass(frozen=True)
class DiffChunk:
    filepath: str
    code_excerpt: str
    line_offset: int
    changed_lines: tuple[int, ...]


class DiffError(RuntimeError):
    """Raised when git diff cannot be read."""


def get_diff_chunks(*, staged: bool = False, cwd: str | Path = ".") -> list[DiffChunk]:
    args = ["git", "diff", "--no-color", "--unified=3"]
    if staged:
        args.append("--cached")
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise DiffError("git is not installed or not on PATH") from exc

    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise DiffError(message or "git diff failed")

    return parse_unified_diff(completed.stdout)


def parse_unified_diff(diff_text: str) -> list[DiffChunk]:
    chunks: list[DiffChunk] = []
    current_file: str | None = None
    hunk_lines: list[tuple[int | None, str, bool]] = []
    hunk_start = 0
    new_line = 0
    skip_file = False

    def flush_hunk() -> None:
        nonlocal hunk_lines, hunk_start
        if current_file is None or skip_file or not hunk_lines:
            hunk_lines = []
            return

        changed = tuple(
            line_no
            for line_no, text, is_changed in hunk_lines
            if is_changed and line_no is not None and not _is_comment_only(text)
        )
        if not changed:
            hunk_lines = []
            return

        excerpt_lines = []
        for line_no, text, is_changed in hunk_lines:
            if line_no is None:
                continue
            marker = "*" if is_changed else " "
            excerpt_lines.append(f"{line_no:>4}{marker} {text}")

        chunks.append(
            DiffChunk(
                filepath=current_file,
                code_excerpt="\n".join(excerpt_lines),
                line_offset=hunk_start,
                changed_lines=changed,
            )
        )
        hunk_lines = []

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("diff --git "):
            flush_hunk()
            current_file = None
            skip_file = False
            continue

        if raw_line.startswith("+++ "):
            path = raw_line[4:].strip()
            if path == "/dev/null":
                current_file = None
                skip_file = True
                continue
            current_file = _normalize_git_path(path)
            skip_file = _should_skip(current_file)
            continue

        if raw_line.startswith("@@ "):
            flush_hunk()
            match = re.search(r"\+(\d+)(?:,(\d+))?", raw_line)
            if not match:
                continue
            hunk_start = int(match.group(1))
            new_line = hunk_start
            continue

        if current_file is None or skip_file:
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            text = raw_line[1:]
            hunk_lines.append((new_line, text, True))
            new_line += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            continue
        elif raw_line.startswith(" "):
            text = raw_line[1:]
            hunk_lines.append((new_line, text, False))
            new_line += 1
        elif raw_line.startswith("\\"):
            continue

    flush_hunk()
    return chunks


def _normalize_git_path(path: str) -> str:
    if path.startswith("b/"):
        return path[2:]
    return path


def _should_skip(filepath: str) -> bool:
    path = Path(filepath)
    return path.name in SKIP_NAMES or path.suffix.lower() in SKIP_EXTENSIONS


def _is_comment_only(line: str) -> bool:
    stripped = line.strip()
    return (
        not stripped
        or stripped.startswith("#")
        or stripped.startswith("//")
        or stripped.startswith("/*")
        or stripped.startswith("*")
        or stripped.startswith("*/")
    )
