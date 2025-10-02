from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

"""ExcelFile domain model and FileStatus enum for Excel -> PostgreSQL import tool.

This module defines the core domain models for representing Excel files during processing,
based on the data-model.md specifications.

Phase: 3.3 (Domain Models)
Task: T015 - Implement ExcelFile & FileStatus enum

The ExcelFile represents the processing context for a single Excel file,
tracking its status through the import lifecycle from pending to success/failed.
"""


class FileStatus(Enum):
    """Status enum for ExcelFile processing lifecycle (FR-002, FR-009).
    
    State transitions: pending → processing → (success | failed)
    
    - PENDING: File discovered but not yet processed
    - PROCESSING: File is currently being processed
    - SUCCESS: File processed successfully, all sheets imported
    - FAILED: File processing failed due to errors
    """
    PENDING = "pending"
    PROCESSING = "processing" 
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class ExcelFile:
    """Processing context for a single Excel file (FR-001, FR-002, FR-009).
    
    This represents the state and metadata for an Excel file throughout
    the import process, from discovery through completion.
    
    Fields align with data-model.md specification and support performance
    tracking (QR-007) and error reporting (FR-008).
    """
    path: Path                           # Full path to Excel file (FR-001)
    name: str                           # File name (FR-001)
    sheets: list[Any]                   # Sheet processing units (FR-003) - SheetProcess from T016
    start_time: datetime | None = None  # Processing start (UTC) (QR-007)
    end_time: datetime | None = None    # Processing end (UTC) (QR-007)
    status: FileStatus = FileStatus.PENDING  # Processing status (FR-002, FR-009)
    total_rows: int = 0                 # Total inserted rows, excluding parent seq columns (FR-011)
    skipped_sheets: int = 0             # Count of sheets without mapping (FR-010)
    error: str | None = None            # Failure reason summary (FR-008)