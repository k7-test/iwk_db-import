from __future__ import annotations

from dataclasses import dataclass

"""Config dataclasses for Excel -> PostgreSQL import tool.

This module defines the domain models for configuration based on data-model.md specifications.
These are separate from the loader implementation in src/config/loader.py and focus on
proper typing and domain modeling.

Phase: 3.3 (Domain Models)
Task: T014 - Implement ImportConfig / SheetMappingConfig / DatabaseConfig dataclasses
"""


@dataclass(frozen=True)
class DatabaseConfig:
    """Database connection configuration (FR-027).
    
    Used as fallback when environment variables are not set.
    Environment variables take precedence over these values.
    """
    host: str | None
    port: int | None
    user: str | None
    password: str | None
    database: str | None
    dsn: str | None


@dataclass(frozen=True)
class SheetMappingConfig:
    """Configuration for mapping a single Excel sheet to a database table (FR-003).
    
    Defines how each sheet should be processed, including which columns to ignore
    for auto-generated sequences and FK propagation.
    """
    sheet_name: str  # Excel sheet name (key in sheet_mappings dict)
    table_name: str  # Target database table name
    sequence_columns: set[str]  # Columns with auto-generated values (ignore Excel values)
    fk_propagation_columns: set[str]  # Columns that get values from parent records
    default_values: dict[str, object] | None = None  # 空セル時適用デフォルト
    
    @property
    def expected_columns(self) -> set[str]:
        """Derived property: columns that must exist in Excel header (FR-016).
        
        These are all columns except those that are auto-generated or propagated.
        Used for validating that required columns are present in the Excel file.
        """
        # In the initial implementation, we don't have a full column list
        # This property will be more meaningful when we have complete table schema info
        # For now, it returns an empty set as a placeholder
        # TODO(T015): Implement expected_columns logic when table schema is available
        return set()


@dataclass(frozen=True)
class ImportConfig:
    """Root configuration object for the import process (FR-014, FR-026, FR-027).
    
    Contains all settings needed to process Excel files and import them to PostgreSQL.
    """
    source_directory: str  # Directory to scan for Excel files
    sheet_mappings: dict[str, SheetMappingConfig]  # Sheet name -> configuration mapping
    sequences: dict[str, str]  # Column name -> sequence name mapping (for reference)
    fk_propagations: dict[str, str]  # Parent column -> child column mapping
    timezone: str  # Timezone for datetime processing (default: "UTC")
    database: DatabaseConfig  # Database connection fallback configuration