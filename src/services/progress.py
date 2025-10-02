from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from tqdm import tqdm
from tqdm.std import tqdm as TqdmType

"""Progress display service with tqdm (TTY only).

T030 Implement progress display with tqdm (TTY only) and integrate into orchestrator.

This module provides progress tracking according to:
- R-003: Single tqdm instance (disable in non-TTY) + manual log integration
- QR-008: 1秒以内更新 / スパム抑止
- TTY detection using sys.stdout.isatty()

The progress display shows:
- File progress: current / total files processed
- Sheet-level indicators when processing sheets within files
"""

__all__ = [
    "ProgressTracker",
    "is_tty_enabled",
    "SheetProgressIndicator",
]


def is_tty_enabled() -> bool:
    """Check if TTY output is enabled.
    
    Returns:
        True if stdout is a TTY and progress should be displayed, False otherwise
    """
    return sys.stdout.isatty()


class ProgressTracker:
    """Progress tracker using tqdm for file processing.
    
    Provides progress display for file processing with TTY detection.
    In non-TTY environments (CI), progress bars are disabled to avoid
    ANSI control sequence spam.
    """
    
    def __init__(self, total_files: int, *, description: str = "Processing files") -> None:
        """Initialize progress tracker.
        
        Args:
            total_files: Total number of files to process
            description: Description for the progress bar
        """
        self.total_files = total_files
        self.description = description
        self.current_file = 0
        
        # Create tqdm instance only if TTY is enabled
        self.enabled = is_tty_enabled()
        self.pbar: TqdmType[Any] | None
        if self.enabled:
            self.pbar = tqdm(
                total=total_files,
                desc=description,
                unit="file",
                disable=False,
                leave=True,
                position=0,
                ncols=80,  # Standard width for consistency
                ascii=True,  # ASCII chars for better compatibility
            )
        else:
            self.pbar = None
    
    def start_file(self, file_path: Path) -> None:
        """Start processing a file.
        
        Args:
            file_path: Path to the file being processed
        """
        self.current_file += 1
        
        if self.enabled and self.pbar is not None:
            # Update description to show current file
            file_desc = f"{self.description} ({file_path.name})"
            self.pbar.set_description(file_desc)
    
    def finish_file(self, success: bool = True) -> None:
        """Finish processing a file.
        
        Args:
            success: Whether the file was processed successfully
        """
        if self.enabled and self.pbar is not None:
            self.pbar.update(1)
            
            # Reset description to base description
            self.pbar.set_description(self.description)
    
    def set_postfix(self, **kwargs: Any) -> None:
        """Set postfix information (stats) on the progress bar.
        
        Args:
            **kwargs: Key-value pairs to show as postfix
        """
        if self.enabled and self.pbar is not None:
            self.pbar.set_postfix(**kwargs)
    
    def close(self) -> None:
        """Close the progress bar."""
        if self.enabled and self.pbar is not None:
            self.pbar.close()
            self.pbar = None
    
    def __enter__(self) -> ProgressTracker:
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


class SheetProgressIndicator:
    """Simple sheet progress indicator for within-file processing.
    
    Shows sheet processing status without a full progress bar,
    since sheet processing is typically fast and doesn't need
    detailed progress tracking.
    """
    
    def __init__(self, file_name: str, total_sheets: int) -> None:
        """Initialize sheet progress indicator.
        
        Args:
            file_name: Name of the file being processed
            total_sheets: Total number of sheets in the file
        """
        self.file_name = file_name
        self.total_sheets = total_sheets
        self.current_sheet = 0
        self.enabled = is_tty_enabled()
    
    def start_sheet(self, sheet_name: str) -> None:
        """Start processing a sheet.
        
        Args:
            sheet_name: Name of the sheet being processed
        """
        self.current_sheet += 1
        
        if self.enabled:
            # Simple print for sheet progress (not persistent like tqdm)
            progress_str = f"  Sheet {self.current_sheet}/{self.total_sheets}: {sheet_name}"
            print(progress_str, end="", flush=True)
    
    def finish_sheet(self, success: bool = True, rows_processed: int = 0) -> None:
        """Finish processing a sheet.
        
        Args:
            success: Whether the sheet was processed successfully
            rows_processed: Number of rows processed
        """
        if self.enabled:
            status = "✓" if success else "✗"
            if rows_processed > 0:
                print(f" - {rows_processed} rows {status}")
            else:
                print(f" {status}")