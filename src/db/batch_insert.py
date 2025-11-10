from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

"""DB batch insert scaffolding.

R-001 Decision: 初版は psycopg2.extras.execute_values を用いたバッチ INSERT。
FR-006/FR-007/FR-029: sequence / fk 伝播列は除外済みの前提でここには渡さない。

スコープ (未実装部分):
- 実際の DB 接続 / エラー分類
- RETURNING 条件分岐 (親PK取得) は後続 service 層で判断し本関数へ引数 bool で渡す予定

この段階ではインタフェースと失敗時例外ラップを提示し、テストはモックで呼び出し確認のみを行う。

T023 Enhancement: Added metrics callback support for batch timing instrumentation.
"""

try:  # pragma: no cover - optional until psycopg2 present at runtime
    import psycopg2
    from psycopg2.extras import execute_values
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore
    execute_values = None  # type: ignore

class BatchInsertError(Exception):
    pass


@dataclass(frozen=True)
class BatchMetrics:
    """Metrics data for a single batch insert operation (T023, T029)."""
    batch_size: int  # Number of rows in this batch
    elapsed_seconds: float  # Time spent on execute_values call
    start_time: float  # Start timestamp (time.time())
    end_time: float  # End timestamp (time.time())


@dataclass(frozen=True)
class InsertResult:
    inserted_rows: int
    returned_values: list[tuple[Any, ...]] | None = None


def batch_insert(
    cursor: Any,
    table: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
    returning: bool = False,
    page_size: int = 1000,
    metrics_callback: Callable[[BatchMetrics], None] | None = None,
    blob_columns: set[str] | None = None,
) -> InsertResult:
    """Perform batched INSERT using psycopg2.extras.execute_values.

    Parameters
    ----------
    cursor: psycopg2 cursor
    table: 対象テーブル名 (サニタイズ済み想定)
    columns: 挿入列 (sequence/fk 伝播列除外後)
    rows: 行シーケンス
    returning: True の場合 SELECT RETURNING 句付与 (PK 取得用途)
    page_size: execute_values の page_size (性能調整)
    metrics_callback: Optional callback to receive BatchMetrics for timing instrumentation 
        (T023, T029).
        Note: If `rows` is empty, this callback will not be invoked (the function returns early).
        
        Example usage for accumulating batch statistics:
            from src.models.processing_result import BatchStatsAccumulator
            
            accumulator = BatchStatsAccumulator()
            def callback(metrics):
                accumulator.add_batch_time(metrics.elapsed_seconds)
            
            batch_insert(cursor, table, columns, rows, metrics_callback=callback)
            total, avg, p95 = accumulator.get_stats()
            # Use stats in FileStat construction
    blob_columns: blob型の列名集合。これらの列はpg_read_binary_file()で読み込む
    """
    if execute_values is None:
        raise BatchInsertError("psycopg2 not available")

    rows_list = list(rows)
    if not rows_list:
        return InsertResult(inserted_rows=0, returned_values=[] if returning else None)

    cols_sql = ",".join(f'"{c}"' for c in columns)
    
    # Build VALUES template with pg_read_binary_file for blob columns
    if blob_columns:
        # Create a template with proper placeholders for blob columns
        value_placeholders = []
        for col in columns:
            if col in blob_columns:
                value_placeholders.append("pg_read_binary_file(%s)")
            else:
                value_placeholders.append("%s")
        template = f"({','.join(value_placeholders)})"
        base_sql = f"INSERT INTO {table} ({cols_sql})"
    else:
        template = None
        base_sql = f"INSERT INTO {table} ({cols_sql}) VALUES %s"
    
    if returning:
        base_sql += " RETURNING *"  # 後続で必要列限定最適化予定 (FR-029)

    # T023: Batch timing instrumentation
    start_time = time.time()
    try:
        if blob_columns:
            # Use custom template with pg_read_binary_file for blob columns
            execute_values(cursor, base_sql, rows_list, template=template, page_size=page_size)
        else:
            execute_values(cursor, base_sql, rows_list, page_size=page_size)
    except Exception as e:  # pragma: no cover - will be covered when real DB tests added
        raise BatchInsertError(str(e)) from e
    finally:
        end_time = time.time()
        # Call metrics callback if provided (T023, T029)
        if metrics_callback is not None:
            metrics = BatchMetrics(
                batch_size=len(rows_list),
                elapsed_seconds=end_time - start_time,
                start_time=start_time,
                end_time=end_time,
            )
            metrics_callback(metrics)

    returned = None
    if returning:
        try:
            returned = cursor.fetchall()
        except Exception as e:  # pragma: no cover
            raise BatchInsertError(f"failed fetching RETURNING rows: {e}") from e

    return InsertResult(inserted_rows=len(rows_list), returned_values=returned)
