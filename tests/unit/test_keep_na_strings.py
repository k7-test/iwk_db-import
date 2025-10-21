"""Tests for keep_na_strings configuration to preserve specific strings from NaN conversion."""
from pathlib import Path

import pandas as pd

from src.excel.reader import normalize_sheet, read_excel_file


def _make_excel(tmp_path: Path, name: str, sheets: dict[str, list[list[object]]]) -> Path:
    """Helper to create Excel files for testing."""
    p = tmp_path / name
    with pd.ExcelWriter(p) as writer:
        for sheet, rows in sheets.items():
            df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=sheet, header=False, index=False)
    return p


def test_read_excel_default_treats_na_as_nan(temp_workdir: Path):
    """Verify that by default 'NA' strings are treated as NaN by pandas."""
    excel = _make_excel(
        temp_workdir,
        "na_test.xlsx",
        {
            "Sheet1": [
                ["Title", "Title2"],
                ["col_a", "col_b"],
                ["NA", "value"],
                ["test", "NA"],
            ]
        },
    )
    # Default behavior: NA should be converted to NaN
    dfs = read_excel_file(excel)
    df = dfs["Sheet1"]
    assert pd.isna(df.iloc[2, 0])  # "NA" in row 3, col 1
    assert pd.isna(df.iloc[3, 1])  # "NA" in row 4, col 2


def test_read_excel_keep_na_strings_preserves_na(temp_workdir: Path):
    """Verify that keep_na_strings=['NA'] prevents 'NA' from being treated as NaN."""
    excel = _make_excel(
        temp_workdir,
        "na_test.xlsx",
        {
            "Sheet1": [
                ["Title", "Title2"],
                ["col_a", "col_b"],
                ["NA", "value"],
                ["test", "NA"],
            ]
        },
    )
    # With keep_na_strings=['NA'], NA should be preserved as string
    dfs = read_excel_file(excel, keep_na_strings=["NA"])
    df = dfs["Sheet1"]
    assert df.iloc[2, 0] == "NA"  # "NA" preserved as string
    assert df.iloc[3, 1] == "NA"  # "NA" preserved as string


def test_read_excel_keep_na_strings_still_converts_other_na_values(temp_workdir: Path):
    """Verify that keep_na_strings=['NA'] still converts other NA values like 'N/A', '#N/A'."""
    excel = _make_excel(
        temp_workdir,
        "na_variants.xlsx",
        {
            "Sheet1": [
                ["Title", "T2", "T3", "T4"],
                ["col_a", "col_b", "col_c", "col_d"],
                ["NA", "N/A", "#N/A", "value"],
                ["test", "NA", "null", "NULL"],
            ]
        },
    )
    # With keep_na_strings=['NA'], only 'NA' is preserved, others are still NaN
    dfs = read_excel_file(excel, keep_na_strings=["NA"])
    df = dfs["Sheet1"]
    # Row 3 (index 2)
    assert df.iloc[2, 0] == "NA"  # "NA" preserved
    assert pd.isna(df.iloc[2, 1])  # "N/A" -> NaN
    assert pd.isna(df.iloc[2, 2])  # "#N/A" -> NaN
    assert df.iloc[2, 3] == "value"  # "value" preserved
    # Row 4 (index 3)
    assert df.iloc[3, 0] == "test"  # "test" preserved
    assert df.iloc[3, 1] == "NA"  # "NA" preserved
    assert pd.isna(df.iloc[3, 2])  # "null" -> NaN
    assert pd.isna(df.iloc[3, 3])  # "NULL" -> NaN


def test_normalize_sheet_with_preserved_na_strings(temp_workdir: Path):
    """Verify that preserved NA strings work correctly through normalize_sheet."""
    excel = _make_excel(
        temp_workdir,
        "na_normalize.xlsx",
        {
            "Sheet1": [
                ["Title", "Title2"],
                ["col_a", "col_b"],
                ["NA", "value"],
                ["test", "NA"],
            ]
        },
    )
    # Read with NA preserved
    dfs = read_excel_file(excel, keep_na_strings=["NA"])
    sheet = normalize_sheet(dfs["Sheet1"], "Sheet1")
    
    # Verify normalized data has "NA" as strings, not None
    assert len(sheet.rows) == 2
    assert sheet.rows[0]["col_a"] == "NA"
    assert sheet.rows[0]["col_b"] == "value"
    assert sheet.rows[1]["col_a"] == "test"
    assert sheet.rows[1]["col_b"] == "NA"


def test_keep_na_strings_multiple_values(temp_workdir: Path):
    """Verify that multiple strings can be preserved from NaN conversion."""
    excel = _make_excel(
        temp_workdir,
        "multi_keep.xlsx",
        {
            "Sheet1": [
                ["Title", "T2", "T3"],
                ["col_a", "col_b", "col_c"],
                ["NA", "N/A", "#N/A"],
                ["test", "NA", "null"],
            ]
        },
    )
    # Keep both 'NA' and 'N/A' as strings
    dfs = read_excel_file(excel, keep_na_strings=["NA", "N/A"])
    df = dfs["Sheet1"]
    
    assert df.iloc[2, 0] == "NA"  # "NA" preserved
    assert df.iloc[2, 1] == "N/A"  # "N/A" preserved
    assert pd.isna(df.iloc[2, 2])  # "#N/A" -> NaN (not in keep list)
    assert df.iloc[3, 1] == "NA"  # "NA" preserved
    assert pd.isna(df.iloc[3, 2])  # "null" -> NaN
