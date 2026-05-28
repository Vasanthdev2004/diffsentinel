import json
import subprocess
from argparse import Namespace
from pathlib import Path

from diffsentinel.agent import build_agent_report, collect_project_findings
from diffsentinel.cli import run_apply_safe, run_fix_plan, run_guard, run_restore


def write_bad_async(path: Path) -> None:
    path.write_text(
        "import asyncio\n"
        "import time\n"
        "\n"
        "async def handle_request():\n"
        "    time.sleep(1)\n",
        encoding="utf-8",
    )


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
    write_bad_async(sample)
    return sample


def guard_namespace(path: Path, **overrides):
    values = {
        "path": str(path),
        "changed": True,
        "project": False,
        "staged": False,
        "json": True,
        "sarif": False,
        "apply_safe": False,
        "dry_run": False,
        "fail_on_critical": True,
        "live": False,
        "model": "gpt-5.5",
        "reasoning_effort": "low",
        "timeout": 10.0,
        "max_files": None,
        "exclude_tests": None,
    }
    values.update(overrides)
    return Namespace(**values)


def test_agent_report_v2_groups_safe_and_manual_findings(tmp_path: Path):
    write_bad_async(tmp_path / "handler.py")
    (tmp_path / "events.py").write_text(
        "def normalize(events):\n"
        "    for event in events:\n"
        "        copied = event.copy()\n",
        encoding="utf-8",
    )
    finding_set = collect_project_findings(
        path=tmp_path,
        live=False,
        model="gpt-5.5",
        timeout=10.0,
        reasoning_effort="low",
        max_files=500,
        exclude_tests=False,
    )

    report = build_agent_report(finding_set, fail_on_critical=True)

    assert report["schema_version"] == "diffsentinel.agent.v2"
    assert report["summary"]["critical"] == 1
    assert report["summary"]["manual_review"] == 1
    assert report["safe_fixes"][0]["optimized_code"] == "    await asyncio.sleep(1)"
    assert report["manual_review"][0]["reason"] == "manual_review_required"
    assert report["exit_policy"]["exit_code"] == 1


def test_guard_changed_json_exits_on_critical(tmp_path: Path, monkeypatch, capsys):
    init_changed_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    code = run_guard(guard_namespace(tmp_path))

    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["schema_version"] == "diffsentinel.agent.v2"
    assert payload["scope"] == "changed"
    assert payload["blocked_reason"] == "critical_issues_found"
    assert payload["next_action"] == "apply_safe_fixes_then_rerun"


def test_guard_changed_sarif_outputs_code_scanning_payload(tmp_path: Path, monkeypatch, capsys):
    init_changed_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    code = run_guard(guard_namespace(tmp_path, json=False, sarif=True, fail_on_critical=False))

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["results"][0]["ruleId"] == "BLOCKING_IO"


def test_fix_plan_project_prints_safe_fix(tmp_path: Path, capsys):
    write_bad_async(tmp_path / "handler.py")

    code = run_fix_plan(
        guard_namespace(tmp_path, changed=False, project=True, json=False, fail_on_critical=False)
    )

    output = capsys.readouterr().out
    assert code == 0
    assert "DiffSentinel fix plan" in output
    assert "handler.py:5" in output


def test_apply_safe_and_restore_round_trip(tmp_path: Path, capsys):
    sample = tmp_path / "handler.py"
    write_bad_async(sample)

    apply_code = run_apply_safe(
        guard_namespace(tmp_path, changed=False, project=True, json=True, fail_on_critical=False)
    )
    apply_payload = json.loads(capsys.readouterr().out)

    assert apply_code == 0
    assert "await asyncio.sleep(1)" in sample.read_text(encoding="utf-8")
    assert apply_payload["applied"][0]["backup_path"]

    restore_code = run_restore(Namespace(path=str(tmp_path), run_id=None, json=True))
    restore_payload = json.loads(capsys.readouterr().out)

    assert restore_code == 0
    assert restore_payload["restored"][0]["file_path"] == str(sample.resolve())
    assert "time.sleep(1)" in sample.read_text(encoding="utf-8")


def test_apply_safe_dry_run_does_not_write_files(tmp_path: Path, capsys):
    sample = tmp_path / "handler.py"
    write_bad_async(sample)

    apply_code = run_apply_safe(
        guard_namespace(tmp_path, changed=False, project=True, json=True, fail_on_critical=False, dry_run=True)
    )
    payload = json.loads(capsys.readouterr().out)

    assert apply_code == 0
    assert payload["applied"][0]["dry_run"] is True
    assert payload["applied"][0]["before"] == "    time.sleep(1)"
    assert "time.sleep(1)" in sample.read_text(encoding="utf-8")
    assert not (tmp_path / ".diffsentinel" / "runs" / "latest.json").exists()
