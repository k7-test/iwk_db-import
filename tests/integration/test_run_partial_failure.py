from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch, MagicMock

import pandas as pd  # type: ignore
import pytest

from src.cli import main as cli_main

"""T010 Integration test: partial failure rollback (one file violates constraint → other commits).

This test verifies end-to-end CLI execution where one file fails due to constraint violation
while other files succeed, resulting in partial failure handling:
- Failed file is rolled back
- Successful files are committed
- Exit code 2 (partial failure)
- Proper SUMMARY output with success/failed counts
- Error log contains the constraint violation

Currently creates a failing test that will be implemented when the full processing pipeline
is built, including database operations with transaction rollback handling.
"""


def _make_excel_file(
    tmp_path: Path, name: str, sheets: dict[str, list[list[object]]]
) -> Path:
    """Create a real Excel file with multiple sheets for testing."""
    excel_path = tmp_path / name
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        for sheet_name, rows in sheets.items():
            df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=sheet_name, header=False, index=False)
    return excel_path


@pytest.fixture
def partial_failure_excel_setup(temp_workdir: Path, write_config: Any) -> Dict[str, Any]:
    """Create Excel files: one successful, one that will cause constraint violation."""
    data_dir = temp_workdir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # File 1: successful_file.xlsx - should succeed
    successful_excel = _make_excel_file(
        data_dir, "successful_file.xlsx",
        {
            "Customers": [
                ["Customer Data", "Sheet 1"],  # Title row (ignored)
                ["id", "name", "email"],       # Header row (2nd row)
                [1, "Alice", "alice@example.com"],
                [2, "Bob", "bob@example.com"],
            ],
        }
    )
    
    # File 2: constraint_violation.xlsx - designed to fail with constraint violation
    # Using a filename that signals constraint violation for test simulation
    failing_excel = _make_excel_file(
        data_dir, "constraint_violation.xlsx",
        {
            "Customers": [
                ["Customer Data", "Sheet 1"],  # Title row (ignored) 
                ["id", "name", "email"],       # Header row (2nd row)
                [1, "Duplicate Alice", "alice@example.com"],  # Duplicate ID - will violate constraint
                [1, "Another Duplicate", "alice2@example.com"],  # Another duplicate ID
            ],
        }
    )
    
    return {
        'successful_file': successful_excel,
        'failing_file': failing_excel,
        'expected_total_files': 2,
        'expected_success_files': 1,
        'expected_failed_files': 1,
        'expected_successful_rows': 2,  # From successful file
        'expected_total_rows': 2,  # Only committed rows from successful file
    }


@pytest.mark.skip(
    "Integration test requires full processing pipeline with transaction rollback - implement after orchestration service"
)
def test_partial_failure_rollback_integration(
    temp_workdir: Path, partial_failure_excel_setup: Dict[str, Any], capsys: Any
) -> None:
    """Test partial failure: one file violates constraint → rollback, other commits successfully.
    
    This integration test should verify:
    1. CLI processes 2 Excel files
    2. One file fails with constraint violation and is rolled back
    3. Other file succeeds and is committed
    4. Exit code is 2 (partial failure)
    5. SUMMARY output shows correct success/failed counts
    6. Error log contains constraint violation details
    7. Only successful file's rows are counted in total
    """
    import os
    
    setup = partial_failure_excel_setup
    
    # Mock database operations to simulate constraint violation for failing file
    def mock_batch_insert_side_effect(*args, **kwargs):
        # Extract filename from the call context (will need adjustment when real implementation exists)
        # For now, simulate based on expected behavior
        if "constraint_violation" in str(args):
            # Simulate constraint violation
            raise Exception("duplicate key value violates unique constraint 'customers_pkey'")
        else:
            # Simulate successful insert
            return setup['expected_successful_rows']
    
    with patch('src.db.batch_insert.batch_insert') as mock_insert:
        mock_insert.side_effect = mock_batch_insert_side_effect
        
        # Mock error log to capture constraint violation
        with patch('src.logging.error_log.ErrorLogBuffer') as mock_error_log:
            mock_error_buffer = MagicMock()
            mock_error_log.return_value = mock_error_buffer
            
            cwd_before = os.getcwd()
            try:
                os.chdir(temp_workdir)
                exit_code = cli_main([])
            finally:
                os.chdir(cwd_before)
    
    captured = capsys.readouterr()
    output = captured.out
    
    # Verify exit code is partial failure
    assert exit_code == 2, f"Expected exit code 2 (partial failure), got {exit_code}"
    
    # Verify SUMMARY line matches contract format for partial failure
    summary_pattern = re.compile(
        r"^SUMMARY\s+files=(\d+)/(\d+)\s+success=(\d+)\s+failed=(\d+)\s+"
        r"rows=(\d+)\s+skipped_sheets=(\d+)\s+elapsed_sec=(\d+\.?\d*)\s+"
        r"throughput_rps=(\d+\.?\d*)$", 
        re.MULTILINE
    )
    
    match = summary_pattern.search(output)
    assert match is not None, f"SUMMARY line not found or malformed in output: {output}"
    
    # Extract and verify SUMMARY values for partial failure
    (total_files, detected_files, success_files, failed_files, 
     total_rows, skipped_sheets, elapsed_sec, throughput_rps) = match.groups()
    
    assert int(total_files) == setup['expected_total_files'], (
        f"Expected {setup['expected_total_files']} total files"
    )
    assert int(detected_files) == setup['expected_total_files'], (
        "Files count mismatch in files=X/Y format"
    )
    assert int(success_files) == setup['expected_success_files'], (
        f"Expected {setup['expected_success_files']} successful files"
    )
    assert int(failed_files) == setup['expected_failed_files'], (
        f"Expected {setup['expected_failed_files']} failed files"
    )
    assert int(total_rows) == setup['expected_total_rows'], (
        f"Expected {setup['expected_total_rows']} total committed rows (only from successful files)"
    )
    assert int(skipped_sheets) == 0, "Expected no skipped sheets"
    assert float(elapsed_sec) > 0, "Expected elapsed time > 0"
    assert float(throughput_rps) >= 0, "Expected throughput >= 0"
    
    # Verify error log was called to record constraint violation
    mock_error_buffer.append.assert_called()
    
    # Verify both success and failure processing occurred
    assert mock_insert.call_count >= 1, "Expected database insert attempts"
    
    # Verify no startup errors (should have gotten past initialization)
    assert "ERROR config:" not in output, f"Unexpected config error in output: {output}"
    assert "ERROR directory not found:" not in output, f"Unexpected directory error in output: {output}"


def test_partial_failure_excel_fixture_creates_valid_files(
    partial_failure_excel_setup: Dict[str, Any]
) -> None:
    """Verify the test fixture creates valid Excel files with expected structure."""
    setup = partial_failure_excel_setup
    
    # Verify files exist
    assert setup['successful_file'].exists(), "successful_file.xlsx should exist"
    assert setup['failing_file'].exists(), "constraint_violation.xlsx should exist"
    
    # Verify files are readable by pandas
    successful_data = pd.ExcelFile(setup['successful_file'])
    failing_data = pd.ExcelFile(setup['failing_file'])
    
    # Verify sheet names
    assert set(successful_data.sheet_names) == {"Customers"}
    assert set(failing_data.sheet_names) == {"Customers"}
    
    # Verify sheet structure (spot check)
    successful_df = successful_data.parse("Customers", header=None)
    failing_df = failing_data.parse("Customers", header=None)
    
    assert len(successful_df) == 4, "Expected 4 rows in successful file (title + header + 2 data rows)"
    assert len(failing_df) == 4, "Expected 4 rows in failing file (title + header + 2 data rows)"
    
    # Verify header structure
    assert successful_df.iloc[1, 0] == "id", "Second row should be header with 'id'"
    assert failing_df.iloc[1, 0] == "id", "Second row should be header with 'id'"
    
    # Verify failing file has duplicate IDs (constraint violation setup)
    assert failing_df.iloc[2, 0] == 1, "Third row should have ID 1"
    assert failing_df.iloc[3, 0] == 1, "Fourth row should have duplicate ID 1"


@pytest.mark.skip("Placeholder until full pipeline implemented")
def test_partial_failure_error_log_details() -> None:
    """Test that error log contains detailed constraint violation information."""
    # TODO: Implement when error logging integration is added
    # Should verify error log contains:
    # - timestamp
    # - file name (constraint_violation.xlsx)
    # - sheet name (Customers)
    # - error_type (CONSTRAINT_VIOLATION)
    # - db_message with constraint details
    pass


@pytest.mark.skip("Placeholder until full pipeline implemented")
def test_partial_failure_transaction_rollback() -> None:
    """Test that failed file transaction is properly rolled back."""
    # TODO: Implement when transaction handling is added
    # Should verify that failed file's changes don't persist in database
    pass


@pytest.mark.skip("Placeholder until full pipeline implemented")
def test_partial_failure_processing_continues() -> None:
    """Test that processing continues after one file fails."""
    # TODO: Implement when orchestration service handles continuation
    # Should verify that failure of one file doesn't stop processing of remaining files
    pass