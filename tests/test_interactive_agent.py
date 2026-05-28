import json
import subprocess
from argparse import Namespace
from pathlib import Path

from diffsentinel.cli import run_agent


def init_changed_repo(path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    sample = path / "handler.py"
    sample.write_text(
        "import asyncio\n"
        "import time\n"
        "\n"
        "async def handle_request():\n"
        "    await asyncio.sleep(1)\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "handler.py"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Demo", "-c", "user.email=demo@example.com", "commit", "-m", "baseline"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    sample.write_text(
        "import asyncio\n"
        "import time\n"
        "\n"
        "async def handle_request():\n"
        "    time.sleep(1)\n",
        encoding="utf-8",
    )
    return sample


def agent_namespace(path: Path, **overrides):
    values = {
        "path": str(path),
        "changed": True,
        "project": False,
        "staged": False,
        "live": False,
        "model": "gpt-5.5",
        "reasoning_effort": "low",
        "timeout": 10.0,
        "max_files": None,
        "exclude_tests": None,
        "yes": True,
        "dry_run": False,
        "json": True,
        "no_rerun": False,
        "fail_on_critical": True,
    }
    values.update(overrides)
    return Namespace(**values)


def test_agent_yes_applies_and_reruns_clean(tmp_path: Path, capsys):
    sample = init_changed_repo(tmp_path)

    code = run_agent(agent_namespace(tmp_path))

    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert code == 0
    assert payload["first_report"]["blocked_reason"] == "critical_issues_found"
    assert payload["final_report"]["next_action"] == "continue"
    assert payload["applied"]["applied"]
    assert "await asyncio.sleep(1)" in sample.read_text(encoding="utf-8")


def test_agent_without_safe_fixes_returns_clean(tmp_path: Path, capsys):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

    code = run_agent(agent_namespace(tmp_path, fail_on_critical=True))

    captured = capsys.readouterr().out
    payload = json.loads(captured[captured.index("{") :])
    assert code == 0
    assert payload["first_report"]["next_action"] == "continue"


def test_agent_dry_run_does_not_write_files(tmp_path: Path, capsys):
    sample = init_changed_repo(tmp_path)

    code = run_agent(agent_namespace(tmp_path, dry_run=True))

    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["applied"]["applied"][0]["dry_run"] is True
    assert "time.sleep(1)" in sample.read_text(encoding="utf-8")
