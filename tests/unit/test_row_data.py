from __future__ import annotations

import pytest

from src.models.row_data import RowData


def test_row_data_creation_basic():
    """Test basic RowData creation with required fields."""
    row = RowData(
        row_number=1,
        values={"id": 123, "name": "Alice"}
    )
    assert row.row_number == 1
    assert row.values == {"id": 123, "name": "Alice"}
    assert row.raw_values is None
    assert row.invalid is False


def test_row_data_creation_with_optional_fields():
    """Test RowData creation with all optional fields."""
    raw_vals = {"id": "123", "name": " Alice "}
    row = RowData(
        row_number=5,
        values={"id": 123, "name": "Alice"},
        raw_values=raw_vals,
        invalid=True
    )
    assert row.row_number == 5
    assert row.values == {"id": 123, "name": "Alice"}
    assert row.raw_values == raw_vals
    assert row.invalid is True


def test_row_data_immutable():
    """Test that RowData is immutable (frozen=True)."""
    row = RowData(
        row_number=1,
        values={"id": 123}
    )
    with pytest.raises(AttributeError):
        row.row_number = 2  # type: ignore
    with pytest.raises(AttributeError):
        row.invalid = True  # type: ignore


def test_row_data_empty_values():
    """Test RowData with empty values dict."""
    row = RowData(
        row_number=10,
        values={}
    )
    assert row.row_number == 10
    assert row.values == {}


def test_row_data_none_values_in_dict():
    """Test RowData with None values in the values dict."""
    row = RowData(
        row_number=3,
        values={"id": 123, "optional_field": None, "name": "Bob"}
    )
    assert row.values["id"] == 123
    assert row.values["optional_field"] is None
    assert row.values["name"] == "Bob"


def test_row_data_complex_values():
    """Test RowData with complex value types."""
    from datetime import datetime
    
    dt = datetime(2023, 5, 15, 10, 30, 0)
    row = RowData(
        row_number=7,
        values={
            "id": 456,
            "name": "Charlie",
            "score": 95.5,
            "active": True,
            "created_at": dt,
            "tags": ["tag1", "tag2"]
        }
    )
    
    assert row.values["id"] == 456
    assert row.values["name"] == "Charlie"
    assert row.values["score"] == 95.5
    assert row.values["active"] is True
    assert row.values["created_at"] == dt
    assert row.values["tags"] == ["tag1", "tag2"]
