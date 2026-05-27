from io import StringIO

from rich.console import Console

from diffsentinel.schema import Issue
from diffsentinel.tui import IssueTarget, show_review


def test_show_review_can_be_forced_noninteractive():
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=100)
    issue = Issue(
        line_number=5,
        severity="CRITICAL",
        category="BLOCKING_IO",
        explanation="Blocking sleep is running inside an async function.",
        impact="Blocks the event loop.",
        optimized_code="    await asyncio.sleep(1)",
        confidence=0.98,
    )

    count = show_review(
        [IssueTarget(file_path="handler.py", issue=issue, excerpt="   5*     time.sleep(1)")],
        console=console,
        interactive=False,
    )

    assert count == 1
    assert "CRITICAL" in output.getvalue()
    assert "handler.py:5" in output.getvalue()
