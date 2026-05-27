from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .diff import DiffChunk


EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".diffsentinel",
    ".tox",
    "node_modules",
    "dist",
    "build",
}


@dataclass(frozen=True)
class ProjectScan:
    root: Path
    chunks: list[DiffChunk]
    files_scanned: int
    files_skipped: int


def scan_project(
    root: str | Path = ".",
    *,
    max_files: int = 500,
    include_tests: bool = True,
) -> ProjectScan:
    project_root = Path(root).resolve()
    if not project_root.exists():
        raise FileNotFoundError(f"Project path does not exist: {project_root}")
    if not project_root.is_dir():
        raise NotADirectoryError(f"Project path is not a directory: {project_root}")

    chunks: list[DiffChunk] = []
    scanned = 0
    skipped = 0
    for path in _iter_python_files(project_root, include_tests=include_tests):
        if scanned >= max_files:
            skipped += 1
            continue
        chunk = _chunk_for_file(path, project_root)
        if chunk is None:
            skipped += 1
            continue
        chunks.append(chunk)
        scanned += 1

    return ProjectScan(
        root=project_root,
        chunks=chunks,
        files_scanned=scanned,
        files_skipped=skipped,
    )


def _iter_python_files(root: Path, *, include_tests: bool) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if not include_tests and any(part in {"test", "tests"} for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def _chunk_for_file(path: Path, root: Path) -> DiffChunk | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if not lines:
        return None

    excerpt_lines: list[str] = []
    changed_lines: list[int] = []
    in_string_block = False
    delimiter = ""
    for number, line in enumerate(lines, start=1):
        changed = not in_string_block
        next_in_string_block, next_delimiter, string_line = _string_block_state(
            line,
            in_string_block=in_string_block,
            delimiter=delimiter,
        )
        if string_line:
            changed = False
        marker = "*" if changed else " "
        analyzed_text = "" if string_line else line
        excerpt_lines.append(f"{number:>4}{marker} {analyzed_text}")
        if changed:
            changed_lines.append(number)
        in_string_block = next_in_string_block
        delimiter = next_delimiter

    relative_path = path.relative_to(root).as_posix()
    return DiffChunk(
        filepath=relative_path,
        code_excerpt="\n".join(excerpt_lines),
        line_offset=1,
        changed_lines=tuple(changed_lines),
    )


def _string_block_state(
    line: str,
    *,
    in_string_block: bool,
    delimiter: str,
) -> tuple[bool, str, bool]:
    if in_string_block:
        if delimiter in line:
            return False, "", True
        return True, delimiter, True

    positions = [
        (line.find('"""'), '"""'),
        (line.find("'''"), "'''"),
    ]
    positions = [(index, token) for index, token in positions if index >= 0]
    if not positions:
        return False, "", False

    _, token = min(positions, key=lambda item: item[0])
    if line.count(token) % 2 == 0:
        return False, "", True
    return True, token, True
