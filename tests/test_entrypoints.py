import tomllib
from pathlib import Path
from unittest.mock import patch

from diffsentinel.cli import main

def test_dfs_console_script_alias_exists():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["diffsentinel"] == "diffsentinel.cli:main"
    assert pyproject["project"]["scripts"]["dfs"] == "diffsentinel.cli:main"


def test_dfs_single_path_opens_shell(tmp_path: Path):
    with patch("sys.argv", ["dfs", str(tmp_path)]), patch("diffsentinel.cli.run_shell", return_value=0) as run_shell:
        code = main()

    assert code == 0
    run_shell.assert_called_once_with(root=str(tmp_path))
