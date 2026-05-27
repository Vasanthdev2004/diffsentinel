import json
from argparse import Namespace
from pathlib import Path

from diffsentinel.cli import run_scan
from diffsentinel.scanner import scan_project


def test_scan_project_builds_chunks_without_git(tmp_path: Path):
    source = tmp_path / "service.py"
    source.write_text(
        "import asyncio\n"
        "import time\n"
        "\n"
        "async def handle_request():\n"
        "    time.sleep(1)\n",
        encoding="utf-8",
    )

    result = scan_project(tmp_path)

    assert result.files_scanned == 1
    assert result.files_skipped == 0
    assert result.chunks[0].filepath == "service.py"
    assert "5*     time.sleep(1)" in result.chunks[0].code_excerpt


def test_scan_project_skips_virtualenv_dirs(tmp_path: Path):
    source = tmp_path / ".venv" / "bad.py"
    source.parent.mkdir()
    source.write_text("time.sleep(1)\n", encoding="utf-8")

    result = scan_project(tmp_path)

    assert result.files_scanned == 0
    assert result.chunks == []


def test_scan_project_marks_triple_quoted_fixture_lines_as_context(tmp_path: Path):
    source = tmp_path / "fixture.py"
    source.write_text(
        "BAD_SAMPLE = \"\"\"import asyncio\n"
        "import time\n"
        "\n"
        "async def handle_request():\n"
        "    time.sleep(1)\n"
        "\"\"\"\n",
        encoding="utf-8",
    )

    result = scan_project(tmp_path)

    assert result.files_scanned == 1
    assert "   5  " in result.chunks[0].code_excerpt
    assert "5*     time.sleep(1)" not in result.chunks[0].code_excerpt


def test_cli_scan_json_outputs_agent_contract(tmp_path: Path, capsys):
    source = tmp_path / "service.py"
    source.write_text(
        "import asyncio\n"
        "import time\n"
        "\n"
        "async def handle_request():\n"
        "    time.sleep(1)\n",
        encoding="utf-8",
    )

    code = run_scan(
        Namespace(
            path=str(tmp_path),
            json=True,
            no_tui=False,
            exit_on_critical=True,
            live=False,
            model="gpt-5.5",
            reasoning_effort="low",
            timeout=10.0,
            max_files=500,
            exclude_tests=False,
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["schema_version"] == "diffsentinel.agent.v1"
    assert payload["scope"] == "project"
    assert payload["summary"]["critical"] == 1
    assert payload["summary"]["files_scanned"] == 1
    assert payload["issues"][0]["file_path"] == "service.py"
    assert payload["issues"][0]["absolute_path"] == str(source.resolve())
