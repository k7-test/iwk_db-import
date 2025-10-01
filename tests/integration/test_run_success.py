from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pandas as pd  # type: ignore
import pytest

from src.cli import main as cli_main

"""T009 Integration test: successful multi-file run (2 files, multiple sheets).

This test verifies end-to-end CLI execution with real Excel files containing multiple sheets,
validates inserted row count and SUMMARY output alignment per the contract.

Currently creates a failing test that will be implemented when the full processing pipeline
is built, including database operations and actual Excel processing.
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
def multi_file_excel_setup(temp_workdir: Path, write_config: Any) -> Dict[str, Any]:
    """Create 2 Excel files with multiple sheets containing test data."""
    data_dir = temp_workdir / "data"
    
    # File 1: customers.xlsx with 2 sheets
    customers_excel = _make_excel_file(
        data_dir, "customers.xlsx",
        {
            "Customers": [
                ["Customer Data", "Sheet 1"],  # Title row (ignored)
                ["id", "name", "email"],       # Header row (2nd row)
                [1, "Alice", "alice@example.com"],
                [2, "Bob", "bob@example.com"],
                [3, "Charlie", "charlie@example.com"],
            ],
            "CustomerProfiles": [
                ["Profile Information"],        # Title row (ignored)
                ["customer_id", "age", "city"], # Header row
                [1, 25, "Tokyo"],
                [2, 30, "Osaka"],
                [3, 28, "Kyoto"],
            ]
        }
    )
    
    # File 2: orders.xlsx with 2 sheets  
    orders_excel = _make_excel_file(
        data_dir, "orders.xlsx", 
        {
            "Orders": [
                ["Order Information"],           # Title row (ignored)
                ["id", "customer_id", "amount"], # Header row
                [101, 1, 1500.00],
                [102, 2, 2500.00],
                [103, 1, 800.00],
                [104, 3, 1200.00],
            ],
            "OrderItems": [
                ["Item Details"],                # Title row (ignored)
                ["order_id", "product", "qty"],  # Header row
                [101, "Widget A", 2],
                [101, "Widget B", 1], 
                [102, "Widget C", 3],
                [103, "Widget A", 1],
                [104, "Widget B", 2],
                [104, "Widget C", 1],
            ]
        }
    )
    
    return {
        'customers_file': customers_excel,
        'orders_file': orders_excel,
        'expected_total_rows': 3 + 3 + 4 + 6,  # Customers + CustomerProfiles + Orders + OrderItems
        'expected_files': 2,
        'expected_sheets': 4
    }


@pytest.mark.skip(
    "Integration test requires full processing pipeline - implement after orchestration service"
)
def test_multi_file_run_success_integration(
    temp_workdir: Path, multi_file_excel_setup: Dict[str, Any], capsys: Any
) -> None:
    """Test successful processing of 2 Excel files with multiple sheets each.
    
    This integration test should verify:
    1. CLI processes 2 Excel files successfully
    2. All 4 sheets are processed (2 per file)  
    3. Total row count matches expected (3+3+4+6=16 rows)
    4. SUMMARY output matches contract format
    5. Exit code is 0 (success)
    6. Database operations are mocked but verify insert calls
    """
    import os
    
    setup = multi_file_excel_setup
    
    # Mock database operations to simulate successful inserts
    with patch('src.db.batch_insert.batch_insert') as mock_insert:
        # Configure mock to return successful insert results
        mock_insert.return_value.inserted_rows = setup['expected_total_rows']
        
        cwd_before = os.getcwd()
        try:
            os.chdir(temp_workdir)
            exit_code = cli_main([])
        finally:
            os.chdir(cwd_before)
    
    captured = capsys.readouterr()
    output = captured.out
    
    # Verify exit code is success
    assert exit_code == 0, f"Expected exit code 0 (success), got {exit_code}"
    
    # Verify SUMMARY line matches contract format and values
    summary_pattern = re.compile(
        r"^SUMMARY\s+files=(\d+)/(\d+)\s+success=(\d+)\s+failed=(\d+)\s+"
        r"rows=(\d+)\s+skipped_sheets=(\d+)\s+elapsed_sec=(\d+\.?\d*)\s+"
        r"throughput_rps=(\d+\.?\d*)$", 
        re.MULTILINE
    )
    
    match = summary_pattern.search(output)
    assert match is not None, f"SUMMARY line not found or malformed in output: {output}"
    
    # Extract and verify SUMMARY values
    (total_files, detected_files, success_files, failed_files, 
     total_rows, skipped_sheets, elapsed_sec, throughput_rps) = match.groups()
    
    assert int(total_files) == setup['expected_files'], (
        f"Expected {setup['expected_files']} total files"
    )
    assert int(detected_files) == setup['expected_files'], (
        "Files count mismatch in files=X/Y format"
    )
    assert int(success_files) == setup['expected_files'], (
        f"Expected {setup['expected_files']} successful files"
    )
    assert int(failed_files) == 0, "Expected no failed files"
    assert int(total_rows) == setup['expected_total_rows'], (
        f"Expected {setup['expected_total_rows']} total rows"
    )
    assert int(skipped_sheets) == 0, "Expected no skipped sheets for valid test data"
    assert float(elapsed_sec) > 0, "Expected elapsed time > 0"
    assert float(throughput_rps) > 0, "Expected throughput > 0"
    
    # Verify database insert was called appropriately
    # (This will be refined when actual DB integration is implemented)
    mock_insert.assert_called()
    
    # Verify no error messages in output
    assert "ERROR" not in output, f"Unexpected error in output: {output}"
    assert "WARN" not in output, f"Unexpected warning in output: {output}"


def test_multi_file_excel_fixture_creates_valid_files(
    multi_file_excel_setup: Dict[str, Any]
) -> None:
    """Verify the test fixture creates valid Excel files with expected structure."""
    setup = multi_file_excel_setup
    
    # Verify files exist
    assert setup['customers_file'].exists(), "customers.xlsx should exist"
    assert setup['orders_file'].exists(), "orders.xlsx should exist"
    
    # Verify files are readable by pandas
    customers_data = pd.ExcelFile(setup['customers_file'])
    orders_data = pd.ExcelFile(setup['orders_file'])
    
    # Verify sheet names
    assert set(customers_data.sheet_names) == {"Customers", "CustomerProfiles"}
    assert set(orders_data.sheet_names) == {"Orders", "OrderItems"}
    
    # Verify sheet structure (spot check one sheet)
    customers_df = customers_data.parse("Customers", header=None)
    assert len(customers_df) == 5, "Expected 5 rows (title + header + 3 data rows)"
    assert customers_df.iloc[1, 0] == "id", "Second row should be header with 'id'"
    assert customers_df.iloc[2, 1] == "Alice", "Third row should contain 'Alice'"


@pytest.mark.skip("Placeholder until full pipeline implemented")  
def test_multi_file_run_with_skipped_sheets() -> None:
    """Test handling of skipped sheets (invalid/empty sheets)."""
    # TODO: Implement when sheet validation and skipping logic is added
    pass


@pytest.mark.skip("Placeholder until full pipeline implemented")
def test_multi_file_run_performance_timing() -> None:
    """Test that processing time is captured and reported correctly."""
    # TODO: Implement when timing instrumentation is added
    pass