from __future__ import annotations
import pandas as pd
import pytest
from pathlib import Path
from src.excel.reader import read_excel_file, normalize_sheet, SheetHeaderError, MissingColumnsError


def _make_excel(tmp_path: Path, name: str, sheets: dict[str, list[list[object]]]) -> Path:
    p = tmp_path / name
    with pd.ExcelWriter(p) as writer:
        for sheet, rows in sheets.items():
            df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=sheet, header=False, index=False)
    return p


def test_read_and_normalize_success(temp_workdir: Path):
    excel = _make_excel(
        temp_workdir, "customers.xlsx",
        {
            "Customers": [
                ["Title Row", "Ignored"],
                ["id", "name"],
                [1, "Alice"],
                [2, "Bob"],
            ]
        }
    )
    dfs = read_excel_file(excel)
    assert "Customers" in dfs
    sheet = normalize_sheet(dfs["Customers"], "Customers", expected_columns={"id", "name"})
    assert sheet.columns == ["id", "name"]
    assert len(sheet.rows) == 2
    assert sheet.rows[0]["id"] == 1


def test_normalize_missing_header_row(temp_workdir: Path):
    excel = _make_excel(
        temp_workdir, "bad.xlsx",
        {
            "Sheet1": [
                ["Only title"],  # 1 row only
            ]
        }
    )
    dfs = read_excel_file(excel)
    with pytest.raises(SheetHeaderError):
        normalize_sheet(dfs["Sheet1"], "Sheet1")


def test_normalize_missing_expected_column(temp_workdir: Path):
    excel = _make_excel(
        temp_workdir, "missing_col.xlsx",
        {
            "Sheet1": [
                ["Title"],
                ["id", "name"],
                [1, "Alice"],
            ]
        }
    )
    dfs = read_excel_file(excel)
    with pytest.raises(MissingColumnsError):
        normalize_sheet(dfs["Sheet1"], "Sheet1", expected_columns={"id", "name", "email"})


def test_normalize_ignores_empty_trailing_rows(temp_workdir: Path):
    excel = _make_excel(
        temp_workdir, "empty_rows.xlsx",
        {
            "Sheet1": [
                ["Title"],
                ["id", "name"],
                [1, "Alice"],
                [None, None],  # should be skipped
                [2, "Bob"],
            ]
        }
    )
    dfs = read_excel_file(excel)
    sheet = normalize_sheet(dfs["Sheet1"], "Sheet1")
    # 空行 (全 NaN) はスキップされるのでデータ行は 2 行のみ
    assert len(sheet.rows) == 2
    assert sheet.rows[0]["id"] == 1
    assert sheet.rows[1]["id"] == 2


def test_read_excel_file_target_sheets_filter(temp_workdir: Path):
    excel = _make_excel(
        temp_workdir, "multi.xlsx",
        {
            "A": [["T"],["c1"],[1]],
            "B": [["T"],["c1"],[2]],
        }
    )
    dfs_all = read_excel_file(excel)
    assert set(dfs_all.keys()) == {"A", "B"}
    dfs_filtered = read_excel_file(excel, target_sheets=["B"])
    assert set(dfs_filtered.keys()) == {"B"}
