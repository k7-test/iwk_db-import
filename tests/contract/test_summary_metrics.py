from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.cli import main as cli_main
from src.logging.init import reset_logging

"""Contract test: summary metrics populated (T006).

Tests that SUMMARY line contains meaningful metrics (rows>0, elapsed_sec>0, throughput_rps>=0)
based on the contract regex from contracts/summary_output.md.

Test Cases from contract:
1. All success: success + failed=0 + positive throughput
2. Partial failure: failed>0 → exit code 2 consistency  
3. rows=0 (Excel 0 files) → throughput_rps=0
4. Skipped sheets: skipped_sheets>0
"""

# Regex pattern from contracts/summary_output.md
SUMMARY_PATTERN = re.compile(
    r"^SUMMARY\s+files=([0-9]+)/(\1)\s+success=([0-9]+)\s+failed=([0-9]+)\s+"
    r"rows=([0-9]+)\s+skipped_sheets=([0-9]+)\s+elapsed_sec=([0-9]+\.?[0-9]*)\s+"
    r"throughput_rps=([0-9]+\.?[0-9]*)$"
)


def test_summary_pattern_valid_format():
    """Test that SUMMARY regex pattern works for valid example lines."""
    test_cases = [
        "SUMMARY files=1/1 success=1 failed=0 rows=4 skipped_sheets=0 elapsed_sec=0.84 "
        "throughput_rps=4761.9",
        "SUMMARY files=2/2 success=1 failed=1 rows=100 skipped_sheets=2 elapsed_sec=1.5 "
        "throughput_rps=66.7",
        "SUMMARY files=0/0 success=0 failed=0 rows=0 skipped_sheets=0 elapsed_sec=0 "
        "throughput_rps=0",
    ]
    
    for line in test_cases:
        match = SUMMARY_PATTERN.match(line)
        assert match, f"SUMMARY line should match regex: {line}"


def test_summary_pattern_extracts_metrics():
    """Test that regex extracts correct metric values."""
    line = (
        "SUMMARY files=3/3 success=2 failed=1 rows=150 skipped_sheets=1 "
        "elapsed_sec=2.5 throughput_rps=60.0"
    )
    match = SUMMARY_PATTERN.match(line)
    assert match
    
    # groups: files, files_duplicate, success, failed, rows, skipped_sheets, 
    # elapsed_sec, throughput_rps
    assert match.group(1) == "3"  # files
    assert match.group(2) == "3"  # files (duplicate for validation)
    assert match.group(3) == "2"  # success
    assert match.group(4) == "1"  # failed
    assert match.group(5) == "150"  # rows
    assert match.group(6) == "1"  # skipped_sheets
    assert match.group(7) == "2.5"  # elapsed_sec
    assert match.group(8) == "60.0"  # throughput_rps


# Skip removed - CLI now populates real metrics through orchestrator
def test_cli_success_populates_metrics(
    temp_workdir: Path, write_config, dummy_excel_files, capsys
):
    """Test Case 1: All success with populated metrics (rows>0, elapsed_sec>0, 
    throughput_rps>=0)."""
    import os
    from unittest.mock import patch

    from src.models.processing_result import ProcessingResult
    
    reset_logging()  # Ensure clean logging state
    
    # Mock the orchestrator to return realistic processing results
    from datetime import datetime, timedelta
    start_time = datetime.now() 
    end_time = start_time + timedelta(seconds=1.5)
    
    mock_result = ProcessingResult(
        success_files=2,  # 2 files processed successfully
        failed_files=0,
        total_inserted_rows=150,  # Some realistic row count
        skipped_sheets=0,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=1.5,  # Some realistic processing time
        throughput_rows_per_sec=100.0  # 150 rows / 1.5 sec = 100 rps
    )
    
    with patch('src.cli.__main__.process_all') as mock_process:
        mock_process.return_value = mock_result
        
        cwd_before = os.getcwd()
        try:
            os.chdir(temp_workdir)
            code = cli_main([])
        finally:
            os.chdir(cwd_before)
    
    out = capsys.readouterr().out
    assert code == 0
    
    # Find SUMMARY line
    summary_lines = [line for line in out.split('\n') if line.startswith('SUMMARY')]
    assert len(summary_lines) == 1, f"Expected exactly one SUMMARY line, got: {summary_lines}"
    
    summary_line = summary_lines[0]
    match = SUMMARY_PATTERN.match(summary_line)
    assert match, f"SUMMARY line should match contract regex: {summary_line}"
    
    # Extract metrics
    rows = int(match.group(5))
    elapsed_sec = float(match.group(7))
    throughput_rps = float(match.group(8))
    
    # Contract: when processing actual files, metrics should be populated
    assert rows > 0, f"Expected rows > 0 for successful processing, got: {rows}"
    assert elapsed_sec > 0, f"Expected elapsed_sec > 0 for actual processing, got: {elapsed_sec}"
    assert throughput_rps >= 0, f"Expected throughput_rps >= 0, got: {throughput_rps}"


def test_cli_zero_files_zero_throughput(temp_workdir: Path, write_config, capsys):
    """Test Case 3: rows=0 (Excel 0 files) → throughput_rps=0."""
    import os
    reset_logging()  # Ensure clean logging state
    
    # Remove any excel files to ensure 0 files scenario
    data_dir = temp_workdir / 'data'
    for f in data_dir.glob('*.xlsx'):
        f.unlink()

    cwd_before = os.getcwd()
    try:
        os.chdir(temp_workdir)
        code = cli_main([])
    finally:
        os.chdir(cwd_before)
    
    out = capsys.readouterr().out
    assert code == 0
    
    # Find SUMMARY line
    summary_lines = [line for line in out.split('\n') if line.startswith('SUMMARY')]
    assert len(summary_lines) == 1
    
    summary_line = summary_lines[0]  
    match = SUMMARY_PATTERN.match(summary_line)
    assert match, f"SUMMARY line should match contract regex: {summary_line}"
    
    # Extract metrics
    files = int(match.group(1))
    rows = int(match.group(5))
    throughput_rps = float(match.group(8))
    
    # Contract: 0 files → rows=0 → throughput_rps=0
    assert files == 0, f"Expected 0 files, got: {files}"
    assert rows == 0, f"Expected 0 rows for 0 files, got: {rows}"
    assert throughput_rps == 0, f"Expected throughput_rps=0 for 0 rows, got: {throughput_rps}"


def test_cli_partial_failure_metrics_consistency(
    temp_workdir: Path, write_config, dummy_excel_files, capsys
):
    """Test Case 2: Partial failure with failed>0 and exit code 2 consistency."""
    import os
    from unittest.mock import patch

    from src.models.processing_result import ProcessingResult
    
    reset_logging()  # Ensure clean logging state
    
    # Mock the orchestrator to return partial failure results
    from datetime import datetime, timedelta
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=2.0)
    
    mock_result = ProcessingResult(
        success_files=1,  # 1 file succeeded
        failed_files=1,   # 1 file failed
        total_inserted_rows=75,  # Only successful file rows counted
        skipped_sheets=0,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=2.0,
        throughput_rows_per_sec=37.5  # 75 rows / 2.0 sec = 37.5 rps
    )
    
    with patch('src.cli.__main__.process_all') as mock_process:
        mock_process.return_value = mock_result
        
        cwd_before = os.getcwd()
        try:
            os.chdir(temp_workdir)
            code = cli_main([])
        finally:
            os.chdir(cwd_before)
    
    out = capsys.readouterr().out
    
    # Should return exit code 2 for partial failure
    assert code == 2, f"Expected exit code 2 for partial failure, got: {code}"
    
    # Find SUMMARY line
    summary_lines = [line for line in out.split('\n') if line.startswith('SUMMARY')]
    assert len(summary_lines) == 1, f"Expected exactly one SUMMARY line, got: {summary_lines}"
    
    summary_line = summary_lines[0]
    match = SUMMARY_PATTERN.match(summary_line)
    assert match, f"SUMMARY line should match contract regex: {summary_line}"
    
    # Extract metrics
    success = int(match.group(3))
    failed = int(match.group(4))
    rows = int(match.group(5))
    elapsed_sec = float(match.group(7))
    throughput_rps = float(match.group(8))
    
    # Contract: partial failure should show failed > 0
    assert failed > 0, f"Expected failed > 0 for partial failure, got: {failed}"
    assert success > 0, f"Expected success > 0 for partial failure, got: {success}"
    assert rows > 0, f"Expected rows > 0 from successful files, got: {rows}"
    assert elapsed_sec > 0, f"Expected elapsed_sec > 0, got: {elapsed_sec}"
    assert throughput_rps >= 0, f"Expected throughput_rps >= 0, got: {throughput_rps}"


@pytest.mark.skip("Skipped sheets handling not yet implemented")
def test_cli_skipped_sheets_metrics(temp_workdir: Path, write_config, capsys):
    """Test Case 4: Skipped sheets with skipped_sheets>0."""
    # Will be implemented when sheet skipping logic is added
    # Should test: skipped_sheets > 0 and other metrics populated correctly
    assert True  # pragma: no cover