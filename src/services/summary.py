from __future__ import annotations

from ..models.processing_result import ProcessingResult

"""Summary line rendering service for Excel -> PostgreSQL import tool.

This module implements the summary line formatting for the SUMMARY output
based on the contract format from contracts/summary_output.md.

Phase: 3.4 (Core Services)
Task: T026 - Implement metrics accumulation & SUMMARY line rendering
"""


def render_summary_line(total_files: int, result: ProcessingResult) -> str:
    """Render a SUMMARY line from ProcessingResult according to contract format.
    
    Format (from contracts/summary_output.md):
    SUMMARY files={total}/{total} success={success} failed={failed} rows={rows} 
    skipped_sheets={skipped} elapsed_sec={elapsed} throughput_rps={throughput}
    
    Args:
        total_files: Total number of files detected/processed
        result: ProcessingResult containing aggregated metrics
        
    Returns:
        Formatted SUMMARY line string matching contract regex
        
    Examples:
        >>> from datetime import datetime, timezone
        >>> start = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc) 
        >>> end = datetime(2023, 1, 1, 10, 0, 2, tzinfo=timezone.utc)
        >>> result = ProcessingResult(
        ...     success_files=1, failed_files=0, total_inserted_rows=1000,
        ...     skipped_sheets=0, start_time=start, end_time=end,
        ...     elapsed_seconds=2.0, throughput_rows_per_sec=500.0
        ... )
        >>> render_summary_line(1, result)  # doctest: +ELLIPSIS
        'SUMMARY files=1/1 success=1 failed=0 rows=1000 skipped_sheets=0 elapsed_sec=2 ...'
    """
    # Format elapsed_sec and throughput_rps according to contract
    # Handle very small numbers and integer values appropriately
    if result.elapsed_seconds == 0:
        elapsed_str = "0"
    elif result.elapsed_seconds == int(result.elapsed_seconds):
        elapsed_str = str(int(result.elapsed_seconds))
    elif result.elapsed_seconds < 0.01:
        # Format very small numbers to avoid scientific notation
        elapsed_str = f"{result.elapsed_seconds:.6f}".rstrip('0').rstrip('.')
    else:
        elapsed_str = str(result.elapsed_seconds)
    
    if result.throughput_rows_per_sec == 0:
        throughput_str = "0"
    elif result.throughput_rows_per_sec == int(result.throughput_rows_per_sec):
        throughput_str = str(int(result.throughput_rows_per_sec))
    else:
        throughput_str = str(result.throughput_rows_per_sec)
    
    return (
        f"SUMMARY files={total_files}/{total_files} "
        f"success={result.success_files} "
        f"failed={result.failed_files} "
        f"rows={result.total_inserted_rows} "
        f"skipped_sheets={result.skipped_sheets} "
        f"elapsed_sec={elapsed_str} "
        f"throughput_rps={throughput_str}"
    )