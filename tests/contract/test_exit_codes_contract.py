from __future__ import annotations

import re
from pathlib import Path
from pathlib import Path as _P
from unittest.mock import MagicMock, patch

from src.cli import main as cli_main
from src.logging.init import reset_logging

"""Exit code contract tests (incrementally enabled)."""

PROJECT_ROOT = _P(__file__).resolve().parents[2]  # /workspaces/iwk_db-import


def test_exit_code_fatal_startup(temp_workdir: Path, capsys):
    # config/import.yml 無し → exit 1
    import os
    reset_logging()  # Ensure clean logging state
    
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
    reset_logging()  # Ensure clean logging state
    
    # Mock Excel processing to simulate successful processing
    mock_sheet_data = MagicMock()
    mock_sheet_data.columns = ["id", "name"]
    mock_sheet_data.rows = [{"id": 1, "name": "Test"}]
    
    def mock_read_side_effect(path, target_sheets=None, keep_na_strings=None):
        if "customers" in str(path):
            return {"Customers": MagicMock()}
        else:  # orders.xlsx
            return {"Orders": MagicMock()}
    
    with patch('src.services.orchestrator.read_excel_file') as mock_read:
        with patch('src.services.orchestrator.normalize_sheet') as mock_normalize:
            mock_read.side_effect = mock_read_side_effect
            mock_normalize.return_value = mock_sheet_data
            
            cwd_before = os.getcwd()
            try:
                os.chdir(temp_workdir)
                code = cli_main([])
            finally:
                os.chdir(cwd_before)
    
    out = capsys.readouterr().out
    assert code == 0
    assert code != 2  # Ensure no exit code 2 on pure success
    assert "SUMMARY files=2/2 success=2 failed=0" in out


def test_exit_code_partial_failure(temp_workdir: Path, write_config, capsys):
    """Test exit code 2 when some files fail but others succeed."""
    import os
    reset_logging()  # Ensure clean logging state
    
    # Create two Excel files - one will be simulated as failing  
    data_dir = temp_workdir / "data"
    success_file = data_dir / "success.xlsx"
    failure_file = data_dir / "failure.xlsx"
    
    # Create minimal Excel files (content doesn't matter since we mock)
    success_file.write_bytes(b"")
    failure_file.write_bytes(b"")
    
    # Mock Excel processing - success file succeeds, failure file fails
    mock_sheet_data = MagicMock()
    mock_sheet_data.columns = ["id", "name"]
    mock_sheet_data.rows = [{"id": 1, "name": "Test"}]
    
    def mock_read_side_effect(path, target_sheets=None, keep_na_strings=None):
        if "failure" in str(path):
            raise Exception("Simulated Excel read failure")
        return {"Customers": MagicMock()}  # Success case
    
    with patch('src.services.orchestrator.read_excel_file') as mock_read:
        with patch('src.services.orchestrator.normalize_sheet') as mock_normalize:
            mock_read.side_effect = mock_read_side_effect
            mock_normalize.return_value = mock_sheet_data
            
            cwd_before = os.getcwd()
            try:
                os.chdir(temp_workdir)
                code = cli_main([])
            finally:
                os.chdir(cwd_before)
    
    out = capsys.readouterr().out
    
    # Should return exit code 2 for partial failure
    assert code == 2
    
    # Should show some files succeeded and some failed in SUMMARY
    assert "SUMMARY files=2/2" in out
    assert "failed=" in out
    # At least one file should have failed (failed>0)
    # Extract failed count and verify it's > 0
    match = re.search(r"failed=(\d+)", out)
    assert match is not None, f"No 'failed=' found in output: {out}"
    failed_count = int(match.group(1))
    assert failed_count > 0, f"Expected failed > 0, got {failed_count}"
