"""Integration test for keep_na_strings feature."""
from pathlib import Path

import pandas as pd

from src.config.loader import load_config
from src.services.orchestrator import process_all


def test_keep_na_strings_integration(temp_workdir: Path) -> None:
    """Test that keep_na_strings configuration preserves NA strings in Excel data."""
    # Directory structure already created by temp_workdir fixture
    config_dir = temp_workdir / "config"
    data_dir = temp_workdir / "data"
    
    # Create config with keep_na_strings
    config_file = config_dir / "import.yml"
    config_file.write_text("""
source_directory: data
keep_na_strings:
  - "NA"
sheet_mappings:
  TestSheet:
    table: test_table
sequences: {}
fk_propagations: []
database:
  host: localhost
  port: 5432
  user: test
  password: ""
  database: test
""")
    
    # Create Excel file with "NA" values
    excel_path = data_dir / "test.xlsx"
    with pd.ExcelWriter(excel_path) as writer:
        df = pd.DataFrame([
            ["Title", "Title2", "Title3"],
            ["col_a", "col_b", "col_c"],
            ["NA", "value1", "test"],
            ["value2", "NA", "N/A"],
            ["test", "test", "NA"],
        ])
        df.to_excel(writer, sheet_name="TestSheet", header=False, index=False)
    
    # Load config and process
    config = load_config(config_file)
    assert config.keep_na_strings == ["NA"]
    
    # Process in mock mode (no DB cursor)
    result = process_all(config, cursor=None)
    
    # Verify processing succeeded
    assert result.success_files == 1
    assert result.failed_files == 0
    assert result.total_inserted_rows == 3  # 3 data rows
    
    # Verify the file was processed
    assert len(result.file_stats) == 1
    file_stat = result.file_stats[0]
    assert file_stat.status == "success"
    assert file_stat.inserted_rows == 3


def test_no_keep_na_strings_default_behavior(temp_workdir: Path) -> None:
    """Test that without keep_na_strings, default pandas behavior applies."""
    # Directory structure already created by temp_workdir fixture
    config_dir = temp_workdir / "config"
    data_dir = temp_workdir / "data"
    
    # Create config WITHOUT keep_na_strings
    config_file = config_dir / "import.yml"
    config_file.write_text("""
source_directory: data
sheet_mappings:
  TestSheet:
    table: test_table
sequences: {}
fk_propagations: []
database:
  host: localhost
  port: 5432
  user: test
  password: ""
  database: test
""")
    
    # Create Excel file with "NA" values
    excel_path = data_dir / "test.xlsx"
    with pd.ExcelWriter(excel_path) as writer:
        df = pd.DataFrame([
            ["Title", "Title2"],
            ["col_a", "col_b"],
            ["NA", "value1"],
            ["value2", "NA"],
        ])
        df.to_excel(writer, sheet_name="TestSheet", header=False, index=False)
    
    # Load config and process
    config = load_config(config_file)
    assert config.keep_na_strings is None
    
    # Process in mock mode (no DB cursor)
    result = process_all(config, cursor=None)
    
    # Verify processing succeeded (NA values become None in data)
    assert result.success_files == 1
    assert result.failed_files == 0
    # Both rows should be processed, even with NA/None values
    assert result.total_inserted_rows == 2
