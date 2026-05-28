import tomllib
from pathlib import Path


def test_dfs_console_script_alias_exists():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["diffsentinel"] == "diffsentinel.cli:main"
    assert pyproject["project"]["scripts"]["dfs"] == "diffsentinel.cli:main"
