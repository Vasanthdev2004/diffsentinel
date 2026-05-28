from io import StringIO
from pathlib import Path

from rich.console import Console

from diffsentinel.shell import run_shell


def test_shell_help_and_exit(tmp_path: Path):
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    commands = iter(["/help", "/exit"])

    code = run_shell(root=tmp_path, console=console, input_func=lambda _: next(commands))

    text = output.getvalue()
    assert code == 0
    assert "DiffSentinel Agent Shell" in text
    assert "/guard" in text
    assert "Session closed" in text


def test_shell_replies_to_plain_text_without_report(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    commands = iter(["can I commit?", "/exit"])

    code = run_shell(root=tmp_path, console=console, input_func=lambda _: next(commands))

    assert code == 0
    assert "I do not have a report yet" in output.getvalue()


def test_shell_chat_uses_last_report(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sample = tmp_path / "handler.py"
    sample.write_text(
        "import asyncio\n"
        "import time\n"
        "\n"
        "async def handle_request():\n"
        "    time.sleep(1)\n",
        encoding="utf-8",
    )
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    commands = iter(["/scan", "can I commit?", "/history", "/exit"])

    code = run_shell(root=tmp_path, console=console, input_func=lambda _: next(commands))

    text = output.getvalue()
    assert code == 0
    assert "Not yet" in text
    assert "Session history" in text
