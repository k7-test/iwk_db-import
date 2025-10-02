from __future__ import annotations

import pytest

from src.models.row_data import RowData


def test_row_data_creation_minimal():
    """Test creating RowData with minimal required fields."""
    row = RowData(
        row_number=1,
        values={"name": "Alice", "age": 30}
    )
    
    assert row.row_number == 1
    assert row.values == {"name": "Alice", "age": 30}
    assert row.raw_values is None
    assert row.invalid is False


def test_row_data_creation_with_optional_fields():
    """Test creating RowData with all fields specified."""
    raw_values = {"name": "Alice", "age": "30", "id": "AUTO_GENERATED"}
    normalized_values = {"name": "Alice", "age": 30}
    
    row = RowData(
        row_number=5,
        values=normalized_values,
        raw_values=raw_values,
        invalid=True
    )
    
    assert row.row_number == 5
    assert row.values == normalized_values
    assert row.raw_values == raw_values
    assert row.invalid is True


def test_row_data_empty_values():
    """Test RowData with empty values dict."""
    row = RowData(
        row_number=1,
        values={}
    )
    
    assert row.row_number == 1
    assert row.values == {}
    assert row.raw_values is None
    assert row.invalid is False


def test_row_data_none_values_in_dict():
    """Test RowData with None values in the dictionary."""
    row = RowData(
        row_number=2,
        values={"name": "Bob", "middle_name": None, "age": 25}
    )
    
    assert row.row_number == 2
    assert row.values["name"] == "Bob"
    assert row.values["middle_name"] is None
    assert row.values["age"] == 25


def test_row_data_immutability():
    """Test that RowData is immutable (frozen dataclass)."""
    row = RowData(
        row_number=1,
        values={"name": "Alice"}
    )
    
    # Should not be able to modify fields
    with pytest.raises(AttributeError):
        row.row_number = 2
    
    with pytest.raises(AttributeError):
        row.values = {"name": "Bob"}
    
    with pytest.raises(AttributeError):
        row.raw_values = {"name": "Alice"}
    
    with pytest.raises(AttributeError):
        row.invalid = True


def test_row_data_values_dict_is_mutable_internally():
    """Test that while RowData is frozen, the internal dict can still be accessed."""
    values = {"name": "Alice", "age": 30}
    row = RowData(row_number=1, values=values)
    
    # The values dict itself should be accessible
    assert row.values is values
    # But we can't reassign the field
    with pytest.raises(AttributeError):
        row.values = {"name": "Bob"}


def test_row_data_type_annotations():
    """Test that various types work correctly in values."""
    from datetime import datetime
    from decimal import Decimal
    
    test_date = datetime(2023, 1, 15, 10, 30)
    test_decimal = Decimal("123.45")
    
    row = RowData(
        row_number=3,
        values={
            "string_col": "test",
            "int_col": 42,
            "float_col": 3.14,
            "bool_col": True,
            "date_col": test_date,
            "decimal_col": test_decimal,
            "none_col": None
        }
    )
    
    assert row.values["string_col"] == "test"
    assert row.values["int_col"] == 42
    assert row.values["float_col"] == 3.14
    assert row.values["bool_col"] is True
    assert row.values["date_col"] == test_date
    assert row.values["decimal_col"] == test_decimal
    assert row.values["none_col"] is None


def test_row_data_equality():
    """Test RowData equality comparison."""
    row1 = RowData(
        row_number=1,
        values={"name": "Alice", "age": 30}
    )
    
    row2 = RowData(
        row_number=1,
        values={"name": "Alice", "age": 30}
    )
    
    row3 = RowData(
        row_number=2,
        values={"name": "Alice", "age": 30}
    )
    
    assert row1 == row2
    assert row1 != row3


def test_row_data_with_raw_values_different_types():
    """Test RowData where raw_values contains different types than normalized values."""
    row = RowData(
        row_number=1,
        values={"age": 30, "active": True},  # normalized
        raw_values={"age": "30", "active": "yes"}  # original string values
    )
    
    assert row.values["age"] == 30
    assert row.values["active"] is True
    assert row.raw_values["age"] == "30"
    assert row.raw_values["active"] == "yes"