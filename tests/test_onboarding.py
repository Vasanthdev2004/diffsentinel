import json
from pathlib import Path

from diffsentinel.onboarding import checks_json, initialize_project, run_doctor
from diffsentinel.settings import load_settings


def test_initialize_project_creates_config_env_agent_docs_and_gitignore(tmp_path: Path):
    result = initialize_project(tmp_path, model="gpt-5.5", reasoning_effort="medium")

    config = tmp_path / ".diffsentinel.toml"
    env_example = tmp_path / ".env.example"
    agents = tmp_path / "AGENTS.md"
    gitignore = tmp_path / ".gitignore"

    assert config in result.created
    assert env_example in result.created
    assert agents in result.created
    assert gitignore in result.created
    assert "OPENAI_API_KEY" not in config.read_text(encoding="utf-8").splitlines()[0]
    assert 'model = "gpt-5.5"' in config.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=your-openai-api-key-here" in env_example.read_text(encoding="utf-8")
    assert "diffsentinel guard --changed --json --fail-on-critical" in agents.read_text(encoding="utf-8")
    assert ".env" in gitignore.read_text(encoding="utf-8")


def test_load_settings_reads_config_and_env_override(tmp_path: Path, monkeypatch):
    initialize_project(tmp_path, model="gpt-5.5", reasoning_effort="medium")
    monkeypatch.setenv("DIFFSENTINEL_REASONING_EFFORT", "high")

    settings = load_settings(tmp_path)

    assert settings.openai_model == "gpt-5.5"
    assert settings.reasoning_effort == "high"
    assert settings.scan_max_files == 500
    assert settings.config_path == tmp_path / ".diffsentinel.toml"


def test_doctor_reports_missing_api_key_without_error(tmp_path: Path, monkeypatch):
    initialize_project(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    checks = run_doctor(tmp_path)
    payload = json.loads(checks_json(checks))

    statuses = {check["name"]: check["status"] for check in payload["checks"]}
    assert statuses["config"] == "ok"
    assert statuses["openai_api_key"] == "warn"
    assert statuses["openai_sdk"] == "ok"
