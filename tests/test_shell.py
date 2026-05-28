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


def test_shell_warns_for_plain_text(tmp_path: Path):
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    commands = iter(["hello", "/exit"])

    code = run_shell(root=tmp_path, console=console, input_func=lambda _: next(commands))

    assert code == 0
    assert "Use slash commands" in output.getvalue()
