import json
import subprocess
from argparse import Namespace
from pathlib import Path

from diffsentinel.cli import run_autopilot_command, run_review_pr


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


def autopilot_namespace(path: Path, **overrides):
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
        "apply_safe": False,
        "dry_run": False,
        "markdown": False,
        "json": True,
        "sarif": False,
        "fail_on_critical": True,
    }
    values.update(overrides)
    return Namespace(**values)


def test_autopilot_apply_safe_reruns_clean_and_writes_markdown(tmp_path: Path, capsys):
    sample = init_changed_repo(tmp_path)

    code = run_autopilot_command(autopilot_namespace(tmp_path, apply_safe=True, markdown=True))

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["first_report"]["blocked_reason"] == "critical_issues_found"
    assert payload["final_report"]["next_action"] == "continue"
    assert payload["markdown_path"]
    assert Path(payload["markdown_path"]).exists()
    assert "await asyncio.sleep(1)" in sample.read_text(encoding="utf-8")


def test_autopilot_without_apply_fails_on_critical(tmp_path: Path, capsys):
    init_changed_repo(tmp_path)

    code = run_autopilot_command(autopilot_namespace(tmp_path))

    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["final_report"]["blocked_reason"] == "critical_issues_found"


def test_review_pr_writes_markdown_report(tmp_path: Path, capsys):
    init_changed_repo(tmp_path)

    code = run_review_pr(autopilot_namespace(tmp_path, json=True, fail_on_critical=False))

    payload = json.loads(capsys.readouterr().out)
    report = Path(payload["markdown_path"])
    assert code == 0
    assert report.exists()
    assert "DiffSentinel PR Review" in report.read_text(encoding="utf-8")
