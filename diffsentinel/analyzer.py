from __future__ import annotations

import json
import os
from typing import Any

from pydantic import ValidationError

from .demo_cache import cached_result_for_chunk
from .diff import DiffChunk
from .rules import analyze_with_rules
from .schema import AnalysisResult
from .settings import DEFAULT_OPENAI_MODEL, DEFAULT_REASONING_EFFORT

SYSTEM_PROMPT = """You are a performance-focused code auditor. Find ONLY performance problems:
blocking calls in async functions, missing await, O(N^2) or worse loops in hot paths,
unnecessary object copies in loops, and inefficient collection use.

Do NOT comment on style, naming, formatting, typing, or documentation.
If there are no real performance problems, return an empty issues list.
For each issue give a concrete impact and an exact drop-in code replacement.
Only flag issues on changed lines or direct context needed to fix a changed line."""


def analyze_chunk(
    chunk: DiffChunk,
    *,
    model: str = DEFAULT_OPENAI_MODEL,
    timeout: float = 10.0,
    force_cache: bool = False,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    enabled_rules: dict[str, bool] | None = None,
) -> AnalysisResult:
    if force_cache or not os.getenv("OPENAI_API_KEY"):
        return analyze_with_rules(chunk, enabled_rules=enabled_rules)

    try:
        return _analyze_with_openai(chunk, model=model, timeout=timeout, reasoning_effort=reasoning_effort)
    except Exception:
        return cached_result_for_chunk(chunk, enabled_rules=enabled_rules)


def _analyze_with_openai(
    chunk: DiffChunk,
    *,
    model: str,
    timeout: float,
    reasoning_effort: str,
) -> AnalysisResult:
    try:
        from openai import OpenAI
    except ImportError:
        return cached_result_for_chunk(chunk)

    client = OpenAI(timeout=timeout)
    last_error: Exception | None = None
    for _ in range(2):
        try:
            result = _call_responses_parse_api(client, chunk, model, reasoning_effort)
            if result is not None:
                return result
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


def _call_responses_parse_api(
    client: Any,
    chunk: DiffChunk,
    model: str,
    reasoning_effort: str,
) -> AnalysisResult | None:
    parse = getattr(getattr(client, "responses", None), "parse", None)
    if parse is None:
        return None

    response = parse(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=_user_prompt(chunk),
        text_format=AnalysisResult,
        reasoning={"effort": reasoning_effort},
        verbosity="low",
        store=False,
        prompt_cache_key="diffsentinel-performance-audit-v1",
    )
    parsed = getattr(response, "output_parsed", None)
    if parsed is not None:
        return parsed
    output_text = getattr(response, "output_text", None)
    if not output_text:
        raise ValueError("OpenAI response had no parseable output")
    return AnalysisResult.model_validate_json(output_text)


def _call_parse_api(client: Any, chunk: DiffChunk, model: str) -> AnalysisResult | None:
    parse = getattr(getattr(getattr(client, "beta", None), "chat", None), "completions", None)
    parse = getattr(parse, "parse", None)
    if parse is None:
        return None

    completion = parse(
        model=model,
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
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _user_prompt(chunk)},
    ]


def _user_prompt(chunk: DiffChunk) -> str:
    changed = ", ".join(str(line) for line in chunk.changed_lines)
    return f"""Analyze this changed file for performance problems only.

File: {chunk.filepath}
Changed line numbers: {changed}

Return issues only for changed lines or direct context needed to fix a changed line.
The line_number field must match the numeric line prefix in the excerpt.

Excerpt:
{chunk.code_excerpt}
"""
