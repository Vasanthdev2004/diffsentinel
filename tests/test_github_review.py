import subprocess
from pathlib import Path

from diffsentinel.github_review import WATERMARK, review_pull_request
from diffsentinel.settings import DiffSentinelSettings


def init_repo(path: Path) -> Path:
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


def test_github_review_dry_run_requests_changes_and_watermarks(tmp_path: Path):
    init_repo(tmp_path)
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    outcome = review_pull_request(
        12,
        root=tmp_path,
        settings=DiffSentinelSettings(),
        act=False,
        runner=runner,
    )

    assert outcome.action == "request-changes"
    assert outcome.acted is False
    assert WATERMARK.strip() in outcome.body
    assert outcome.report_path.exists()
    assert calls == [["gh", "pr", "checkout", "12"]]


def test_github_review_act_posts_request_changes(tmp_path: Path):
    init_repo(tmp_path)
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    outcome = review_pull_request(
        7,
        root=tmp_path,
        settings=DiffSentinelSettings(),
        act=True,
        runner=runner,
    )

    assert outcome.acted is True
    assert calls[0] == ["gh", "pr", "checkout", "7"]
    assert calls[1][0:4] == ["gh", "pr", "review", "7"]
    assert "REQUEST_CHANGES" in calls[1]
