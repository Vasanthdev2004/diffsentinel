from io import StringIO
from types import SimpleNamespace
from pathlib import Path

from rich.console import Console

from diffsentinel.shell import ASCII_LOGO, THINKING_PHRASES, UNICODE_LOGO, _advance_status, _logo_for_console, run_shell


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


def test_shell_greets_without_report(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    commands = iter(["hi", "/exit"])

    code = run_shell(root=tmp_path, console=console, input_func=lambda _: next(commands))

    assert code == 0
    assert "Hey. I am here." in output.getvalue()


def test_shell_uses_live_chat_when_available(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("diffsentinel.shell._openai_shell_reply", lambda *_args: ("live answer", None))
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    commands = iter(["hi", "/chat-debug", "/exit"])

    code = run_shell(root=tmp_path, console=console, input_func=lambda _: next(commands))

    text = output.getvalue()
    assert code == 0
    assert "live answer" in text
    assert "Live chat is available" in text


def test_shell_chat_debug_shows_fallback_reason(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("diffsentinel.shell._openai_shell_reply", lambda *_args: (None, "boom"))
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    commands = iter(["hi", "/chat-debug", "/exit"])

    code = run_shell(root=tmp_path, console=console, input_func=lambda _: next(commands))

    text = output.getvalue()
    assert code == 0
    assert "boom" in text


def test_thinking_status_advances_phrase():
    calls = []

    class FakeStatus:
        def update(self, text):
            calls.append(text)

    _advance_status(FakeStatus(), 1)

    assert THINKING_PHRASES[1] in calls[0]


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


def test_shell_auto_selects_single_child_project(tmp_path: Path):
    project = tmp_path / "diffsentinel"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    commands = iter(["/status", "/exit"])

    code = run_shell(root=tmp_path, console=console, input_func=lambda _: next(commands))

    assert code == 0
    assert str(project.resolve()) in output.getvalue()


def test_shell_logo_uses_ascii_for_captured_output():
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)

    assert _logo_for_console(console) == ASCII_LOGO


def test_shell_logo_uses_unicode_for_utf8_terminal():
    console = SimpleNamespace(is_terminal=True, encoding="utf-8")

    assert _logo_for_console(console) == UNICODE_LOGO
