from diffsentinel.analyzer import DEFAULT_OPENAI_MODEL, DEFAULT_REASONING_EFFORT, analyze_chunk
from diffsentinel.diff import DiffChunk


def test_default_live_model_is_gpt_55():
    assert DEFAULT_OPENAI_MODEL == "gpt-5.5"
    assert DEFAULT_REASONING_EFFORT == "low"


def test_analyze_chunk_without_api_key_uses_local_rules(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
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

    result = analyze_chunk(chunk)

    assert result.issues[0].category == "BLOCKING_IO"
    assert result.issues[0].optimized_code == "    await asyncio.sleep(1)"
