from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .scanner import scan_project
from .settings import load_settings


MEMORY_DIR = ".diffsentinel"
MEMORY_MD = "PROJECT_MEMORY.md"
MEMORY_JSON = "project_memory.json"


@dataclass(frozen=True)
class ProjectMemory:
    root: Path
    markdown_path: Path
    json_path: Path
    summary: dict


def has_project_memory(root: str | Path) -> bool:
    root_path = Path(root).resolve()
    return (root_path / MEMORY_DIR / MEMORY_MD).exists() and (root_path / MEMORY_DIR / MEMORY_JSON).exists()


def load_project_memory(root: str | Path) -> dict | None:
    path = Path(root).resolve() / MEMORY_DIR / MEMORY_JSON
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def analyse_project(root: str | Path) -> ProjectMemory:
    root_path = Path(root).resolve()
    settings = load_settings(root_path)
    scan = scan_project(
        root_path,
        max_files=settings.scan_max_files,
        include_tests=not settings.scan_exclude_tests,
        ignore_paths=settings.ignore_paths,
    )
    summary = _summary(root_path, scan.chunks, scan.files_scanned, scan.files_skipped)
    memory_dir = root_path / MEMORY_DIR
    memory_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = memory_dir / MEMORY_MD
    json_path = memory_dir / MEMORY_JSON
    markdown_path.write_text(_markdown(summary), encoding="utf-8", newline="\n")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return ProjectMemory(root=root_path, markdown_path=markdown_path, json_path=json_path, summary=summary)


def _summary(root: Path, chunks, files_scanned: int, files_skipped: int) -> dict:
    files = [chunk.filepath for chunk in chunks]
    top_dirs: dict[str, int] = {}
    imports: dict[str, int] = {}
    async_files = 0
    for chunk in chunks:
        top = chunk.filepath.split("/", 1)[0]
        top_dirs[top] = top_dirs.get(top, 0) + 1
        if "async def " in chunk.code_excerpt:
            async_files += 1
        for line in chunk.code_excerpt.splitlines():
            text = line[6:].strip() if len(line) > 6 else line.strip()
            if text.startswith("import "):
                name = text.split()[1].split(".")[0]
                imports[name] = imports.get(name, 0) + 1
            elif text.startswith("from "):
                name = text.split()[1].split(".")[0]
                imports[name] = imports.get(name, 0) + 1
    return {
        "schema_version": "diffsentinel.project_memory.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "files_scanned": files_scanned,
        "files_skipped": files_skipped,
        "python_files": files,
        "top_directories": dict(sorted(top_dirs.items(), key=lambda item: item[1], reverse=True)[:10]),
        "top_imports": dict(sorted(imports.items(), key=lambda item: item[1], reverse=True)[:15]),
        "async_files": async_files,
    }


def _markdown(summary: dict) -> str:
    lines = [
        "# DiffSentinel Project Memory",
        "",
        f"- Root: `{summary['root']}`",
        f"- Created at: `{summary['created_at']}`",
        f"- Python files scanned: {summary['files_scanned']}",
        f"- Files skipped: {summary['files_skipped']}",
        f"- Files containing async functions: {summary['async_files']}",
        "",
        "## Top Directories",
        "",
    ]
    if summary["top_directories"]:
        lines.extend(f"- `{name}`: {count} files" for name, count in summary["top_directories"].items())
    else:
        lines.append("- None")
    lines.extend(["", "## Top Imports", ""])
    if summary["top_imports"]:
        lines.extend(f"- `{name}`: {count}" for name, count in summary["top_imports"].items())
    else:
        lines.append("- None")
    lines.extend(["", "## Python Files", ""])
    lines.extend(f"- `{path}`" for path in summary["python_files"][:50])
    if len(summary["python_files"]) > 50:
        lines.append(f"- ...and {len(summary['python_files']) - 50} more")
    return "\n".join(lines) + "\n"
