from __future__ import annotations
"""DB batch insert scaffolding.

R-001 Decision: 初版は psycopg2.extras.execute_values を用いたバッチ INSERT。
FR-006/FR-007/FR-029: sequence / fk 伝播列は除外済みの前提でここには渡さない。

スコープ (未実装部分):
- 実際の DB 接続 / エラー分類
- RETURNING 条件分岐 (親PK取得) は後続 service 層で判断し本関数へ引数 bool で渡す予定

この段階ではインタフェースと失敗時例外ラップを提示し、テストはモックで呼び出し確認のみを行う。
"""
from dataclasses import dataclass
from typing import Iterable, Sequence, Any

try:  # pragma: no cover - optional until psycopg2 present at runtime
    import psycopg2  # type: ignore
    from psycopg2.extras import execute_values  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore
    execute_values = None  # type: ignore

class BatchInsertError(Exception):
    pass

@dataclass(frozen=True)
class InsertResult:
    inserted_rows: int
    returned_values: list[tuple] | None = None


def batch_insert(
    cursor: Any,
    table: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
    returning: bool = False,
    page_size: int = 1000,
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
    """
    if execute_values is None:
        raise BatchInsertError("psycopg2 not available")

    rows_list = list(rows)
    if not rows_list:
        return InsertResult(inserted_rows=0, returned_values=[] if returning else None)

    cols_sql = ",".join(f'"{c}"' for c in columns)
    base_sql = f"INSERT INTO {table} ({cols_sql}) VALUES %s"
    if returning:
        base_sql += " RETURNING *"  # 後続で必要列限定最適化予定 (FR-029)

    try:
        execute_values(cursor, base_sql, rows_list, page_size=page_size)
    except Exception as e:  # pragma: no cover - will be covered when real DB tests added
        raise BatchInsertError(str(e)) from e

    returned = None
    if returning:
        try:
            returned = cursor.fetchall()  # type: ignore[attr-defined]
        except Exception as e:  # pragma: no cover
            raise BatchInsertError(f"failed fetching RETURNING rows: {e}") from e

    return InsertResult(inserted_rows=len(rows_list), returned_values=returned)
