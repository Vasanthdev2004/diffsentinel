from __future__ import annotations

import re
from dataclasses import dataclass

from .diff import DiffChunk
from .schema import AnalysisResult, Issue


@dataclass(frozen=True)
class CodeLine:
    number: int
    text: str
    changed: bool

    @property
    def indent(self) -> int:
        return len(self.text) - len(self.text.lstrip())


BLOCKING_CALLS = {
    "time.sleep(": "Blocks the event loop for the sleep duration on every call.",
    "requests.get(": "Runs synchronous network I/O on the event loop.",
    "requests.post(": "Runs synchronous network I/O on the event loop.",
    "requests.put(": "Runs synchronous network I/O on the event loop.",
    "requests.delete(": "Runs synchronous network I/O on the event loop.",
    "subprocess.run(": "Runs a blocking subprocess call on the event loop.",
}


def analyze_with_rules(chunk: DiffChunk, *, enabled_rules: dict[str, bool] | None = None) -> AnalysisResult:
    lines = _parse_excerpt(chunk)
    issues: list[Issue] = []
    enabled_rules = enabled_rules or {}

    for line in lines:
        if not line.changed:
            continue
        if enabled_rules.get("blocking_io", True):
            issues.extend(_blocking_async_issues(lines, line))
        if enabled_rules.get("missing_await", True):
            issues.extend(_missing_await_issues(lines, line))
        if enabled_rules.get("clone_in_loop", True):
            issues.extend(_clone_in_loop_issues(lines, line))
        if enabled_rules.get("inefficient_collection", True):
            issues.extend(_inefficient_membership_issues(lines, line))

    return AnalysisResult(issues=_dedupe(issues))


def can_auto_apply(issue: Issue) -> bool:
    return "\n" not in issue.optimized_code and issue.confidence >= 0.8


def _blocking_async_issues(lines: list[CodeLine], line: CodeLine) -> list[Issue]:
    if not _inside_async_function(lines, line):
        return []

    stripped = line.text.strip()
    if "time.sleep(" in stripped:
        replacement = re.sub(r"\btime\.sleep\(", "asyncio.sleep(", stripped, count=1)
        return [
            Issue(
                line_number=line.number,
                severity="CRITICAL",
                category="BLOCKING_IO",
                explanation="Blocking sleep is running inside an async function.",
                impact="Blocks the event loop for the sleep duration on every call.",
                optimized_code=f"{_indent(line)}await {replacement}",
                confidence=0.98,
            )
        ]

    for call, impact in BLOCKING_CALLS.items():
        if call not in stripped or stripped.startswith("await "):
            continue
        optimized = _to_thread_replacement(line.text, call.rstrip("("))
        if optimized:
            return [
                Issue(
                    line_number=line.number,
                    severity="CRITICAL",
                    category="BLOCKING_IO",
                    explanation="Synchronous blocking work is running inside an async function.",
                    impact=impact,
                    optimized_code=optimized,
                    confidence=0.86,
                )
            ]
    return []


def _missing_await_issues(lines: list[CodeLine], line: CodeLine) -> list[Issue]:
    stripped = line.text.strip()
    if not _inside_async_function(lines, line):
        return []
    if stripped.startswith(("await ", "return await ")):
        return []
    if re.search(r"(^|=\s*|\(\s*|,\s*)asyncio\.\w+\(", stripped):
        optimized = _await_replacement(line.text)
        return [
            Issue(
                line_number=line.number,
                severity="CRITICAL",
                category="MISSING_AWAIT",
                explanation="Coroutine-like asyncio call is not awaited inside an async function.",
                impact="The coroutine may never run, causing delayed or missing async work.",
                optimized_code=optimized,
                confidence=0.84,
            )
        ]
    return []


def _clone_in_loop_issues(lines: list[CodeLine], line: CodeLine) -> list[Issue]:
    stripped = line.text.strip()
    if not re.search(r"\.(copy|clone)\(\)", stripped):
        return []
    if not _inside_loop(lines, line):
        return []
    return [
        Issue(
            line_number=line.number,
            severity="WARNING",
            category="UNNECESSARY_CLONE",
            explanation="Copying inside a loop adds avoidable allocation pressure.",
            impact="Allocates an extra object on every iteration.",
            optimized_code=f"{_indent(line)}# Avoid copying here; mutate a local projection or pass a reference instead.",
            confidence=0.68,
        )
    ]


def _inefficient_membership_issues(lines: list[CodeLine], line: CodeLine) -> list[Issue]:
    stripped = line.text.strip()
    if " in " not in stripped or not _inside_loop(lines, line):
        return []
    if re.search(r"\bin\s+(list|tuple)\(", stripped) or re.search(r"\bin\s+\w+_list\b", stripped):
        return [
            Issue(
                line_number=line.number,
                severity="WARNING",
                category="INEFFICIENT_COLLECTION",
                explanation="Repeated list membership inside a loop can become O(n^2).",
                impact="Converts repeated lookups into linear scans per iteration.",
                optimized_code=(
                    f"{_indent(line)}# Convert the membership source to a set before the loop, "
                    "then check membership against that set."
                ),
                confidence=0.74,
            )
        ]
    return []


def _to_thread_replacement(text: str, call_name: str) -> str | None:
    indent = text[: len(text) - len(text.lstrip())]
    stripped = text.strip()
    pattern = re.escape(call_name) + r"\((.*)\)"
    match = re.search(pattern, stripped)
    if not match:
        return None
    args = match.group(1)
    before = stripped[: match.start()]
    after = stripped[match.end() :]
    replacement_call = f"await asyncio.to_thread({call_name}, {args})"
    return f"{indent}{before}{replacement_call}{after}"


def _await_replacement(text: str) -> str:
    indent = text[: len(text) - len(text.lstrip())]
    stripped = text.strip()
    if "=" in stripped:
        left, right = stripped.split("=", 1)
        return f"{indent}{left.strip()} = await {right.strip()}"
    return f"{indent}await {stripped}"


def _inside_async_function(lines: list[CodeLine], line: CodeLine) -> bool:
    for candidate in reversed(lines):
        if candidate.number >= line.number:
            continue
        if re.match(r"\s*async def\s+\w+", candidate.text):
            return line.indent > candidate.indent
        if re.match(r"\s*def\s+\w+", candidate.text) and line.indent > candidate.indent:
            return False
    return False


def _inside_loop(lines: list[CodeLine], line: CodeLine) -> bool:
    for candidate in reversed(lines):
        if candidate.number >= line.number:
            continue
        if re.match(r"\s*(for|while)\s+", candidate.text):
            return line.indent > candidate.indent
        if candidate.text.strip() and candidate.indent < line.indent:
            return False
    return False


def _parse_excerpt(chunk: DiffChunk) -> list[CodeLine]:
    parsed: list[CodeLine] = []
    for raw_line in chunk.code_excerpt.splitlines():
        match = re.match(r"\s*(\d+)([ *]) (.*)", raw_line)
        if not match:
            continue
        parsed.append(
            CodeLine(
                number=int(match.group(1)),
                changed=match.group(2) == "*",
                text=match.group(3),
            )
        )
    return parsed


def _dedupe(issues: list[Issue]) -> list[Issue]:
    seen: set[tuple[int, str]] = set()
    unique: list[Issue] = []
    for issue in issues:
        key = (issue.line_number, issue.category)
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)
    return unique


def _indent(line: CodeLine) -> str:
    return line.text[: line.indent]
