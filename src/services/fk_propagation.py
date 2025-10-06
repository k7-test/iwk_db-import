from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from src.models.config_models import ImportConfig

"""FK propagation service for conditional RETURNING logic (R-007).

This service implements the FK propagation logic that determines when RETURNING
is needed and manages the mapping of parent PKs to child FK values.

R-007 Decision: Use RETURNING only when parent PK is needed for FK propagation.
- Default: no RETURNING 
- Parent table → child table: use RETURNING to get generated PKs, build in-memory map
- Child records receive propagated FK values from parent PK map

Phase: 3.4 (Core Services)
Task: T022 - Implement FK propagation + conditional RETURNING logic
"""


class FKPropagationError(Exception):
    """Exception raised during FK propagation operations."""
    pass


@dataclass(frozen=True)
class ParentPKResult:
    """Result of parent table insert with RETURNING data."""
    table_name: str
    returned_values: list[tuple[Any, ...]]  # Raw RETURNING result tuples
    pk_column_index: int  # Index of PK column in returned_values tuples


@dataclass(frozen=True)
class FKPropagationMap:
    """Mapping configuration for FK propagation."""
    parent_table: str
    parent_identifier_column: str  # Column used to match parent records
    child_fk_column: str  # FK column in child table
    parent_pk_column: str  # PK column in parent table


def needs_returning(
    table_name: str,
    config: ImportConfig,
    processed_tables: set[str]
) -> bool:
    """Determine if table insert needs RETURNING clause for FK propagation.
    
    Per R-007: Use RETURNING only when parent PK is needed for child FK propagation.
    
    Parameters
    ----------
    table_name: Target table being inserted
    config: Import configuration with FK propagation mappings
    processed_tables: Set of tables already processed (to avoid circular dependencies)
    
    Returns
    -------
    bool: True if RETURNING clause should be used, False otherwise
    """
    # Check if any child tables reference this table's PK
    fp = config.fk_propagations
    # list 新形式
    if isinstance(fp, list):
        for entry in fp:
            try:
                parent_ref = entry.get("parent")
                child_ref = entry.get("child")
            except AttributeError:
                continue
            if not parent_ref or not child_ref or "." not in parent_ref or "." not in child_ref:
                continue
            parent_table, _ = parent_ref.split(".", 1)
            if parent_table != table_name:
                continue
            child_table, _ = child_ref.split(".", 1)
            if child_table not in processed_tables:
                return True
    # 旧 dict 形式
    elif isinstance(fp, dict):
        for fk_mapping_key, child_reference in fp.items():
            if "." in fk_mapping_key:
                parent_table, _ = fk_mapping_key.split(".", 1)
                if parent_table == table_name:
                    if "." in child_reference:
                        child_table, _ = child_reference.split(".", 1)
                        if child_table not in processed_tables:
                            return True
    
    return False


def build_fk_propagation_maps(config: ImportConfig) -> list[FKPropagationMap]:
    """Build FK propagation mapping configurations from config.
    
    Parameters
    ----------
    config: Import configuration
    
    Returns
    -------
    list[FKPropagationMap]: List of FK propagation mappings
    """
    maps = []
    
    fp = config.fk_propagations
    def _append(parent_ref: str, child_ref: str):
        if "." not in parent_ref or "." not in child_ref:
            return
        parent_table, parent_identifier = parent_ref.split(".", 1)
        child_table, child_fk_column = child_ref.split(".", 1)
        # parent_pk_column 推定: sequences に parent_identifier が key として存在すればそれを PK とみなす
        parent_pk_column = parent_identifier
        maps.append(FKPropagationMap(
            parent_table=parent_table,
            parent_identifier_column=parent_identifier,
            child_fk_column=child_fk_column,
            parent_pk_column=parent_pk_column
        ))
    if isinstance(fp, list):
        for entry in fp:
            if not isinstance(entry, dict):
                continue
            parent_ref = entry.get("parent")
            child_ref = entry.get("child")
            if parent_ref and child_ref:
                _append(parent_ref, child_ref)
    elif isinstance(fp, dict):
        for k, v in fp.items():
            _append(k, v)
    
    return maps


def build_parent_pk_map(
    parent_result: ParentPKResult,
    parent_identifier_column_index: int
) -> dict[Any, Any]:
    """Build lookup map from parent identifier values to generated PKs.
    
    Parameters
    ----------
    parent_result: Result from parent table insert with RETURNING data
    parent_identifier_column_index: Index of identifier column in returned tuples
    
    Returns
    -------
    dict[Any, Any]: Map from identifier value to generated PK value
    """
    pk_map = {}
    
    for row in parent_result.returned_values:
        if len(row) > max(parent_result.pk_column_index, parent_identifier_column_index):
            identifier_value = row[parent_identifier_column_index]
            pk_value = row[parent_result.pk_column_index]
            pk_map[identifier_value] = pk_value
    
    return pk_map


def propagate_foreign_keys(
    child_rows: list[tuple[Any, ...]],
    fk_mapping: FKPropagationMap,
    parent_pk_map: dict[Any, Any],
    child_fk_column_index: int,
    child_identifier_column_index: int
) -> list[tuple[Any, ...]]:
    """Propagate FK values from parent PK map to child rows.
    
    Parameters
    ----------
    child_rows: Original child table rows
    fk_mapping: FK propagation mapping configuration
    parent_pk_map: Map from parent identifier to generated PK
    child_fk_column_index: Index of FK column in child rows
    child_identifier_column_index: Index of identifier column in child rows
    
    Returns
    -------
    list[tuple[Any, ...]]: Child rows with propagated FK values
    
    Raises
    ------
    FKPropagationError: If identifier not found in parent map
    """
    propagated_rows = []
    
    for row in child_rows:
        if len(row) <= max(child_fk_column_index, child_identifier_column_index):
            raise FKPropagationError(
                f"Row has insufficient columns: {len(row)} columns, "
                f"need at least {max(child_fk_column_index, child_identifier_column_index) + 1}"
            )
        
        # Get the identifier value from child row
        identifier_value = row[child_identifier_column_index]
        
        # Look up the corresponding parent PK
        if identifier_value not in parent_pk_map:
            raise FKPropagationError(
                f"Parent identifier '{identifier_value}' not found in parent PK map. "
                f"Available keys: {list(parent_pk_map.keys())}"
            )
        
        parent_pk = parent_pk_map[identifier_value]
        
        # Replace the FK column value with the parent PK
        row_list = list(row)
        row_list[child_fk_column_index] = parent_pk
        propagated_rows.append(tuple(row_list))
    
    return propagated_rows


def get_column_index(column_name: str, columns: Sequence[str]) -> int:
    """Get index of column by name.
    
    Parameters
    ----------
    column_name: Name of column to find
    columns: Sequence of column names
    
    Returns
    -------
    int: Index of column
    
    Raises
    ------
    FKPropagationError: If column not found
    """
    try:
        return columns.index(column_name)
    except ValueError:
        raise FKPropagationError(
            f"Column '{column_name}' not found in columns: {list(columns)}"
        ) from None