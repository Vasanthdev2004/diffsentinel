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
            apply_first=False,
            exit_on_critical=False,
            force_cache=True,
            model="gpt-5-mini",
            timeout=10.0,
        )
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["issues"][0]["severity"] == "CRITICAL"
    assert payload["issues"][0]["auto_applyable"] is True
    assert payload["issues"][0]["optimized_code"] == "    await asyncio.sleep(1)"


def test_cli_apply_first_rewrites_safe_fix(tmp_path: Path, monkeypatch):
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
            json=False,
            no_tui=False,
            apply_first=True,
            exit_on_critical=False,
            force_cache=True,
            model="gpt-5-mini",
            timeout=10.0,
        )
    )

    assert code == 0
    assert "await asyncio.sleep(1)" in sample.read_text(encoding="utf-8")
    assert (tmp_path / "async_blocking.py.diffsentinel.bak").exists()
