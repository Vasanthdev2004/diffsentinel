from pathlib import Path

from diffsentinel.memory import analyse_project, has_project_memory, load_project_memory


def test_analyse_project_writes_memory_files(tmp_path: Path):
    (tmp_path / "service.py").write_text(
        "import asyncio\n\nasync def handler():\n    return 1\n",
        encoding="utf-8",
    )

    memory = analyse_project(tmp_path)

    assert has_project_memory(tmp_path)
    assert memory.markdown_path.exists()
    assert memory.json_path.exists()
    loaded = load_project_memory(tmp_path)
    assert loaded is not None
    assert loaded["files_scanned"] == 1
    assert loaded["async_files"] == 1
    assert "service.py" in loaded["python_files"]
