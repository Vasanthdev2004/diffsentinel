from diffsentinel.diff import DiffChunk
from diffsentinel.rules import analyze_with_rules, can_auto_apply


def test_rules_detect_requests_get_inside_async():
    chunk = DiffChunk(
        filepath="service.py",
        code_excerpt=(
            "   1  import requests\n"
            "   2  import asyncio\n"
            "   4  async def fetch_user(url):\n"
            "   5*     response = requests.get(url)\n"
            "   6      return response.json()"
        ),
        line_offset=1,
        changed_lines=(5,),
    )

    result = analyze_with_rules(chunk)

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.category == "BLOCKING_IO"
    assert issue.optimized_code == "    response = await asyncio.to_thread(requests.get, url)"
    assert can_auto_apply(issue)


def test_rules_detect_missing_await_assignment():
    chunk = DiffChunk(
        filepath="service.py",
        code_excerpt=(
            "   1  import asyncio\n"
            "   3  async def work():\n"
            "   4*     pause = asyncio.sleep(1)\n"
            "   5      return pause"
        ),
        line_offset=1,
        changed_lines=(4,),
    )

    result = analyze_with_rules(chunk)

    assert len(result.issues) == 1
    assert result.issues[0].category == "MISSING_AWAIT"
    assert result.issues[0].optimized_code == "    pause = await asyncio.sleep(1)"


def test_rules_marks_clone_warning_as_manual_review():
    chunk = DiffChunk(
        filepath="service.py",
        code_excerpt=(
            "   1  def normalize(events):\n"
            "   2      for event in events:\n"
            "   3*         copied = event.copy()\n"
            "   4          yield copied"
        ),
        line_offset=1,
        changed_lines=(3,),
    )

    result = analyze_with_rules(chunk)

    assert len(result.issues) == 1
    assert result.issues[0].category == "UNNECESSARY_CLONE"
    assert not can_auto_apply(result.issues[0])


def test_rules_can_disable_blocking_io():
    chunk = DiffChunk(
        filepath="service.py",
        code_excerpt=(
            "   1  import asyncio\n"
            "   2  import time\n"
            "   4  async def handle_request():\n"
            "   5*     time.sleep(1)"
        ),
        line_offset=1,
        changed_lines=(5,),
    )

    result = analyze_with_rules(chunk, enabled_rules={"blocking_io": False})

    assert result.issues == []
