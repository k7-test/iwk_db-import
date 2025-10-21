from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

"""Excel reader scaffolding (Phase 1).

FR-004: 2行目をヘッダ行として扱い、3行目以降をデータ行。
FR-016: 設定で期待される列が欠落した場合はファイルエラー (ここでは例外を投げる方向性)。

現段階では pandas を利用し、後続でメモリ最適化/downcast 等を実装予定。
"""


class SheetHeaderError(Exception):
    """Raised when header row (2nd line) is missing or invalid."""

class MissingColumnsError(Exception):
    """Raised when expected columns are missing in sheet header."""

@dataclass
class SheetData:
    sheet_name: str
    columns: list[str]
    rows: list[dict[str, Any]]  # 正規化済 (列名→値)


def read_excel_file(
    path: Path, target_sheets: Iterable[str] | None = None, keep_na_strings: list[str] | None = None
) -> dict[str, pd.DataFrame]:
    """Read an Excel file returning raw DataFrames keyed by sheet name.

    Parameters
    ----------
    path: Excel ファイルパス
    target_sheets: 対象シート制限 (None なら全シート)
    keep_na_strings: Pandasの既定NaN変換から除外する文字列リスト (例: ['NA'])
    """
    # Pandas default NA values を取得し、keep_na_strings を除外
    # pandas._libs.parsers.STR_NA_VALUES には既定のNA文字列集合が格納されている
    import pandas._libs.parsers as parsers
    
    if keep_na_strings:
        # 既定のNA値から keep_na_strings を除外
        default_na = parsers.STR_NA_VALUES.copy()
        custom_na = default_na - set(keep_na_strings)
        na_values = list(custom_na)
        keep_default_na = False
    else:
        # keep_na_strings が指定されていない場合は既定の動作
        na_values = None
        keep_default_na = True
    
    dfs: dict[str, pd.DataFrame] = {}
    xls = pd.ExcelFile(path)
    for name in xls.sheet_names:
        if target_sheets is not None and str(name) not in target_sheets:
            continue
        # ヘッダなしで生読み (後で2行目をヘッダとして適用)
        # keep_default_na と na_values を指定して NA 変換を制御
        df = xls.parse(name, header=None, keep_default_na=keep_default_na, na_values=na_values)
        dfs[str(name)] = df
    return dfs


def normalize_sheet(
    df: pd.DataFrame,
    sheet_name: str,
    expected_columns: set[str] | None = None,
    default_values: dict[str, Any] | None = None,
    null_sentinels: set[str] | None = None,
) -> SheetData:
    """Normalize a raw DataFrame using second row as header.

    Steps:
    1. Validate at least 2 rows exist (1: title, 2: header)
    2. Extract header from second row (index=1)
    3. Remaining rows (index>=2) become data rows (index offset not stored here)
    4. Validate expected columns subset
    """
    if df.shape[0] < 2:
        raise SheetHeaderError(f"sheet '{sheet_name}' lacks second row header")
    header_series = df.iloc[1]
    columns = [str(c).strip() for c in header_series.tolist()]
    # Data rows start from index 2
    data_part = df.iloc[2:]
    rows: list[dict[str, Any]] = []
    for _, raw in data_part.iterrows():
        # Build row dict skipping trailing NaNs only if entire row is NaN
        if raw.isna().all():
            continue
        row_dict: dict[str, Any] = {}
        for col, val in zip(columns, raw.tolist(), strict=False):
            if pd.isna(val):
                if default_values and col in default_values:
                    row_dict[col] = default_values[col]
                else:
                    row_dict[col] = None
            else:
                if isinstance(val, str):
                    stripped = val.strip()
                    upper = stripped.upper()
                    # NULL サニタイズ
                    if null_sentinels and upper in null_sentinels:
                        row_dict[col] = None
                        continue
                    # 空文字 / ホワイトスペースのみ -> default
                    if stripped == "" and default_values and col in default_values:
                        row_dict[col] = default_values[col]
                        continue
                row_dict[col] = val
        rows.append(row_dict)

    if expected_columns is not None:
        missing = expected_columns - set(columns)
        if missing:
            raise MissingColumnsError(f"sheet '{sheet_name}' missing columns: {sorted(missing)}")

    return SheetData(sheet_name=sheet_name, columns=columns, rows=rows)
