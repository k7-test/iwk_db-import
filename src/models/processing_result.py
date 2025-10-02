from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

"""Processing result models for Excel -> PostgreSQL import tool.

This module defines the domain models for aggregating processing results and metrics
based on data-model.md specifications.

Phase: 3.3 (Domain Models)
Task: T019 - Implement ProcessingResult, FileStat, MetricsSnapshot
"""


@dataclass(frozen=True)
class FileStat:
    """Per-file processing statistics (internal helper for ProcessingResult).
    
    Used to track detailed metrics for each individual file processed.
    """
    file_name: str  # ファイル名
    status: str  # success/failed
    inserted_rows: int  # 成功時行数
    elapsed_seconds: float  # ファイル処理時間


@dataclass(frozen=True)
class ProcessingResult:
    """Aggregated results and summary output for import processing (FR-011, FR-022, QR-007).
    
    Contains all metrics needed for the SUMMARY output line and overall processing results.
    """
    success_files: int  # 成功ファイル数 (FR-011)
    failed_files: int  # 失敗ファイル数 (FR-011) 
    total_inserted_rows: int  # 総挿入行数 (FR-011)
    skipped_sheets: int  # スキップシート合計 (FR-010, FR-011)
    start_time: datetime  # 全体開始 (QR-007)
    end_time: datetime  # 全体終了 (QR-007)
    elapsed_seconds: float  # end - start (QR-004)
    throughput_rows_per_sec: float  # total_inserted / elapsed (QR-005)
    file_stats: list[FileStat] | None = None  # ファイル詳細 (QR-007)


@dataclass(frozen=True)  
class MetricsSnapshot:
    """Real-time progress display structure (QR-007, QR-008).
    
    In-memory only structure for tracking current processing state.
    初版はオンメモリのみ。
    """
    current_file_index: int  # 現在ファイル番号
    total_files: int  # 総ファイル数
    current_sheet: str  # 現在処理シート
    processed_rows_in_file: int  # 現ファイルで処理済行数
    last_update: datetime  # 最終表示更新時刻