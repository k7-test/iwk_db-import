from __future__ import annotations

"""Error log JSON schema contract test (FR-030)."""
import json
import pathlib

import pytest

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore

SCHEMA_PATH = pathlib.Path("specs/001-excel-postgressql-excel/contracts/error_log_schema.json")

@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_error_log_schema_valid_example():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    record = {
        "timestamp": "2025-09-26T10:12:33Z",
        "file": "customers.xlsx",
        "sheet": "Orders",
        "row": 2,
        "error_type": "CONSTRAINT_VIOLATION",
        "db_message": "duplicate key value violates unique constraint 'orders_pkey'"
    }
    jsonschema.validate(record, schema)  # type: ignore

@pytest.mark.skipif(jsonschema is None, reason="jsonschema library not installed")
def test_error_log_schema_rejects_extra_key():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    record = {
        "timestamp": "2025-09-26T10:12:33Z",
        "file": "customers.xlsx",
        "sheet": "Orders",
        "row": 2,
        "error_type": "CONSTRAINT_VIOLATION",
        "db_message": "duplicate key value violates unique constraint 'orders_pkey'",
        "extra": "not allowed"
    }
    with pytest.raises(Exception):  # jsonschema.exceptions.ValidationError
        jsonschema.validate(record, schema)  # type: ignore
