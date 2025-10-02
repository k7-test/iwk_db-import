from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime

"""Processing result models for Excel -> PostgreSQL import tool.

This module defines the domain models for aggregating processing results and metrics
based on data-model.md specifications.

Phase: 3.3 (Domain Models)
Task: T019 - Implement ProcessingResult, FileStat, MetricsSnapshot
Task: T029 - Add batch timing statistics accumulation
"""


@dataclass(frozen=True)
class FileStat:
    """Per-file processing statistics (internal helper for ProcessingResult).
    
    Used to track detailed metrics for each individual file processed.
    Includes batch-level timing statistics for performance analysis (T029).
    """
    file_name: str  # ファイル名
    status: str  # success/failed
    inserted_rows: int  # 成功時行数
    elapsed_seconds: float  # ファイル処理時間
    # T029: Batch timing statistics
    total_batches: int = 0  # 総バッチ数
    avg_batch_seconds: float = 0.0  # 平均バッチ時間
    p95_batch_seconds: float = 0.0  # p95 バッチ時間 (performance monitoring)


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


class BatchStatsAccumulator:
    """Helper class to accumulate batch timing statistics for FileStat (T029).
    
    Collects individual batch timing data and calculates summary statistics.
    """
    
    def __init__(self) -> None:
        self.batch_times: list[float] = []
    
    def add_batch_time(self, elapsed_seconds: float) -> None:
        """Add a batch timing measurement."""
        self.batch_times.append(elapsed_seconds)
    
    def get_stats(self) -> tuple[int, float, float]:
        """Calculate batch statistics.
        
        Returns:
            tuple: (total_batches, avg_batch_seconds, p95_batch_seconds)
        """
        if not self.batch_times:
            return (0, 0.0, 0.0)
        
        total_batches = len(self.batch_times)
        avg_batch_seconds = statistics.mean(self.batch_times)
        
        # Calculate p95 (95th percentile)
        if total_batches == 1:
            p95_batch_seconds = self.batch_times[0]
        else:
            # Use quantiles for p95 calculation
            p95_batch_seconds = statistics.quantiles(
                self.batch_times, n=20, method='inclusive'
            )[18]  # 95th percentile (19th out of 20 quantiles, 0-indexed)
        
        return (total_batches, avg_batch_seconds, p95_batch_seconds)