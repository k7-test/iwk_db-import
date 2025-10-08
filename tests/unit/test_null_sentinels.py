from pathlib import Path
import pandas as pd
from src.excel.reader import normalize_sheet, SheetData
from src.models.config_models import SheetMappingConfig
from src.services.orchestrator import _convert_config_to_domain_mappings
from src.config.loader import ImportConfig, DatabaseConfig


def test_normalize_sheet_null_sentinels_basic():
    # DataFrame with title row, header row, then data
    df = pd.DataFrame([
        ["タイトル", "タイトル2"],
        ["col_a", "col_b"],
        ["« NULL »", "NULL"],
        ["(NULL)", "value"],
        [" keep ", "(null)"],  # lower-case variant
    ])
    sheet = normalize_sheet(
        df,
        sheet_name="S",
        expected_columns=None,
        default_values=None,
        null_sentinels={"« NULL »".upper(), "NULL", "(NULL)"}
    )
    # Rows should have None substitutions
    assert sheet.rows[0]["col_a"] is None
    assert sheet.rows[0]["col_b"] is None
    assert sheet.rows[1]["col_a"] is None
    assert sheet.rows[1]["col_b"] == "value"
    # lower-case (null) also sanitized due to upper comparison
    assert sheet.rows[2]["col_b"] is None
    # value with spaces ' keep ' should remain trimmed? we don't trim non-null sentinel
    assert sheet.rows[2]["col_a"] == " keep "


def test_convert_config_to_domain_mappings_propagates_null_sentinels():
    raw = ImportConfig(
        source_directory="./data",
        sheet_mappings={
            "SHEET1": {"table": "t_sheet1"}
        },
        sequences={},
        fk_propagations={},
        timezone="UTC",
        database=DatabaseConfig(host=None, port=None, user=None, password=None, database=None, dsn=None),
        null_sentinels=["NULL", "« NULL »"],
    )
    mappings = _convert_config_to_domain_mappings(raw)
    m = mappings["SHEET1"]
    assert m.null_sentinels == {"NULL", "« NULL »"}
