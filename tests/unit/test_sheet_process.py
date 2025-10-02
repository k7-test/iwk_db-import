from __future__ import annotations

import pytest
from src.models.sheet_process import SheetProcess
from src.models.config_models import SheetMappingConfig
from src.models.row_data import RowData


def test_sheet_process_creation_minimal():
    """Test SheetProcess creation with minimal required fields."""
    mapping = SheetMappingConfig(
        sheet_name="TestSheet",
        table_name="test_table",
        sequence_columns=set(),
        fk_propagation_columns=set()
    )
    
    sheet = SheetProcess(
        sheet_name="TestSheet",
        table_name="test_table",
        mapping=mapping
    )
    
    assert sheet.sheet_name == "TestSheet"
    assert sheet.table_name == "test_table"
    assert sheet.mapping == mapping
    assert sheet.rows is None
    assert sheet.ignored_columns is None
    assert sheet.inserted_rows == 0
    assert sheet.error is None


def test_sheet_process_creation_with_rows():
    """Test SheetProcess creation with row data."""
    mapping = SheetMappingConfig(
        sheet_name="DataSheet",
        table_name="data_table",
        sequence_columns={"id"},
        fk_propagation_columns=set()
    )
    
    rows = [
        RowData(row_number=1, values={"name": "Alice", "age": 25}),
        RowData(row_number=2, values={"name": "Bob", "age": 30})
    ]
    
    ignored_cols = {"id", "created_at"}
    
    sheet = SheetProcess(
        sheet_name="DataSheet",
        table_name="data_table",
        mapping=mapping,
        rows=rows,
        ignored_columns=ignored_cols
    )
    
    assert sheet.sheet_name == "DataSheet"
    assert sheet.table_name == "data_table"
    assert sheet.mapping == mapping
    assert sheet.rows == rows
    assert len(sheet.rows) == 2
    assert sheet.ignored_columns == ignored_cols
    assert sheet.inserted_rows == 0
    assert sheet.error is None


def test_sheet_process_with_processing_results():
    """Test SheetProcess with processing results (inserted_rows, error)."""
    mapping = SheetMappingConfig(
        sheet_name="ProcessedSheet",
        table_name="processed_table",
        sequence_columns=set(),
        fk_propagation_columns={"parent_id"}
    )
    
    sheet = SheetProcess(
        sheet_name="ProcessedSheet",
        table_name="processed_table",
        mapping=mapping,
        inserted_rows=150,
        error="Database connection failed"
    )
    
    assert sheet.sheet_name == "ProcessedSheet"
    assert sheet.table_name == "processed_table"
    assert sheet.mapping == mapping
    assert sheet.inserted_rows == 150
    assert sheet.error == "Database connection failed"


def test_sheet_process_immutable():
    """Test that SheetProcess is immutable (frozen=True)."""
    mapping = SheetMappingConfig(
        sheet_name="ImmutableSheet",
        table_name="immutable_table",
        sequence_columns=set(),
        fk_propagation_columns=set()
    )
    
    sheet = SheetProcess(
        sheet_name="ImmutableSheet",
        table_name="immutable_table",
        mapping=mapping
    )
    
    with pytest.raises(AttributeError):
        sheet.sheet_name = "NewName"  # type: ignore
    with pytest.raises(AttributeError):
        sheet.inserted_rows = 100  # type: ignore


def test_sheet_process_empty_rows_list():
    """Test SheetProcess with empty rows list."""
    mapping = SheetMappingConfig(
        sheet_name="EmptySheet",
        table_name="empty_table",
        sequence_columns=set(),
        fk_propagation_columns=set()
    )
    
    sheet = SheetProcess(
        sheet_name="EmptySheet",
        table_name="empty_table",
        mapping=mapping,
        rows=[]
    )
    
    assert sheet.rows == []
    assert len(sheet.rows) == 0


def test_sheet_process_empty_ignored_columns():
    """Test SheetProcess with empty ignored_columns set."""
    mapping = SheetMappingConfig(
        sheet_name="NoIgnoredCols",
        table_name="no_ignored_table",
        sequence_columns=set(),
        fk_propagation_columns=set()
    )
    
    sheet = SheetProcess(
        sheet_name="NoIgnoredCols",
        table_name="no_ignored_table",
        mapping=mapping,
        ignored_columns=set()
    )
    
    assert sheet.ignored_columns == set()


def test_sheet_process_complex_scenario():
    """Test SheetProcess with complex real-world-like scenario."""
    mapping = SheetMappingConfig(
        sheet_name="ComplexSheet",
        table_name="complex_table",
        sequence_columns={"id", "uuid"},
        fk_propagation_columns={"parent_id", "category_id"}
    )
    
    rows = [
        RowData(
            row_number=1,
            values={"name": "Product A", "price": 99.99, "active": True},
            raw_values={"name": " Product A ", "price": "99.99", "active": "true"}
        ),
        RowData(
            row_number=3,  # Skipped row 2 due to validation
            values={"name": "Product B", "price": 149.50, "active": False},
            invalid=False
        )
    ]
    
    ignored_cols = {"id", "uuid", "parent_id", "category_id", "created_at", "updated_at"}
    
    sheet = SheetProcess(
        sheet_name="ComplexSheet",
        table_name="complex_table",
        mapping=mapping,
        rows=rows,
        ignored_columns=ignored_cols,
        inserted_rows=2
    )
    
    assert sheet.sheet_name == "ComplexSheet"
    assert sheet.table_name == "complex_table"
    assert len(sheet.rows) == 2
    assert sheet.rows[0].row_number == 1
    assert sheet.rows[0].raw_values is not None
    assert sheet.rows[1].row_number == 3
    assert sheet.inserted_rows == 2
    assert len(sheet.ignored_columns) == 6
    assert "id" in sheet.ignored_columns
    assert "parent_id" in sheet.ignored_columns