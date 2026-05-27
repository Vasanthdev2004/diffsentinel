from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONFIG_NAME = ".diffsentinel.toml"
DEFAULT_OPENAI_MODEL = "gpt-5.5"
DEFAULT_REASONING_EFFORT = "low"
VALID_REASONING_EFFORTS = ("low", "medium", "high", "xhigh")


@dataclass(frozen=True)
class DiffSentinelSettings:
    openai_model: str = DEFAULT_OPENAI_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    scan_max_files: int = 500
    scan_exclude_tests: bool = False
    scan_live: bool = False
    agent_default_scope: str = "changed"
    agent_fail_on_critical: bool = True
    config_path: Path | None = None


def load_settings(start: str | Path = ".") -> DiffSentinelSettings:
    config_path = find_config(start)
    data: dict[str, Any] = {}
    if config_path is not None:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    openai = data.get("openai", {})
    scan = data.get("scan", {})
    agent = data.get("agent", {})

    model = str(openai.get("model", DEFAULT_OPENAI_MODEL))
    reasoning_effort = str(openai.get("reasoning_effort", DEFAULT_REASONING_EFFORT))
    model = os.getenv("DIFFSENTINEL_MODEL", model)
    reasoning_effort = os.getenv("DIFFSENTINEL_REASONING_EFFORT", reasoning_effort)

    if reasoning_effort not in VALID_REASONING_EFFORTS:
        reasoning_effort = DEFAULT_REASONING_EFFORT

    return DiffSentinelSettings(
        openai_model=model,
        reasoning_effort=reasoning_effort,
        scan_max_files=int(scan.get("max_files", 500)),
        scan_exclude_tests=bool(scan.get("exclude_tests", False)),
        scan_live=bool(scan.get("live", False)),
        agent_default_scope=str(agent.get("default_scope", "changed")),
        agent_fail_on_critical=bool(agent.get("fail_on_critical", True)),
        config_path=config_path,
    )


def find_config(start: str | Path = ".") -> Path | None:
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        candidate = directory / CONFIG_NAME
        if candidate.exists():
            return candidate
    return None


def default_config_text(*, model: str = DEFAULT_OPENAI_MODEL, reasoning_effort: str = DEFAULT_REASONING_EFFORT) -> str:
    return f"""# DiffSentinel project configuration
# Do not store API keys in this file. Use OPENAI_API_KEY in your shell or secret manager.

[openai]
model = "{model}"
reasoning_effort = "{reasoning_effort}"

[scan]
max_files = 500
exclude_tests = false
live = false

[agent]
default_scope = "changed"
fail_on_critical = true
"""
