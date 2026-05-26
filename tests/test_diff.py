import subprocess
from pathlib import Path

from diffsentinel.diff import get_diff_chunks, parse_unified_diff


def test_parse_unified_diff_extracts_changed_python_line():
    diff_text = """diff --git a/samples/async_blocking.py b/samples/async_blocking.py
index 1111111..2222222 100644
--- a/samples/async_blocking.py
+++ b/samples/async_blocking.py
@@ -2,4 +2,4 @@ import asyncio
 import time
 
 async def handle_request():
-    await asyncio.sleep(1)
+    time.sleep(1)
     return {"status": "ok"}
"""

    chunks = parse_unified_diff(diff_text)

    assert len(chunks) == 1
    assert chunks[0].filepath == "samples/async_blocking.py"
    assert chunks[0].changed_lines == (5,)
    assert "5*     time.sleep(1)" in chunks[0].code_excerpt


def test_get_diff_chunks_reads_git_diff(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sample = tmp_path / "sample.py"
    sample.write_text(
        "import asyncio\n"
        "import time\n"
        "\n"
        "async def handle_request():\n"
        "    await asyncio.sleep(1)\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "sample.py"], cwd=tmp_path, check=True, capture_output=True)
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

    chunks = get_diff_chunks(cwd=tmp_path)

    assert len(chunks) == 1
    assert chunks[0].filepath == "sample.py"
    assert chunks[0].changed_lines == (5,)
