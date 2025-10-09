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
from .progress import ProgressTracker, SheetProgressIndicator

# FK 伝播サービス (T023 統合)
from .fk_propagation import (
    needs_returning,
    build_fk_propagation_maps,
    build_parent_pk_map,
    get_column_index,
    FKPropagationError,
    FKPropagationMap,
)
from ..config.loader import ImportConfig as LoaderImportConfig  # type: ignore
from ..models.config_models import ImportConfig as DomainImportConfig  # for type clarity
import logging

logger = logging.getLogger(__name__)


def _diagnose_table_columns(cursor: Any, table: str, insert_columns: list[str]) -> None:
    """Print diagnostic info about table column presence vs insert columns.

    This is a temporary diagnostic helper; it prints to stdout so that even when
    logging output is suppressed by progress bars we still see the result.
    """
    try:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
            (table,),
        )
        existing = {r[0] for r in cursor.fetchall()}
        missing = [c for c in insert_columns if c not in existing]
        extra = [c for c in existing if c not in insert_columns]
        print(
            f"[DIAG] table={table} existing_cols={len(existing)} missing={missing if missing else '[]'} extra_not_used={extra[:10]}"
        )
    except Exception as e:  # pragma: no cover
        print(f"[DIAG] failed to inspect table columns table={table} err={e}")

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
    
    global_nulls = set()
    # loader.ImportConfig may have list[str] or None
    try:
        if getattr(config, 'null_sentinels', None):
            global_nulls = {s.strip().upper() for s in config.null_sentinels if isinstance(s, str)}  # type: ignore[attr-defined]
    except Exception:
        global_nulls = set()

    for sheet_name, mapping_data in config.sheet_mappings.items():
        if not isinstance(mapping_data, dict):
            raise ProcessingError(
                f"Invalid mapping data for sheet '{sheet_name}': expected a dict, "
                f"got {type(mapping_data).__name__}"
            )
        # Extract table name from mapping data
        table_name = mapping_data.get("table", sheet_name.lower())
        
        # Get sequence columns for this sheet from the mapping data
        sequence_cols = set(mapping_data.get("sequence_columns", []))
        
        # Get FK propagation columns for this sheet from the mapping data
        fk_cols = set(mapping_data.get("fk_propagation_columns", []))
        default_vals = mapping_data.get("default_values") if isinstance(mapping_data, dict) else None
        
        domain_mappings[sheet_name] = DomainSheetMappingConfig(
            sheet_name=sheet_name,
            table_name=table_name,
            sequence_columns=sequence_cols,
            fk_propagation_columns=fk_cols,
            default_values=default_vals,
            null_sentinels=global_nulls if global_nulls else None,
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
    
    # FK 伝播関連マップ (親テーブル → 親 RETURNING 結果 PK マップ)
    fk_maps: list[FKPropagationMap] = build_fk_propagation_maps(config)
    parent_pk_lookup: dict[str, dict[Any, Any]] = {}

    # 既に RETURNING 済テーブルセット (needs_returning 判定用)
    processed_tables: set[str] = set()

    # Process each file with progress tracking
    file_stats: list[FileStat] = []
    success_count = 0
    failed_count = 0
    total_rows = 0
    total_skipped_sheets = 0
    
    # Initialize progress tracker for files (T030)
    with ProgressTracker(len(file_paths), description="Processing files") as progress:
        for file_path in file_paths:
            # Start file processing
            progress.start_file(file_path)
            
            file_start = datetime.now(UTC)
            file_result = _process_single_file(
                file_path,
                domain_mappings,
                cursor,
                error_log,
                fk_maps,
                parent_pk_lookup,
                processed_tables,
                config,
            )
            file_end = datetime.now(UTC)
            file_elapsed = (file_end - file_start).total_seconds()
            
            # Update counters
            if file_result.status == FileStatus.SUCCESS:
                success_count += 1
                total_rows += file_result.total_rows
            else:
                failed_count += 1
            
            total_skipped_sheets += file_result.skipped_sheets
            
            # Update progress postfix with current stats
            progress.set_postfix(
                success=success_count,
                failed=failed_count,
                rows=total_rows
            )
            
            # Finish file processing
            progress.finish_file(success=(file_result.status == FileStatus.SUCCESS))
            
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
    error_log: ErrorLogBuffer,
    fk_maps: list[FKPropagationMap],
    parent_pk_lookup: dict[str, dict[Any, Any]],
    processed_tables: set[str],
    raw_config: ImportConfig,
) -> ExcelFile:
    """Process a single Excel file with transaction boundary.
    
    T021: Implements per-file transaction with rollback on failure.
    Each file is processed in its own transaction - on success, changes
    are committed; on failure, changes are rolled back and processing
    continues with the next file.
    
    Args:
        file_path: Path to Excel file to process
        sheet_mappings: Sheet mapping configurations
        cursor: Database cursor (None = mock mode)  
        error_log: Error log buffer for recording errors
        
    Returns:
        ExcelFile with processing results and status
    """
    start_time = datetime.now(UTC)
    
    # Begin transaction for this file (if real DB connection)
    if cursor is not None:
        try:
            cursor.execute("BEGIN")
        except Exception as e:
            # If we can't even begin a transaction, record error and fail
            error_record = ErrorRecord.create(
                file=file_path.name,
                sheet="<FILE_LEVEL>",
                row=-1,
                error_type="TRANSACTION_BEGIN_ERROR",
                db_message=str(e)
            )
            error_log.append(error_record)
            
            end_time = datetime.now(UTC)
            return ExcelFile(
                path=file_path,
                name=file_path.name,
                sheets=[],
                start_time=start_time,
                end_time=end_time,
                status=FileStatus.FAILED,
                total_rows=0,
                skipped_sheets=0,
                error=f"Failed to begin transaction: {e}"
            )
    
    try:
        # Read Excel file
        raw_sheets = read_excel_file(file_path, target_sheets=set(sheet_mappings.keys()))

        total_inserted_rows = 0
        skipped_sheets = 0
        sheet_processes: list[SheetProcess] = []
        file_failed = False

        # Count sheets (config順) that both have a mapping and exist in workbook
        mapped_sheets = [name for name in sheet_mappings.keys() if name in raw_sheets]

        # Initialize sheet progress indicator (T030)
        sheet_progress = SheetProgressIndicator(
            file_name=file_path.name,
            total_sheets=len(mapped_sheets)
        )
        
        # Process in config (dict insertion) order
        for sheet_name, sheet_mapping in sheet_mappings.items():
            # 物理シートに存在しない場合はスキップ (mapped_sheets 集計対象外なので skipped_sheets++)
            if sheet_name not in raw_sheets:
                skipped_sheets += 1
                continue
            df = raw_sheets[sheet_name]
            # Start sheet processing (progress uses only existing mapped sheets count)
            sheet_progress.start_sheet(sheet_name)
            sheet_result = _process_single_sheet(
                sheet_name,
                df,
                sheet_mapping,
                cursor,
                error_log,
                file_path.name,
                fk_maps,
                parent_pk_lookup,
                processed_tables,
                raw_config,
            )
            sheet_processes.append(sheet_result)
            total_inserted_rows += sheet_result.inserted_rows

            # If this sheet failed, mark and break (Patch2/3)
            if sheet_result.error is not None:
                file_failed = True
                # Rollback immediately for file-level atomicity
                if cursor is not None:
                    try:
                        cursor.execute("ROLLBACK")
                    except Exception:
                        pass
                # Finish sheet (failed) and break out
                sheet_progress.finish_sheet(success=False, rows_processed=sheet_result.inserted_rows)
                # Skip remaining mapped sheets
                break
            
            # Finish sheet processing
            sheet_progress.finish_sheet(
                success=(sheet_result.error is None),
                rows_processed=sheet_result.inserted_rows
            )
        
        # If file failed but we didn't rollback earlier (e.g., no DB cursor), mark status
        if file_failed:
            end_time = datetime.now(UTC)
            return ExcelFile(
                path=file_path,
                name=file_path.name,
                sheets=sheet_processes,
                start_time=start_time,
                end_time=end_time,
                status=FileStatus.FAILED,
                total_rows=total_inserted_rows,
                skipped_sheets=skipped_sheets,
                error="sheet failure — transaction rolled back" if cursor is not None else "sheet failure"
            )

        # Commit transaction on success (if real DB connection)
        if cursor is not None:
            try:
                cursor.execute("COMMIT")
            except Exception as e:
                # Treat commit failure as file failure
                try:
                    cursor.execute("ROLLBACK")
                except Exception:
                    pass
                end_time = datetime.now(UTC)
                error_record = ErrorRecord.create(
                    file=file_path.name,
                    sheet="<FILE_LEVEL>",
                    row=-1,
                    error_type="TRANSACTION_COMMIT_ERROR",
                    db_message=str(e)
                )
                error_log.append(error_record)
                return ExcelFile(
                    path=file_path,
                    name=file_path.name,
                    sheets=sheet_processes,
                    start_time=start_time,
                    end_time=end_time,
                    status=FileStatus.FAILED,
                    total_rows=total_inserted_rows,
                    skipped_sheets=skipped_sheets,
                    error=f"commit failed: {e}"
                )
        
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
        # Rollback transaction on any failure (if real DB connection)
        if cursor is not None:
            try:
                cursor.execute("ROLLBACK")
            except Exception as rollback_e:
                # Log rollback failure but don't override original error
                rollback_error = ErrorRecord.create(
                    file=file_path.name,
                    sheet="<FILE_LEVEL>",
                    row=-1,
                    error_type="TRANSACTION_ROLLBACK_ERROR",
                    db_message=str(rollback_e)
                )
                error_log.append(rollback_error)
        
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
    file_name: str,
    fk_maps: list[FKPropagationMap],
    parent_pk_lookup: dict[str, dict[Any, Any]],
    processed_tables: set[str],
    raw_config: ImportConfig,
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
        try:
            sheet_data = normalize_sheet(
                df,
                sheet_name,
                expected_columns=sheet_mapping.expected_columns or None,
                default_values=sheet_mapping.default_values,
                null_sentinels=sheet_mapping.null_sentinels,
            )
        except TypeError:  # 後方互換: テストモックが旧シグネチャの場合
            sheet_data = normalize_sheet(
                df,
                sheet_name,
                expected_columns=sheet_mapping.expected_columns or None,
                default_values=sheet_mapping.default_values,
            )  # pragma: no cover (fallback path for legacy mocks)
        
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
        # Prepare data for batch insert: sequence列は除外、FK伝播列は含めて後で値補完
        ignored_columns = sheet_mapping.sequence_columns
        insert_columns = [col for col in sheet_data.columns if col not in ignored_columns]
        table_name = sheet_mapping.table_name

        # Warn if nothing to insert (all columns were ignored)
        if not insert_columns:
            logger.warning(
                "sheet=%s table=%s has no insertable columns (ignored=%s)",
                sheet_name,
                table_name,
                sorted(ignored_columns),
            )

        # Determine if this table is a parent requiring RETURNING
        do_returning = False
        if cursor is not None:
            try:
                do_returning = needs_returning(table_name, raw_config, processed_tables)
            except Exception:
                do_returning = False
        
        # Build raw insert rows
        insert_rows = []
        for row_dict in sheet_data.rows:
            row_values = [row_dict.get(col) for col in insert_columns]
            insert_rows.append(row_values)
        logger.debug(
            "sheet=%s table=%s insert_columns=%s row_count=%d fk_cols=%s returning_candidate=%s",
            sheet_name,
            table_name,
            insert_columns,
            len(insert_rows),
            sorted(sheet_mapping.fk_propagation_columns),
            do_returning,
        )
        # Print trace for direct visibility regardless of logger level (temporary diagnostic)
        try:
            print(
                f"[TRACE] build sheet={sheet_name} table={table_name} cols={len(insert_columns)} rows={len(insert_rows)} returning={do_returning} first_row={insert_rows[0] if insert_rows else '[]'}"
            )
        except Exception:  # pragma: no cover
            pass

        # FK 伝播適用: 親マップが存在し、当該シートに fk_propagation_columns がある場合
        if sheet_mapping.fk_propagation_columns and cursor is not None:
            # 簡易: 全ての fk_propagation_columns について parent_pk_lookup のどれか1つを利用
            # マッピング形式 parent_table.parent_identifier -> child_table.child_fk
            for fk_col in sheet_mapping.fk_propagation_columns:
                if fk_col not in insert_columns:
                    continue  # sequence によって除外されたなど
                # 探索: fk_maps から該当 child_fk_column 終端一致
                target_maps = [m for m in fk_maps if m.child_fk_column.endswith(f".{fk_col}") or m.child_fk_column == fk_col]
                if not target_maps:
                    logger.warning("FK propagation mapping not found for fk_col=%s sheet=%s", fk_col, sheet_name)
                    continue
                # 1件のみ利用 (複数は未サポート)
                m = target_maps[0]
                parent_map = parent_pk_lookup.get(m.parent_table)
                if not parent_map:
                    logger.warning("Parent PK map not ready for parent_table=%s fk_col=%s", m.parent_table, fk_col)
                    continue
                # 値置換: 現状 row_dict 内に識別子キー列が同一 fk_col 名で入っているとは限らない -> 単純に None のセル埋めのみ
                col_index = insert_columns.index(fk_col)
                for ridx, row_values in enumerate(insert_rows):
                    if row_values[col_index] is None:
                        # 適当な単一キー選択ロジック (データ行数==親件数かつ順序対応と仮定)
                        # 安全のためインデックスで対応
                        try:
                            pk_list = list(parent_map.values())
                            row_values[col_index] = pk_list[ridx % len(pk_list)] if pk_list else None
                        except Exception:  # pragma: no cover
                            pass
        
        # Perform batch insert
        if cursor is not None:
            # Real database insert
            # Pre-insert diagnostic: compare insert columns to table definition
            _diagnose_table_columns(cursor, sheet_mapping.table_name, insert_columns)
            result = batch_insert(
                cursor=cursor,
                table=sheet_mapping.table_name,
                columns=insert_columns,
                rows=insert_rows,
                returning=do_returning,
                page_size=1000   # R-006 default batch size
            )
            inserted_rows = result.inserted_rows
            logger.debug(
                "sheet=%s executed batch_insert inserted_rows=%d returning=%s returned_values_len=%s",
                sheet_name,
                inserted_rows,
                do_returning,
                (len(result.returned_values) if result.returned_values else 0),
            )
            try:
                print(
                    f"[TRACE] inserted sheet={sheet_name} inserted_rows={inserted_rows} returned={len(result.returned_values) if result.returned_values else 0}"
                )
            except Exception:  # pragma: no cover
                pass
            # Build parent PK map if needed
            if do_returning and result.returned_values:
                # 推定: sequences で親 PK 列名を推理 (列名→シーケンスの辞書なので key を列名扱い)
                # もし複数候補なら最初を使用 (複数 PK 未対応)
                candidate_pk_cols: list[str] = []
                for col in raw_config.sequences.keys():
                    # sequences の key は列名想定
                    if "." in col:
                        # 旧形式で table.col の場合、現在テーブル名に一致するものを抽出
                        t, c = col.split(".", 1)
                        if t == table_name:
                            candidate_pk_cols.append(c)
                    else:
                        candidate_pk_cols.append(col)

                pk_col_index = 0  # fallback
                detected = False
                try:
                    # psycopg2 の cursor.description から列順メタデータを取得し、候補列一致を探索
                    if cursor is not None and getattr(cursor, "description", None):  # type: ignore[truthy-bool]
                        col_names = [d[0] for d in cursor.description]  # type: ignore[index]
                        for cand in candidate_pk_cols:
                            if cand in col_names:
                                pk_col_index = col_names.index(cand)
                                detected = True
                                break
                except Exception:  # pragma: no cover
                    logger.debug("could not inspect cursor.description for pk index", exc_info=True)

                if not detected and candidate_pk_cols:
                    # 候補はあるが description 無い場合は 0 のまま (戻り値位置依存)
                    logger.debug(
                        "pk column index fallback=0 table=%s candidates=%s", table_name, candidate_pk_cols
                    )

                # PK 値抽出 (rv[pk_col_index]) をキー・値ともに利用（現行ロジック互換: values() 列挙で順序使用）
                parent_pk_lookup[table_name] = {
                    rv[pk_col_index]: rv[pk_col_index] for rv in result.returned_values if rv and len(rv) > pk_col_index
                }
                processed_tables.add(table_name)
                logger.debug(
                    "sheet=%s parent_pk_map_size=%d",
                    sheet_name,
                    len(parent_pk_lookup[table_name]),
                )
        else:
            # Mock mode - assume all rows inserted successfully
            inserted_rows = len(insert_rows)
            logger.debug(
                "sheet=%s mock mode inserted_rows=%d",
                sheet_name,
                inserted_rows,
            )
            try:
                print(f"[TRACE] mock-insert sheet={sheet_name} inserted_rows={inserted_rows}")
            except Exception:  # pragma: no cover
                pass

        # 子テーブルなら、既に親 PK マップがある場合に本来は FK 列を埋めて再挿入すべきだが
        # 現行アーキテクチャでは除外列をそもそも挿入しない形のため、将来: 挿入前に
        # fk_propagation_columns を insert_columns に含め、行値を parent_pk_lookup で置換してから実行する再設計が必要。
        # ここでは警告のみ出す。
        if sheet_mapping.fk_propagation_columns and cursor is not None and not do_returning:
            # ここまでで do_returning=False は「子側想定」。既に親 PK マップ構築済みなら補完後に挿入されている。
            # 先行ループで None 埋め補完を試行済みなのでここでは診断ログのみ残す。
            for fk_col in sheet_mapping.fk_propagation_columns:
                mapped = any(
                    m.child_fk_column.endswith(f".{fk_col}") or m.child_fk_column == fk_col for m in fk_maps
                )
                if mapped:
                    logger.debug(
                        "sheet=%s fk_col=%s fk_propagation_applied_or_no_nulls", sheet_name, fk_col
                    )
                else:
                    logger.warning(
                        "sheet=%s fk_col=%s no fk_propagation mapping (config missing?)", sheet_name, fk_col
                    )
        
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
        print(f"[TRACE] batch_insert error sheet={sheet_name} table={sheet_mapping.table_name}: {e}")
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