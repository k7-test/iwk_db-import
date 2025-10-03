from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.models.excel_file import ExcelFile, FileStatus


def test_file_status_enum_values():
    """Test FileStatus enum has correct values and state transitions."""
    assert FileStatus.PENDING.value == "pending"
    assert FileStatus.PROCESSING.value == "processing"
    assert FileStatus.SUCCESS.value == "success"
    assert FileStatus.FAILED.value == "failed"
    
    # Test all expected values are present
    expected_values = {"pending", "processing", "success", "failed"}
    actual_values = {status.value for status in FileStatus}
    assert actual_values == expected_values


def test_excel_file_creation_with_defaults():
    """Test ExcelFile can be created with required fields and proper defaults."""
    file_path = Path("/test/sample.xlsx")
    excel_file = ExcelFile(
        path=file_path,
        name="sample.xlsx",
        sheets=[]
    )
    
    assert excel_file.path == file_path
    assert excel_file.name == "sample.xlsx"
    assert excel_file.sheets == []
    assert excel_file.start_time is None
    assert excel_file.end_time is None
    assert excel_file.status == FileStatus.PENDING
    assert excel_file.total_rows == 0
    assert excel_file.skipped_sheets == 0
    assert excel_file.error is None


def test_excel_file_creation_with_all_fields():
    """Test ExcelFile can be created with all fields specified."""
    file_path = Path("/test/complete.xlsx")
    start_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
    end_time = datetime(2025, 1, 1, 10, 5, 0, tzinfo=UTC)
    
    excel_file = ExcelFile(
        path=file_path,
        name="complete.xlsx",
        sheets=[],  # Would contain SheetProcess objects when T016 is implemented
        start_time=start_time,
        end_time=end_time,
        status=FileStatus.SUCCESS,
        total_rows=1500,
        skipped_sheets=2,
        error=None
    )
    
    assert excel_file.path == file_path
    assert excel_file.name == "complete.xlsx"
    assert excel_file.sheets == []
    assert excel_file.start_time == start_time
    assert excel_file.end_time == end_time
    assert excel_file.status == FileStatus.SUCCESS
    assert excel_file.total_rows == 1500
    assert excel_file.skipped_sheets == 2
    assert excel_file.error is None


def test_excel_file_with_error():
    """Test ExcelFile can represent failed processing with error message."""
    excel_file = ExcelFile(
        path=Path("/test/failed.xlsx"),
        name="failed.xlsx",
        sheets=[],
        status=FileStatus.FAILED,
        error="Connection timeout during database insert"
    )
    
    assert excel_file.status == FileStatus.FAILED
    assert excel_file.error == "Connection timeout during database insert"


def test_excel_file_frozen_dataclass():
    """Test that ExcelFile is frozen and immutable."""
    excel_file = ExcelFile(
        path=Path("/test/frozen.xlsx"),
        name="frozen.xlsx",
        sheets=[]
    )
    
    # Should not be able to modify fields after creation
    with pytest.raises(AttributeError):
        excel_file.status = FileStatus.PROCESSING  # type: ignore[misc]
        
    with pytest.raises(AttributeError):
        excel_file.total_rows = 100  # type: ignore[misc]


def test_file_status_state_transitions():
    """Test the documented state transitions for FileStatus."""
    # Test that we can create files in each expected state
    pending_file = ExcelFile(
        path=Path("/test/pending.xlsx"),
        name="pending.xlsx", 
        sheets=[],
        status=FileStatus.PENDING
    )
    assert pending_file.status == FileStatus.PENDING
    
    processing_file = ExcelFile(
        path=Path("/test/processing.xlsx"),
        name="processing.xlsx",
        sheets=[],
        status=FileStatus.PROCESSING
    )
    assert processing_file.status == FileStatus.PROCESSING
    
    success_file = ExcelFile(
        path=Path("/test/success.xlsx"), 
        name="success.xlsx",
        sheets=[],
        status=FileStatus.SUCCESS
    )
    assert success_file.status == FileStatus.SUCCESS
    
    failed_file = ExcelFile(
        path=Path("/test/failed.xlsx"),
        name="failed.xlsx", 
        sheets=[],
        status=FileStatus.FAILED
    )
    assert failed_file.status == FileStatus.FAILED