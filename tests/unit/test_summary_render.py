from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

from src.models.processing_result import FileStat, ProcessingResult
from src.services.summary import render_summary_line

"""Unit tests for summary rendering service (T026).

Tests the render_summary_line function against the contract format from
contracts/summary_output.md.
"""

# Regex pattern from contracts/summary_output.md
SUMMARY_PATTERN = re.compile(
    r"^SUMMARY\s+files=([0-9]+)/(\1)\s+success=([0-9]+)\s+failed=([0-9]+)\s+"
    r"rows=([0-9]+)\s+skipped_sheets=([0-9]+)\s+elapsed_sec=([0-9]+\.?[0-9]*)\s+"
    r"throughput_rps=([0-9]+\.?[0-9]*)$"
)


def test_render_summary_line_all_success():
    """Test SUMMARY rendering for all successful files scenario."""
    start_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2023, 1, 1, 10, 0, 2, tzinfo=timezone.utc)  # 2 seconds elapsed
    
    result = ProcessingResult(
        success_files=2,
        failed_files=0,
        total_inserted_rows=1000,
        skipped_sheets=1,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=2.0,
        throughput_rows_per_sec=500.0,
    )
    
    summary_line = render_summary_line(2, result)
    
    # Should match contract regex
    match = SUMMARY_PATTERN.match(summary_line)
    assert match, f"SUMMARY line should match regex: {summary_line}"
    
    # Verify fields
    assert match.group(1) == "2"  # files
    assert match.group(3) == "2"  # success
    assert match.group(4) == "0"  # failed
    assert match.group(5) == "1000"  # rows 
    assert match.group(6) == "1"  # skipped_sheets
    assert match.group(7) == "2"  # elapsed_sec (integer formatted without decimal)
    assert match.group(8) == "500"  # throughput_rps (integer formatted without decimal)


def test_render_summary_line_partial_failure():
    """Test SUMMARY rendering for partial failure scenario."""
    start_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2023, 1, 1, 10, 0, 3, tzinfo=timezone.utc)  # 3 seconds elapsed
    
    result = ProcessingResult(
        success_files=1,
        failed_files=2,
        total_inserted_rows=500,
        skipped_sheets=0,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=3.0,
        throughput_rows_per_sec=166.67,
    )
    
    summary_line = render_summary_line(3, result)
    
    # Should match contract regex
    match = SUMMARY_PATTERN.match(summary_line)
    assert match, f"SUMMARY line should match regex: {summary_line}"
    
    # Verify fields
    assert match.group(1) == "3"  # files
    assert match.group(3) == "1"  # success
    assert match.group(4) == "2"  # failed
    assert match.group(5) == "500"  # rows
    assert match.group(6) == "0"  # skipped_sheets
    assert match.group(7) == "3"  # elapsed_sec (integer formatted without decimal)
    assert match.group(8) == "166.67"  # throughput_rps


def test_render_summary_line_zero_files():
    """Test SUMMARY rendering for zero files scenario."""
    start_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)  # 0 seconds elapsed
    
    result = ProcessingResult(
        success_files=0,
        failed_files=0,
        total_inserted_rows=0,
        skipped_sheets=0,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=0.0,
        throughput_rows_per_sec=0.0,
    )
    
    summary_line = render_summary_line(0, result)
    
    # Should match contract regex
    match = SUMMARY_PATTERN.match(summary_line)
    assert match, f"SUMMARY line should match regex: {summary_line}"
    
    # Verify fields
    assert match.group(1) == "0"  # files
    assert match.group(3) == "0"  # success
    assert match.group(4) == "0"  # failed
    assert match.group(5) == "0"  # rows
    assert match.group(6) == "0"  # skipped_sheets
    assert match.group(7) == "0"  # elapsed_sec
    assert match.group(8) == "0"  # throughput_rps


def test_render_summary_line_decimal_precision():
    """Test SUMMARY rendering handles decimal precision correctly."""
    start_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2023, 1, 1, 10, 0, 0, 840000, tzinfo=timezone.utc)  # 0.84 seconds
    
    result = ProcessingResult(
        success_files=1,
        failed_files=0,
        total_inserted_rows=4,
        skipped_sheets=0,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=0.84,
        throughput_rows_per_sec=4761.9,
    )
    
    summary_line = render_summary_line(1, result)
    
    # Should match contract regex
    match = SUMMARY_PATTERN.match(summary_line)
    assert match, f"SUMMARY line should match regex: {summary_line}"
    
    # This should produce the exact line from the contract example
    expected = "SUMMARY files=1/1 success=1 failed=0 rows=4 skipped_sheets=0 elapsed_sec=0.84 throughput_rps=4761.9"
    assert summary_line == expected


def test_render_summary_line_integer_elapsed_time():
    """Test SUMMARY rendering with integer elapsed time (no decimal point)."""
    start_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2023, 1, 1, 10, 0, 5, tzinfo=timezone.utc)  # 5 seconds elapsed
    
    result = ProcessingResult(
        success_files=1,
        failed_files=0,
        total_inserted_rows=1000,
        skipped_sheets=0,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=5.0,
        throughput_rows_per_sec=200.0,
    )
    
    summary_line = render_summary_line(1, result)
    
    # Should match contract regex
    match = SUMMARY_PATTERN.match(summary_line)
    assert match, f"SUMMARY line should match regex: {summary_line}"
    
    # Integer elapsed time should be formatted as "5" not "5.0"
    assert "elapsed_sec=5 " in summary_line
    assert "throughput_rps=200" in summary_line  # No trailing space since it's at end of line


def test_render_summary_line_formats_numbers_correctly():
    """Test that numeric formatting meets contract requirements."""
    start_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2023, 1, 1, 10, 0, 1, 500000, tzinfo=timezone.utc)  # 1.5 seconds
    
    result = ProcessingResult(
        success_files=2,
        failed_files=1,
        total_inserted_rows=100,
        skipped_sheets=2,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=1.5,
        throughput_rows_per_sec=66.666666,  # Will be rounded/formatted appropriately
    )
    
    summary_line = render_summary_line(3, result)
    
    # Should match contract regex
    match = SUMMARY_PATTERN.match(summary_line)
    assert match, f"SUMMARY line should match regex: {summary_line}"
    
    # All integers should be formatted without decimals
    assert "files=3/3" in summary_line
    assert "success=2" in summary_line
    assert "failed=1" in summary_line
    assert "rows=100" in summary_line
    assert "skipped_sheets=2" in summary_line


def test_render_summary_line_handles_very_small_elapsed_time():
    """Test SUMMARY rendering handles very small elapsed times without scientific notation."""
    start_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2023, 1, 1, 10, 0, 0, 50, tzinfo=timezone.utc)  # 50 microseconds
    
    result = ProcessingResult(
        success_files=0,
        failed_files=0,
        total_inserted_rows=0,
        skipped_sheets=0,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=0.00005,  # 50 microseconds, would format as 5e-05
        throughput_rows_per_sec=0.0,
    )
    
    summary_line = render_summary_line(0, result)
    
    # Should match contract regex (no scientific notation)
    match = SUMMARY_PATTERN.match(summary_line)
    assert match, f"SUMMARY line should match regex: {summary_line}"
    
    # Should not contain scientific notation
    assert "e-" not in summary_line
    assert "e+" not in summary_line
    
    # Should format very small number appropriately
    assert "elapsed_sec=0.00005" in summary_line