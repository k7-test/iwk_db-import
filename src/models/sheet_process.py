from __future__ import annotations

from dataclasses import dataclass

from .config_models import SheetMappingConfig
from .row_data import RowData

"""SheetProcess model for Excel -> PostgreSQL import tool.

This module defines the SheetProcess domain model based on data-model.md specifications.
SheetProcess represents the processing unit for a single Excel sheet.

Phase: 3.3 (Domain Models)
Task: T016 - Implement SheetProcess dataclass
"""

__all__ = [
    "SheetProcess",
]


@dataclass(frozen=True)
class SheetProcess:
    """Processing unit for a single Excel sheet (FR-003).
    
    Represents the complete processing context for one Excel sheet, including
    its configuration, normalized data rows, and processing results.
    """
    sheet_name: str  # Excel sheet name
    table_name: str  # Target database table name
    mapping: SheetMappingConfig  # Configuration reference
    rows: list[RowData] | None = None  # Normalized row data (FR-004, FR-005)
    # Auto-sequence/FK propagation excluded columns (FR-006, FR-007, FR-021)
    ignored_columns: set[str] | None = None
    inserted_rows: int = 0  # Successfully committed row count (FR-022)
    error: str | None = None  # Sheet-level error message (FR-008)