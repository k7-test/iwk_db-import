from __future__ import annotations

from dataclasses import dataclass
from typing import Any

"""RowData model for Excel -> PostgreSQL import tool.

This module defines the RowData domain model based on data-model.md specifications.
RowData represents a single row of normalized data after Excel processing.

Phase: 3.3 (Domain Models)
Task: T016 - Implement RowData dataclass (dependency for SheetProcess)
"""

__all__ = [
    "RowData",
]


@dataclass(frozen=True)
class RowData:
    """Logical representation of a single row after Excel normalization (FR-004, FR-005).
    
    Represents one row of data from Excel after header processing and normalization.
    The row_number refers to the original Excel row number (3rd row = 1st data row).
    """
    row_number: int  # Excel row number (starting from 3rd row = 1st data)
    values: dict[str, Any]  # Column name -> normalized value (excluding ignored columns)
    raw_values: dict[str, Any] | None = None  # Original values for debug/warning purposes
    invalid: bool = False  # Row-level validation flag (future extension)
