from __future__ import annotations

from dataclasses import dataclass
from typing import Any

"""RowData model for Excel row representation.

T017 [P] Implementation of RowData dataclass as defined in data-model.md.
This represents a single row of data after normalization from Excel.
"""


@dataclass(frozen=True)
class RowData:
    """Represents a single normalized row from Excel data.
    
    This class encapsulates a single row after Excel processing:
    - Extracted from Excel starting at row 3 (1st data row after title and header)
    - Normalized values with excluded columns (sequences, FK propagation) removed
    - Optional raw values for debugging and validation purposes
    - Future extension for row-level validation support
    
    Attributes:
        row_number: Excel row number (3rd row = 1, 4th row = 2, etc.)
        values: Column name -> normalized value mapping (excluded columns removed)
        raw_values: Original values before normalization (optional, for debugging)
        invalid: Row-level validation flag (future extension, defaults to False)
    """
    row_number: int
    values: dict[str, Any]
    raw_values: dict[str, Any] | None = None
    invalid: bool = False