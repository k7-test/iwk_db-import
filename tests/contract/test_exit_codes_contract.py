from __future__ import annotations
"""Exit code contract tests (incrementally enabled)."""
from pathlib import Path
import pytest
from pathlib import Path as _P
from src.cli import main as cli_main

PROJECT_ROOT = _P(__file__).resolve().parents[2]  # /workspaces/iwk_db-import


def test_exit_code_fatal_startup(temp_workdir: Path, capsys):
    # config/import.yml 無し → exit 1
    import os
    cwd_before = os.getcwd()
    try:
        os.chdir(temp_workdir)
        code = cli_main([])
    finally:
        os.chdir(cwd_before)
    captured = capsys.readouterr()
    assert code == 1
    assert "ERROR config:" in captured.out


def test_exit_code_all_success(temp_workdir: Path, write_config, dummy_excel_files, capsys):
    import os
    cwd_before = os.getcwd()
    try:
        os.chdir(temp_workdir)
        code = cli_main([])
    finally:
        os.chdir(cwd_before)
    out = capsys.readouterr().out
    assert code == 0
    assert "SUMMARY files=2/2 success=2 failed=0" in out


@pytest.mark.skip("Partial failure path not yet implemented")
def test_exit_code_partial_failure():  # pragma: no cover
    assert True
