from io import StringIO
from pathlib import Path

from rich.console import Console

from diffsentinel.demo import run_agent_demo, run_demo


def test_run_demo_creates_repo_detects_issue_and_applies_fix(tmp_path: Path):
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=100)

    result = run_demo(path=tmp_path / "demo", console=console)

    assert result.issue is not None
    assert result.issue.category == "BLOCKING_IO"
    assert result.applied is True
    assert "await asyncio.sleep(1)" in result.target_file.read_text(encoding="utf-8")
    assert result.backup_file is not None
    assert result.backup_file.exists()
    assert "time.sleep(1)" in result.backup_file.read_text(encoding="utf-8")
    assert "Demo workspace" in output.getvalue()


def test_run_demo_can_show_without_applying(tmp_path: Path):
    console = Console(file=StringIO(), force_terminal=False, width=100)

    result = run_demo(path=tmp_path / "demo", apply_fix=False, console=console)

    assert result.issue is not None
    assert result.applied is False
    assert "time.sleep(1)" in result.target_file.read_text(encoding="utf-8")
    assert result.backup_file is None


def test_run_agent_demo_shows_guard_apply_and_restore(tmp_path: Path):
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)

    result = run_agent_demo(path=tmp_path / "agent-demo", console=console)

    assert result.first_report["schema_version"] == "diffsentinel.agent.v2"
    assert result.first_report["blocked_reason"] == "critical_issues_found"
    assert result.clean_report["next_action"] == "continue"
    assert result.applied_count == 1
    assert result.restored_count == 1
    assert "time.sleep(1)" in result.target_file.read_text(encoding="utf-8")
    assert "Agent JSON v2 Summary" in output.getvalue()
