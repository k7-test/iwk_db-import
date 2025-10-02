from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config.loader import ImportConfig
from ..db.batch_insert import BatchInsertError, batch_insert
from ..excel.reader import MissingColumnsError, SheetHeaderError, normalize_sheet, read_excel_file
from ..logging.error_log import ErrorLogBuffer, ErrorRecord
from ..models.config_models import SheetMappingConfig as DomainSheetMappingConfig
from ..models.excel_file import ExcelFile, FileStatus
from ..models.processing_result import FileStat, ProcessingResult
from ..models.sheet_process import SheetProcess

"""Service orchestration for Excel -> PostgreSQL import tool.

This module implements the main orchestration service that coordinates the entire
import process: scanning directories, processing files with transactions, 
aggregating metrics, and returning results.

Phase: 3.4 (Core Services)
Task: T020 - Service orchestration: implement process_all()
"""


class ProcessingError(Exception):
    """Base exception for processing errors."""
    pass


def _convert_config_to_domain_mappings(config: ImportConfig) -> dict[str, DomainSheetMappingConfig]:
    """Convert basic config sheet mappings to domain model mappings.
    
    Args:
        config: Basic ImportConfig from loader
        
    Returns:
        Dictionary of sheet name to domain SheetMappingConfig
    """
    domain_mappings: dict[str, DomainSheetMappingConfig] = {}
    
    for sheet_name, mapping_data in config.sheet_mappings.items():
        if not isinstance(mapping_data, dict):
            raise ProcessingError(
                f"Invalid mapping data for sheet '{sheet_name}': expected a dict, got {type(mapping_data).__name__}"
            )
        # Extract table name from mapping data
        table_name = mapping_data.get("table", sheet_name.lower())
        
        # Get sequence columns for this sheet from the mapping data
        sequence_cols = set(mapping_data.get("sequence_columns", []))
        
        # Get FK propagation columns for this sheet from the mapping data
        fk_cols = set(mapping_data.get("fk_propagation_columns", []))
        
        domain_mappings[sheet_name] = DomainSheetMappingConfig(
            sheet_name=sheet_name,
            table_name=table_name,
            sequence_columns=sequence_cols,
            fk_propagation_columns=fk_cols
        )
    
    return domain_mappings


def scan_excel_files(directory: Path) -> list[Path]:
    """Scan directory for .xlsx files (non-recursive).
    
    Args:
        directory: Directory to scan for Excel files
        
    Returns:
        List of Excel file paths found in directory
        
    Raises:
        ProcessingError: If directory doesn't exist or can't be read
    """
    if not directory.exists():
        raise ProcessingError(f"Directory not found: {directory}")
    
    if not directory.is_dir():
        raise ProcessingError(f"Path is not a directory: {directory}")
    
    try:
        return [p for p in directory.iterdir() if p.is_file() and p.suffix == ".xlsx"]
    except OSError as e:
        raise ProcessingError(f"Error reading directory {directory}: {e}") from e


def process_all(config: ImportConfig, cursor: Any = None) -> ProcessingResult:
    """Process all Excel files in configured directory.
    
    This is the main orchestration function that:
    1. Scans the directory for .xlsx files
    2. Processes each file in its own transaction
    3. Aggregates metrics and results
    4. Returns ProcessingResult with summary data
    
    Args:
        config: Import configuration with directory and mappings
        cursor: Database cursor for transactions (None = mock mode)
        
    Returns:
        ProcessingResult with aggregated metrics and file stats
        
    Raises:
        ProcessingError: For fatal errors that prevent processing
    """
    start_time = datetime.now(UTC)
    error_log = ErrorLogBuffer()
    
    # Convert config to domain models
    try:
        domain_mappings = _convert_config_to_domain_mappings(config)
    except Exception as e:
        raise ProcessingError(f"Invalid configuration: {e}") from e
    
    # Scan directory for Excel files
    directory = Path(config.source_directory)
    try:
        file_paths = scan_excel_files(directory)
    except ProcessingError:
        # Re-raise directory scanning errors as fatal
        raise
    
    # Handle empty directory case (FR-025)
    if not file_paths:
        end_time = datetime.now(UTC)
        elapsed = (end_time - start_time).total_seconds()
        return ProcessingResult(
            success_files=0,
            failed_files=0,
            total_inserted_rows=0,
            skipped_sheets=0,
            start_time=start_time,
            end_time=end_time,
            elapsed_seconds=elapsed,
            throughput_rows_per_sec=0.0,
            file_stats=[]
        )
    
    # Process each file
    file_stats: list[FileStat] = []
    success_count = 0
    failed_count = 0
    total_rows = 0
    total_skipped_sheets = 0
    
    for file_path in file_paths:
        file_start = datetime.now(UTC)
        file_result = _process_single_file(file_path, domain_mappings, cursor, error_log)
        file_end = datetime.now(UTC)
        file_elapsed = (file_end - file_start).total_seconds()
        
        # Update counters
        if file_result.status == FileStatus.SUCCESS:
            success_count += 1
            total_rows += file_result.total_rows
        else:
            failed_count += 1
        
        total_skipped_sheets += file_result.skipped_sheets
        
        # Create file stat
        file_stat = FileStat(
            file_name=file_path.name,
            status=file_result.status.value,
            inserted_rows=file_result.total_rows,
            elapsed_seconds=file_elapsed
        )
        file_stats.append(file_stat)
    
    # Flush error log once (R-005)
    try:
        error_log.flush()
    except Exception:
        # Don't fail the entire process if error log flush fails
        pass
    
    # Calculate final metrics
    end_time = datetime.now(UTC)
    elapsed_seconds = (end_time - start_time).total_seconds()
    
    # Calculate throughput (avoid division by zero)
    if elapsed_seconds > 0:
        throughput_rps = total_rows / elapsed_seconds
    else:
        throughput_rps = 0.0
    
    return ProcessingResult(
        success_files=success_count,
        failed_files=failed_count,
        total_inserted_rows=total_rows,
        skipped_sheets=total_skipped_sheets,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=elapsed_seconds,
        throughput_rows_per_sec=throughput_rps,
        file_stats=file_stats
    )


def _process_single_file(
    file_path: Path, 
    sheet_mappings: dict[str, DomainSheetMappingConfig], 
    cursor: Any,
    error_log: ErrorLogBuffer
) -> ExcelFile:
    """Process a single Excel file with transaction boundary.
    
    Args:
        file_path: Path to Excel file to process
        sheet_mappings: Sheet mapping configurations
        cursor: Database cursor (None = mock mode)  
        error_log: Error log buffer for recording errors
        
    Returns:
        ExcelFile with processing results and status
    """
    start_time = datetime.now(UTC)
    
    try:
        # Read Excel file
        raw_sheets = read_excel_file(file_path, target_sheets=set(sheet_mappings.keys()))
        
        total_inserted_rows = 0
        skipped_sheets = 0
        sheet_processes: list[SheetProcess] = []
        
        # Process each sheet that has a mapping
        for sheet_name, df in raw_sheets.items():
            if sheet_name not in sheet_mappings:
                skipped_sheets += 1
                continue
            
            sheet_mapping = sheet_mappings[sheet_name]
            sheet_result = _process_single_sheet(
                sheet_name, df, sheet_mapping, cursor, error_log, file_path.name
            )
            sheet_processes.append(sheet_result)
            total_inserted_rows += sheet_result.inserted_rows
        
        # Count skipped sheets (sheets in file but not in mappings)
        all_sheet_names = set(raw_sheets.keys())
        mapped_sheet_names = set(sheet_mappings.keys())
        
        end_time = datetime.now(UTC)
        
        # Return successful result
        return ExcelFile(
            path=file_path,
            name=file_path.name,
            sheets=sheet_processes,
            start_time=start_time,
            end_time=end_time,
            status=FileStatus.SUCCESS,
            total_rows=total_inserted_rows,
            skipped_sheets=skipped_sheets,
            error=None
        )
        
    except Exception as e:
        # Log file-level error
        error_record = ErrorRecord.create(
            file=file_path.name,
            sheet="<FILE_LEVEL>",
            row=-1,
            error_type="PROCESSING_ERROR",
            db_message=str(e)
        )
        error_log.append(error_record)
        
        end_time = datetime.now(UTC)
        
        # Return failed result
        return ExcelFile(
            path=file_path,
            name=file_path.name,
            sheets=[],
            start_time=start_time,
            end_time=end_time,
            status=FileStatus.FAILED,
            total_rows=0,
            skipped_sheets=0,
            error=str(e)
        )


def _process_single_sheet(
    sheet_name: str,
    df: Any,  # pandas DataFrame
    sheet_mapping: DomainSheetMappingConfig,
    cursor: Any,
    error_log: ErrorLogBuffer,
    file_name: str
) -> SheetProcess:
    """Process a single Excel sheet.
    
    Args:
        sheet_name: Name of the Excel sheet
        df: Raw pandas DataFrame from Excel
        sheet_mapping: Configuration for this sheet
        cursor: Database cursor (None = mock mode)
        error_log: Error log buffer 
        file_name: Name of source Excel file (for error logging)
        
    Returns:
        SheetProcess with processing results
    """
    try:
        # Normalize sheet data (extract header from row 2, data from row 3+)
        sheet_data = normalize_sheet(df, sheet_name, expected_columns=None)
        
        if not sheet_data.rows:
            # Empty sheet, but not an error
            return SheetProcess(
                sheet_name=sheet_name,
                table_name=sheet_mapping.table_name,
                mapping=sheet_mapping,
                rows=None,
                ignored_columns=(
                    sheet_mapping.sequence_columns | sheet_mapping.fk_propagation_columns
                ),
                inserted_rows=0,
                error=None
            )
        
        # Prepare data for batch insert (exclude sequence/FK columns)
        ignored_columns = sheet_mapping.sequence_columns | sheet_mapping.fk_propagation_columns
        insert_columns = [col for col in sheet_data.columns if col not in ignored_columns]
        
        # Prepare row data for insert
        insert_rows = []
        for row_dict in sheet_data.rows:
            row_values = [row_dict.get(col) for col in insert_columns]
            insert_rows.append(row_values)
        
        # Perform batch insert
        if cursor is not None:
            # Real database insert
            result = batch_insert(
                cursor=cursor,
                table=sheet_mapping.table_name,
                columns=insert_columns,
                rows=insert_rows,
                returning=False,  # TODO: Handle FK propagation case later (T022)
                page_size=1000   # R-006 default batch size
            )
            inserted_rows = result.inserted_rows
        else:
            # Mock mode - assume all rows inserted successfully
            inserted_rows = len(insert_rows)
        
        return SheetProcess(
            sheet_name=sheet_name,
            table_name=sheet_mapping.table_name,
            mapping=sheet_mapping,
            rows=None,  # Don't store row data in result (memory optimization)
            ignored_columns=ignored_columns,
            inserted_rows=inserted_rows,
            error=None
        )
        
    except (SheetHeaderError, MissingColumnsError) as e:
        # Sheet validation errors
        error_record = ErrorRecord.create(
            file=file_name,
            sheet=sheet_name,
            row=-1,  # Sheet-level error
            error_type="SHEET_VALIDATION_ERROR",
            db_message=str(e)
        )
        error_log.append(error_record)
        
        return SheetProcess(
            sheet_name=sheet_name,
            table_name=sheet_mapping.table_name,
            mapping=sheet_mapping,
            rows=None,
            ignored_columns=set(),
            inserted_rows=0,
            error=str(e)
        )
        
    except BatchInsertError as e:
        # Database insert errors
        error_record = ErrorRecord.create(
            file=file_name,
            sheet=sheet_name,
            row=-1,  # Batch-level error (could be refined to specific row later)
            error_type="DATABASE_INSERT_ERROR",
            db_message=str(e)
        )
        error_log.append(error_record)
        
        return SheetProcess(
            sheet_name=sheet_name,
            table_name=sheet_mapping.table_name,
            mapping=sheet_mapping,
            rows=None,
            ignored_columns=set(),
            inserted_rows=0,
            error=str(e)
        )
        
    except Exception as e:
        # Unexpected errors
        error_record = ErrorRecord.create(
            file=file_name,
            sheet=sheet_name,
            row=-1,
            error_type="UNEXPECTED_ERROR",
            db_message=str(e)
        )
        error_log.append(error_record)
        
        return SheetProcess(
            sheet_name=sheet_name,
            table_name=sheet_mapping.table_name,
            mapping=sheet_mapping,
            rows=None,
            ignored_columns=set(),
            inserted_rows=0,
            error=str(e)
        )