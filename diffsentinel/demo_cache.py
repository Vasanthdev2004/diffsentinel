from __future__ import annotations

from .diff import DiffChunk
from .rules import analyze_with_rules
from .schema import AnalysisResult


def cached_result_for_chunk(chunk: DiffChunk, *, enabled_rules: dict[str, bool] | None = None) -> AnalysisResult:
    """Backward-compatible name for the offline local analyzer."""
    return analyze_with_rules(chunk, enabled_rules=enabled_rules)
