from __future__ import annotations

import json

from src.models.error_record import ErrorRecord

"""Unit tests for ErrorRecord model (T018)."""


def test_error_record_row_minus_one_support():
    """Test that ErrorRecord properly supports row=-1 for file-level errors."""
    rec = ErrorRecord.create(
        file="problematic.xlsx",
        sheet="Sheet1",
        row=-1,  # Sentinel value for file-level error
        error_type="FILE_LEVEL_FATAL",
        db_message="Database connection failed during file processing"
    )
    
    # Verify the record is created with row=-1
    assert rec.row == -1
    assert rec.file == "problematic.xlsx"
    assert rec.sheet == "Sheet1"
    assert rec.error_type == "FILE_LEVEL_FATAL"
    assert rec.db_message == "Database connection failed during file processing"
    
    # Verify JSON serialization includes row=-1
    line = rec.to_json_line()
    data = json.loads(line)
    assert data["row"] == -1
    assert data["file"] == "problematic.xlsx"
    assert data["sheet"] == "Sheet1"
    assert data["error_type"] == "FILE_LEVEL_FATAL"
    assert "timestamp" in data and data["timestamp"].endswith("Z")
    assert set(data.keys()) == {"timestamp", "file", "sheet", "row", "error_type", "db_message"}


def test_error_record_positive_row_number():
    """Test that ErrorRecord works with positive row numbers (normal case)."""
    rec = ErrorRecord.create(
        file="normal.xlsx",
        sheet="Data",
        row=42,
        error_type="CONSTRAINT_VIOLATION",
        db_message="duplicate key value"
    )
    
    assert rec.row == 42
    line = rec.to_json_line()
    data = json.loads(line)
    assert data["row"] == 42


def test_error_record_zero_row():
    """Test that ErrorRecord handles row=0 (edge case)."""
    rec = ErrorRecord.create(
        file="edge.xlsx",
        sheet="Headers",
        row=0,
        error_type="HEADER_ERROR",
        db_message="invalid header format"
    )
    
    assert rec.row == 0
    line = rec.to_json_line()
    data = json.loads(line)
    assert data["row"] == 0