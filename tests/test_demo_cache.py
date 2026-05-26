from diffsentinel.demo_cache import cached_result_for_chunk
from diffsentinel.diff import DiffChunk


def test_async_blocking_cache_returns_critical_issue():
    chunk = DiffChunk(
        filepath="samples/async_blocking.py",
        code_excerpt=(
            "   1  import asyncio\n"
            "   2  import time\n"
            "   4  async def handle_request():\n"
            "   5*     time.sleep(1)\n"
            "   6      return {\"status\": \"ok\"}"
        ),
        line_offset=1,
        changed_lines=(5,),
    )

    result = cached_result_for_chunk(chunk)

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.severity == "CRITICAL"
    assert issue.category == "BLOCKING_IO"
    assert issue.line_number == 5
    assert issue.optimized_code == "    await asyncio.sleep(1)"
