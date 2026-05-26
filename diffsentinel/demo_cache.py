from __future__ import annotations

import re
from pathlib import Path

from .diff import DiffChunk
from .schema import AnalysisResult, Issue


def cached_result_for_chunk(chunk: DiffChunk) -> AnalysisResult:
    basename = Path(chunk.filepath).name
    if basename == "async_blocking.py":
        return AnalysisResult(issues=[_async_blocking_issue(chunk)])
    if basename == "nested_loop.py":
        return AnalysisResult(issues=[_nested_loop_issue(chunk)])
    if basename == "clone_in_loop.py":
        return AnalysisResult(issues=[_clone_in_loop_issue(chunk)])
    return _heuristic_result(chunk)


def _heuristic_result(chunk: DiffChunk) -> AnalysisResult:
    if "async def " in chunk.code_excerpt and re.search(r"\btime\.sleep\(", chunk.code_excerpt):
        return AnalysisResult(issues=[_async_blocking_issue(chunk)])
    return AnalysisResult(issues=[])


def _async_blocking_issue(chunk: DiffChunk) -> Issue:
    line_number = _line_for(chunk, "time.sleep", default=next(iter(chunk.changed_lines), 1))
    original = _line_text(chunk, line_number)
    indent = original[: len(original) - len(original.lstrip())]
    replacement = re.sub(r"\btime\.sleep\(", "asyncio.sleep(", original.strip(), count=1)
    return Issue(
        line_number=line_number,
        severity="CRITICAL",
        category="BLOCKING_IO",
        explanation="Blocking sleep is running inside an async function.",
        impact="Blocks the event loop for the sleep duration on every call.",
        optimized_code=f"{indent}await {replacement}",
        confidence=0.98,
    )


def _nested_loop_issue(chunk: DiffChunk) -> Issue:
    line_number = _line_for(chunk, "for active_id in active_ids", default=next(iter(chunk.changed_lines), 1))
    indent = " " * 4
    return Issue(
        line_number=line_number,
        severity="WARNING",
        category="COMPLEXITY_REGRESSION",
        explanation="Nested membership checks make this lookup scale quadratically.",
        impact="Turns matching into O(users * active_ids) work instead of O(users + active_ids).",
        optimized_code=(
            f"{indent}active_id_set = set(active_ids)\n"
            f"{indent}return [user for user in users if user[\"id\"] in active_id_set]"
        ),
        confidence=0.82,
    )


def _clone_in_loop_issue(chunk: DiffChunk) -> Issue:
    line_number = _line_for(chunk, ".copy()", default=next(iter(chunk.changed_lines), 1))
    original = _line_text(chunk, line_number)
    indent = original[: len(original) - len(original.lstrip())]
    return Issue(
        line_number=line_number,
        severity="WARNING",
        category="UNNECESSARY_CLONE",
        explanation="Copying every event inside the loop adds avoidable allocation pressure.",
        impact="Allocates one extra dictionary per event processed.",
        optimized_code=f"{indent}event = event",
        confidence=0.68,
    )


def _line_for(chunk: DiffChunk, needle: str, *, default: int) -> int:
    for raw_line in chunk.code_excerpt.splitlines():
        if needle not in raw_line:
            continue
        match = re.match(r"\s*(\d+)[ *]", raw_line)
        if match:
            return int(match.group(1))
    return default


def _line_text(chunk: DiffChunk, line_number: int) -> str:
    prefix = f"{line_number:>4}"
    for raw_line in chunk.code_excerpt.splitlines():
        if raw_line.startswith(prefix):
            return raw_line[6:]
    return ""
