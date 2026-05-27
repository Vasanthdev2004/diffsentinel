import os
import subprocess
from pathlib import Path

import pytest

from diffsentinel.hooks import HookError, install_pre_commit_hook, uninstall_pre_commit_hook


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)


def test_install_pre_commit_hook_writes_managed_hook(tmp_path: Path):
    init_repo(tmp_path)

    result = install_pre_commit_hook(cwd=tmp_path)

    assert result.hook_path.exists()
    hook = result.hook_path.read_text(encoding="utf-8")
    assert "diffsentinel-managed-hook" in hook
    assert "diffsentinel check --staged --exit-on-critical --no-tui --force-cache" in hook
    assert os.access(result.hook_path, os.X_OK)


def test_install_hook_requires_force_for_existing_user_hook(tmp_path: Path):
    init_repo(tmp_path)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho user hook\n", encoding="utf-8")

    with pytest.raises(HookError):
        install_pre_commit_hook(cwd=tmp_path)


def test_install_hook_force_backs_up_existing_hook_and_uninstall_restores(tmp_path: Path):
    init_repo(tmp_path)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho user hook\n", encoding="utf-8")

    install_result = install_pre_commit_hook(cwd=tmp_path, force=True)

    assert install_result.backup_path is not None
    assert install_result.backup_path.exists()
    assert "user hook" in install_result.backup_path.read_text(encoding="utf-8")
    assert "diffsentinel-managed-hook" in hook_path.read_text(encoding="utf-8")

    uninstall_result = uninstall_pre_commit_hook(cwd=tmp_path)

    assert uninstall_result.backup_path is not None
    assert hook_path.exists()
    assert "user hook" in hook_path.read_text(encoding="utf-8")
