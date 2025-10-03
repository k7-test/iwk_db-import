from __future__ import annotations

"""Error log row=-1 sentinel contract test (T007).

Validates that the error log JSON schema accepts row=-1 as a sentinel value
for file-level fatal errors where the specific row cannot be determined.
"""
import json
import pathlib

import pytest

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore

SCHEMA_PATH = pathlib.Path("specs/001-excel-postgressql-excel/contracts/error_log_schema.json")


@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_error_log_schema_accepts_row_minus_one():
    """Test that error log schema accepts row=-1 for file-level fatal errors."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    record = {
        "timestamp": "2025-09-26T10:12:33Z",
        "file": "customers.xlsx",
        "sheet": "Orders",
        "row": -1,  # Sentinel value for unknown row
        "error_type": "FILE_LEVEL_FATAL",
        "db_message": "Database connection failed during file processing"
    }
    # Should not raise ValidationError
    jsonschema.validate(record, schema)  # type: ignore


@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_error_log_schema_rejects_row_less_than_minus_one():
    """Test that error log schema rejects row values less than -1."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    record = {
        "timestamp": "2025-09-26T10:12:33Z",
        "file": "customers.xlsx",
        "sheet": "Orders",
        "row": -2,  # Invalid: less than minimum -1
        "error_type": "CONSTRAINT_VIOLATION",
        "db_message": "duplicate key value violates unique constraint"
    }
    with pytest.raises(Exception):  # jsonschema.exceptions.ValidationError
        jsonschema.validate(record, schema)  # type: ignore


@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_error_log_schema_accepts_positive_row_numbers():
    """Test that error log schema accepts positive row numbers (normal case)."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    record = {
        "timestamp": "2025-09-26T10:12:33Z",
        "file": "customers.xlsx",
        "sheet": "Orders",
        "row": 42,  # Normal positive row number
        "error_type": "CONSTRAINT_VIOLATION",
        "db_message": "duplicate key value violates unique constraint"
    }
    # Should not raise ValidationError
    jsonschema.validate(record, schema)  # type: ignore