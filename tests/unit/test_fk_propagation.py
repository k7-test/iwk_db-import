from __future__ import annotations

import pytest

from src.models.config_models import DatabaseConfig, ImportConfig, SheetMappingConfig
from src.services.fk_propagation import (
    FKPropagationError,
    FKPropagationMap,
    ParentPKResult,
    build_fk_propagation_maps,
    build_parent_pk_map,
    get_column_index,
    needs_returning,
    propagate_foreign_keys,
)

"""Unit tests for FK propagation service (T022).

Tests the FK propagation logic including:
- Conditional RETURNING determination (R-007)
- Parent PK map building
- FK value propagation to child records
- Error handling for missing references
"""


@pytest.fixture
def sample_config() -> ImportConfig:
    """Sample config with FK propagation setup."""
    return ImportConfig(
        source_directory="test_data",
        sheet_mappings={
            "Customers": SheetMappingConfig(
                sheet_name="Customers",
                table_name="customers",
                sequence_columns={"id"},
                fk_propagation_columns=set()
            ),
            "Orders": SheetMappingConfig(
                sheet_name="Orders",
                table_name="orders", 
                sequence_columns={"id"},
                fk_propagation_columns={"customer_id"}
            )
        },
        sequences={"customers.id": "customer_id_seq", "orders.id": "order_id_seq"},
        fk_propagations={
            "customers.name": "orders.customer_id"  # customers.name -> orders.customer_id
        },
        timezone="UTC",
        database=DatabaseConfig(
            host=None, port=None, user=None, password=None, database=None, dsn=None
        )
    )


def test_needs_returning_when_parent_has_unprocessed_children(sample_config: ImportConfig) -> None:
    """Test needs_returning returns True when table is parent with unprocessed children."""
    processed_tables: set[str] = set()
    
    # customers table should need RETURNING because orders table references it and isn't processed
    assert needs_returning("customers", sample_config, processed_tables) is True


def test_needs_returning_when_parent_children_already_processed(
    sample_config: ImportConfig,
) -> None:
    """Test needs_returning returns False when child tables already processed."""
    processed_tables = {"orders"}  # orders already processed
    
    # customers should not need RETURNING because orders is already processed
    assert needs_returning("customers", sample_config, processed_tables) is False


def test_needs_returning_when_not_parent_table(sample_config: ImportConfig) -> None:
    """Test needs_returning returns False when table is not a parent."""
    processed_tables: set[str] = set()
    
    # orders table is not a parent, should not need RETURNING
    assert needs_returning("orders", sample_config, processed_tables) is False


def test_needs_returning_with_no_fk_propagations() -> None:
    """Test needs_returning returns False when no FK propagations configured."""
    config = ImportConfig(
        source_directory="test_data",
        sheet_mappings={},
        sequences={},
        fk_propagations={},  # No FK propagations
        timezone="UTC",
        database=DatabaseConfig(
            host=None, port=None, user=None, password=None, database=None, dsn=None
        )
    )
    
    assert needs_returning("any_table", config, set()) is False


def test_build_fk_propagation_maps(sample_config: ImportConfig) -> None:
    """Test building FK propagation maps from config."""
    maps = build_fk_propagation_maps(sample_config)
    
    assert len(maps) == 1
    
    fk_map = maps[0]
    assert fk_map.parent_table == "customers"
    assert fk_map.parent_identifier_column == "name"
    assert fk_map.child_fk_column == "customer_id" 
    assert fk_map.parent_pk_column == "id"  # Default assumption


def test_build_fk_propagation_maps_with_invalid_format() -> None:
    """Test building FK propagation maps with invalid format strings."""
    config = ImportConfig(
        source_directory="test_data",
        sheet_mappings={},
        sequences={},
        fk_propagations={
            "invalid_format": "also_invalid",  # No dots
            "parent.col": "no_dot_here",      # Child missing dot
            "no_dot": "child.col"             # Parent missing dot
        },
        timezone="UTC",
        database=DatabaseConfig(
            host=None, port=None, user=None, password=None, database=None, dsn=None
        )
    )
    
    maps = build_fk_propagation_maps(config)
    assert len(maps) == 0  # All invalid formats should be skipped


def test_build_parent_pk_map() -> None:
    """Test building parent PK lookup map from RETURNING results."""
    parent_result = ParentPKResult(
        table_name="customers",
        returned_values=[
            (101, "Alice", "alice@example.com"),
            (102, "Bob", "bob@example.com"),
            (103, "Charlie", "charlie@example.com")
        ],
        pk_column_index=0  # First column is PK
    )
    
    # Name column is at index 1
    name_column_index = 1
    
    pk_map = build_parent_pk_map(parent_result, name_column_index)
    
    expected_map = {
        "Alice": 101,
        "Bob": 102,
        "Charlie": 103
    }
    
    assert pk_map == expected_map


def test_build_parent_pk_map_with_insufficient_columns() -> None:
    """Test building parent PK map with rows that have insufficient columns."""
    parent_result = ParentPKResult(
        table_name="customers",
        returned_values=[
            (101,),  # Only one column, but we need at least 2
        ],
        pk_column_index=0
    )
    
    pk_map = build_parent_pk_map(parent_result, 1)  # Try to access index 1
    
    # Should gracefully handle insufficient columns by skipping rows
    assert pk_map == {}


def test_propagate_foreign_keys() -> None:
    """Test propagating FK values from parent PK map to child records."""
    fk_mapping = FKPropagationMap(
        parent_table="customers",
        parent_identifier_column="name",
        child_fk_column="customer_id",
        parent_pk_column="id"
    )
    
    parent_pk_map = {
        "Alice": 101,
        "Bob": 102,
        "Charlie": 103
    }
    
    child_rows = [
        (None, "Alice", 1500.00),    # (id, customer_id, amount)
        (None, "Bob", 2500.00),
        (None, "Alice", 800.00),
        (None, "Charlie", 1200.00)
    ]
    
    # Column indices
    child_fk_column_index = 1      # customer_id column
    child_identifier_column_index = 1  # Same as FK column in this case
    
    propagated_rows = propagate_foreign_keys(
        child_rows=child_rows,
        fk_mapping=fk_mapping,
        parent_pk_map=parent_pk_map,
        child_fk_column_index=child_fk_column_index,
        child_identifier_column_index=child_identifier_column_index
    )
    
    expected_rows = [
        (None, 101, 1500.00),  # Alice -> 101
        (None, 102, 2500.00),  # Bob -> 102
        (None, 101, 800.00),   # Alice -> 101
        (None, 103, 1200.00)   # Charlie -> 103
    ]
    
    assert propagated_rows == expected_rows


def test_propagate_foreign_keys_missing_parent_reference() -> None:
    """Test propagating FK values when child references non-existent parent."""
    fk_mapping = FKPropagationMap(
        parent_table="customers",
        parent_identifier_column="name",
        child_fk_column="customer_id",
        parent_pk_column="id"
    )
    
    parent_pk_map = {
        "Alice": 101,
        "Bob": 102
        # Charlie is missing
    }
    
    child_rows = [
        (None, "Charlie", 1200.00)  # References non-existent Charlie
    ]
    
    with pytest.raises(FKPropagationError, match="Parent identifier 'Charlie' not found"):
        propagate_foreign_keys(
            child_rows=child_rows,
            fk_mapping=fk_mapping,
            parent_pk_map=parent_pk_map,
            child_fk_column_index=1,
            child_identifier_column_index=1
        )


def test_propagate_foreign_keys_insufficient_columns() -> None:
    """Test propagating FK values when child rows have insufficient columns."""
    fk_mapping = FKPropagationMap(
        parent_table="customers",
        parent_identifier_column="name",
        child_fk_column="customer_id",
        parent_pk_column="id"
    )
    
    parent_pk_map = {"Alice": 101}
    
    child_rows = [
        ("Alice",)  # Only one column, but we need at least 2
    ]
    
    with pytest.raises(FKPropagationError, match="Row has insufficient columns"):
        propagate_foreign_keys(
            child_rows=child_rows,
            fk_mapping=fk_mapping,
            parent_pk_map=parent_pk_map,
            child_fk_column_index=1,
            child_identifier_column_index=0
        )


def test_get_column_index() -> None:
    """Test getting column index by name."""
    columns = ["id", "name", "email", "customer_id"]
    
    assert get_column_index("id", columns) == 0
    assert get_column_index("name", columns) == 1
    assert get_column_index("email", columns) == 2
    assert get_column_index("customer_id", columns) == 3


def test_get_column_index_not_found() -> None:
    """Test getting column index when column doesn't exist."""
    columns = ["id", "name", "email"]
    
    with pytest.raises(FKPropagationError, match="Column 'missing' not found"):
        get_column_index("missing", columns)


def test_multiple_fk_propagation_maps() -> None:
    """Test building multiple FK propagation maps."""
    config = ImportConfig(
        source_directory="test_data",
        sheet_mappings={},
        sequences={},
        fk_propagations={
            "customers.name": "orders.customer_id",
            "products.sku": "order_items.product_id",
            "categories.name": "products.category_id"
        },
        timezone="UTC",
        database=DatabaseConfig(
            host=None, port=None, user=None, password=None, database=None, dsn=None
        )
    )
    
    maps = build_fk_propagation_maps(config)
    
    assert len(maps) == 3
    
    # Sort by parent table for consistent testing
    maps_by_parent = {m.parent_table: m for m in maps}
    
    assert "customers" in maps_by_parent
    assert maps_by_parent["customers"].child_fk_column == "customer_id"
    
    assert "products" in maps_by_parent
    assert maps_by_parent["products"].child_fk_column == "product_id"
    
    assert "categories" in maps_by_parent
    assert maps_by_parent["categories"].child_fk_column == "category_id"


def test_needs_returning_with_multiple_children() -> None:
    """Test needs_returning when parent table has multiple child references."""
    config = ImportConfig(
        source_directory="test_data",
        sheet_mappings={},
        sequences={},
        fk_propagations={
            "customers.name": "orders.customer_id",
            "customers.email": "addresses.customer_id"  # Same parent, multiple children
        },
        timezone="UTC",
        database=DatabaseConfig(
            host=None, port=None, user=None, password=None, database=None, dsn=None
        )
    )
    
    processed_tables: set[str] = set()
    
    # Should need RETURNING because both orders and addresses reference customers
    assert needs_returning("customers", config, processed_tables) is True
    
    # After processing one child, should still need RETURNING for the other
    processed_tables.add("orders")
    assert needs_returning("customers", config, processed_tables) is True
    
    # After processing both children, should not need RETURNING
    processed_tables.add("addresses")
    assert needs_returning("customers", config, processed_tables) is False