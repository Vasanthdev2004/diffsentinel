from __future__ import annotations

import json
import os
from typing import Any

from pydantic import ValidationError

from .demo_cache import cached_result_for_chunk
from .diff import DiffChunk
from .rules import analyze_with_rules
from .schema import AnalysisResult


SYSTEM_PROMPT = """You are a performance-focused code auditor. You are given a snippet of code
that was just changed. Find ONLY performance problems: blocking calls in async
functions, missing await, O(N^2) or worse loops in hot paths, unnecessary
object copies in loops, inefficient collection use.

Do NOT comment on style, naming, formatting, typing, or documentation.
If there are no real performance problems, return an empty issues list.
For each issue give a concrete impact and an exact drop-in code replacement.

Return ONLY JSON matching the provided schema."""


def analyze_chunk(
    chunk: DiffChunk,
    *,
    model: str = "gpt-5-mini",
    timeout: float = 10.0,
    force_cache: bool = False,
) -> AnalysisResult:
    if force_cache or not os.getenv("OPENAI_API_KEY"):
        return analyze_with_rules(chunk)

    try:
        return _analyze_with_openai(chunk, model=model, timeout=timeout)
    except Exception:
        return cached_result_for_chunk(chunk)


def _analyze_with_openai(chunk: DiffChunk, *, model: str, timeout: float) -> AnalysisResult:
    try:
        from openai import OpenAI
    except ImportError:
        return cached_result_for_chunk(chunk)

    client = OpenAI(timeout=timeout)
    last_error: Exception | None = None
    for _ in range(2):
        try:
            result = _call_parse_api(client, chunk, model)
            if result is not None:
                return result
            return _call_json_schema_api(client, chunk, model)
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    raise RuntimeError("OpenAI analysis failed")


def _call_parse_api(client: Any, chunk: DiffChunk, model: str) -> AnalysisResult | None:
    parse = getattr(getattr(getattr(client, "beta", None), "chat", None), "completions", None)
    parse = getattr(parse, "parse", None)
    if parse is None:
        return None

    completion = parse(
        model=model,
        temperature=0,
        messages=_messages(chunk),
        response_format=AnalysisResult,
    )
    message = completion.choices[0].message
    parsed = getattr(message, "parsed", None)
    if parsed is not None:
        return parsed
    refusal = getattr(message, "refusal", None)
    if refusal:
        raise ValueError(refusal)
    content = getattr(message, "content", None)
    if not content:
        raise ValueError("OpenAI response had no content")
    return AnalysisResult.model_validate_json(content)


def _call_json_schema_api(client: Any, chunk: DiffChunk, model: str) -> AnalysisResult:
    completion = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=_messages(chunk),
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "diffsentinel_analysis",
                "strict": True,
                "schema": AnalysisResult.model_json_schema(),
            },
        },
    )
    message = completion.choices[0].message
    refusal = getattr(message, "refusal", None)
    if refusal:
        raise ValueError(refusal)
    return AnalysisResult.model_validate_json(message.content)


def _messages(chunk: DiffChunk) -> list[dict[str, str]]:
    changed = ", ".join(str(line) for line in chunk.changed_lines)
    user_prompt = f"""Analyze this changed file for performance problems only.

File: {chunk.filepath}
Changed line numbers: {changed}

Return issues only for changed lines or direct context needed to fix a changed line.
The line_number field must match the numeric line prefix in the excerpt.

Excerpt:
{chunk.code_excerpt}
"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
