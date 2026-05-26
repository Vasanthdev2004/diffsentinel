import json
import subprocess
from argparse import Namespace
from pathlib import Path

from diffsentinel.cli import run_check


def test_cli_json_uses_cache_for_primary_demo(tmp_path: Path, monkeypatch, capsys):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sample = tmp_path / "async_blocking.py"
    sample.write_text(
        "import asyncio\n"
        "import time\n"
        "\n"
        "async def handle_request():\n"
        "    await asyncio.sleep(1)\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "async_blocking.py"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Demo", "-c", "user.email=demo@example.com", "commit", "-m", "baseline"],
        cwd=tmp_path,
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

    monkeypatch.chdir(tmp_path)
    code = run_check(
        Namespace(
            staged=False,
            json=True,
            no_tui=False,
            force_cache=True,
            model="gpt-5-mini",
            timeout=10.0,
        )
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["issues"][0]["severity"] == "CRITICAL"
    assert payload["issues"][0]["optimized_code"] == "    await asyncio.sleep(1)"
