from io import StringIO

from rich.console import Console

from diffsentinel.schema import Issue
from diffsentinel.tui import IssueTarget, render_dashboard, show_review


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


def test_render_dashboard_contains_product_sections():
    console = Console(record=True, force_terminal=False, width=140, height=40)
    critical = Issue(
        line_number=5,
        severity="CRITICAL",
        category="BLOCKING_IO",
        explanation="Blocking sleep is running inside an async function.",
        impact="Blocks the event loop.",
        optimized_code="    await asyncio.sleep(1)",
        confidence=0.98,
    )
    warning = Issue(
        line_number=8,
        severity="WARNING",
        category="UNNECESSARY_CLONE",
        explanation="Copying inside a loop adds avoidable allocation pressure.",
        impact="Allocates an extra object on every iteration.",
        optimized_code="        # Avoid copying here; mutate a projection instead.",
        confidence=0.68,
    )

    console.print(
        render_dashboard(
            [
                IssueTarget(file_path="handler.py", issue=critical, excerpt="   5*     time.sleep(1)"),
                IssueTarget(file_path="events.py", issue=warning, excerpt="   8*         copied = event.copy()"),
            ],
            selected=0,
            status_message="Testing render",
        )
    )

    output = console.export_text()
    assert "DiffSentinel" in output
    assert "Changed Code" in output
    assert "Issue Feed" in output
    assert "Fix Preview" in output
    assert "SAFE" in output
    assert "FIXES" in output
