from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

"""ErrorRecord model for error logging.

T018 [P] Implement ErrorRecord (row=-1 support).

This module defines the ErrorRecord dataclass used for structured error logging
in the Excel -> PostgreSQL import process. It supports row=-1 as a sentinel value
for file-level errors where the specific row cannot be determined.

The ErrorRecord adheres to the JSON schema contract defined in:
specs/001-excel-postgressql-excel/contracts/error_log_schema.json
"""

__all__ = [
    "ErrorRecord",
]


@dataclass(frozen=True)
class ErrorRecord:
    """Structured error record for JSON Lines logging.

    Attributes:
        timestamp: ISO8601 UTC timestamp with 'Z' suffix
        file: Excel filename being processed
        sheet: Sheet name within the file
        row: Row number (1-based). Use -1 for file-level errors where row is unknown
        error_type: Error classification in UPPER_SNAKE_CASE format
        db_message: Database error message or description
    """
    timestamp: str  # ISO8601 UTC
    file: str
    sheet: str
    row: int  # 行番号。不明な場合 -1 許容
    error_type: str  # UPPER_SNAKE
    db_message: str

    @staticmethod
    def create(file: str, sheet: str, row: int, error_type: str, db_message: str) -> ErrorRecord:
        """Create a new ErrorRecord with current UTC timestamp.

        Parameters:
            file: Excel filename being processed
            sheet: Sheet name within the file
            row: Row number (1-based). Use -1 for file-level errors where row is unknown
            error_type: Error classification in UPPER_SNAKE_CASE format
            db_message: Database error message or description

        Returns:
            New ErrorRecord instance with current UTC timestamp
        """
        ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return ErrorRecord(
            timestamp=ts,
            file=file,
            sheet=sheet,
            row=row,
            error_type=error_type,
            db_message=db_message,
        )

    def to_json_line(self) -> str:
        """Serialize ErrorRecord to JSON Lines format.

        Returns:
            JSON string representation without extra keys (contract enforced)
        """
        # 追加キー阻止: dataclass -> dict して json.dumps
        return json.dumps(asdict(self), ensure_ascii=False)