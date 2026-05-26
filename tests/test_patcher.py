from pathlib import Path

from diffsentinel.patcher import apply_issue
from diffsentinel.schema import Issue


def test_apply_issue_replaces_line_and_creates_backup(tmp_path: Path):
    target = tmp_path / "async_blocking.py"
    target.write_text(
        "import asyncio\n"
        "import time\n"
        "\n"
        "async def handle_request():\n"
        "    time.sleep(1)\n"
        "    return {\"status\": \"ok\"}\n",
        encoding="utf-8",
    )
    issue = Issue(
        line_number=5,
        severity="CRITICAL",
        category="BLOCKING_IO",
        explanation="Blocking sleep is running inside an async function.",
        impact="Blocks the event loop.",
        optimized_code="    await asyncio.sleep(1)",
        confidence=0.98,
    )

    result = apply_issue(target, issue)

    assert target.read_text(encoding="utf-8").splitlines()[4] == "    await asyncio.sleep(1)"
    assert result.backup_path.exists()
    assert "time.sleep(1)" in result.backup_path.read_text(encoding="utf-8")
