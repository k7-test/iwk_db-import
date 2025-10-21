from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config.loader import load_config
from src.models.processing_result import ProcessingResult
from src.services.orchestrator import ProcessingError, process_all, scan_excel_files


def test_scan_excel_files_success(temp_workdir: Path) -> None:
    """Test successful Excel file scanning."""
    data_dir = temp_workdir / "data"
    
    # Create test Excel files
    (data_dir / "customers.xlsx").write_bytes(b"test")
    (data_dir / "orders.xlsx").write_bytes(b"test")
    (data_dir / "readme.txt").write_text("ignore this")
    (data_dir / "temp.xls").write_bytes(b"old format - ignore")
    
    files = scan_excel_files(data_dir)
    
    assert len(files) == 2
    file_names = {f.name for f in files}
    assert file_names == {"customers.xlsx", "orders.xlsx"}


def test_scan_excel_files_directory_not_found() -> None:
    """Test scanning non-existent directory."""
    non_existent = Path("/non/existent/path")
    
    with pytest.raises(ProcessingError, match="Directory not found"):
        scan_excel_files(non_existent)


def test_scan_excel_files_empty_directory(temp_workdir: Path) -> None:
    """Test scanning directory with no Excel files."""
    data_dir = temp_workdir / "data"
    
    # Create non-Excel files
    (data_dir / "readme.txt").write_text("no Excel files here")
    
    files = scan_excel_files(data_dir)
    assert len(files) == 0


def test_process_all_empty_directory(temp_workdir: Path, write_config: Path) -> None:
    """Test processing empty directory (FR-025)."""
    config = load_config(write_config)
    
    result = process_all(config, cursor=None)
    
    assert isinstance(result, ProcessingResult)
    assert result.success_files == 0
    assert result.failed_files == 0
    assert result.total_inserted_rows == 0
    assert result.skipped_sheets == 0
    assert result.elapsed_seconds >= 0
    assert result.throughput_rows_per_sec == 0.0
    assert result.file_stats == []


def test_process_all_mock_success(temp_workdir: Path, write_config: Path) -> None:
    """Test successful processing of Excel files in mock mode."""
    config = load_config(write_config)
    data_dir = temp_workdir / "data"
    
    # Create test Excel files
    (data_dir / "customers.xlsx").write_bytes(b"test")
    (data_dir / "orders.xlsx").write_bytes(b"test")
    
    # Mock Excel reader to return test data - different sheets per file
    def mock_read_side_effect(path, target_sheets=None, keep_na_strings=None):
        if "customers" in str(path):
            return {"Customers": MagicMock()}
        else:  # orders.xlsx
            return {"Orders": MagicMock()}
    
    mock_sheet_data = MagicMock()
    mock_sheet_data.columns = ["id", "name", "email"]
    mock_sheet_data.rows = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
    ]
    
    with patch('src.services.orchestrator.read_excel_file') as mock_read:
        with patch('src.services.orchestrator.normalize_sheet') as mock_normalize:
            mock_read.side_effect = mock_read_side_effect
            mock_normalize.return_value = mock_sheet_data
            
            result = process_all(config, cursor=None)
    
    assert result.success_files == 2
    assert result.failed_files == 0
    assert result.total_inserted_rows == 4  # 2 rows per sheet * 1 sheet per file * 2 files
    assert result.elapsed_seconds > 0
    assert result.throughput_rows_per_sec > 0
    assert len(result.file_stats) == 2
    
    # Check file stats
    for file_stat in result.file_stats:
        assert file_stat.status == "success"
        assert file_stat.inserted_rows == 2
        assert file_stat.elapsed_seconds > 0


def test_process_all_partial_failure(temp_workdir: Path, write_config: Path) -> None:
    """Test partial failure handling - one file succeeds, one fails."""
    config = load_config(write_config)
    data_dir = temp_workdir / "data"
    
    # Create test Excel files
    (data_dir / "customers.xlsx").write_bytes(b"test")
    (data_dir / "broken.xlsx").write_bytes(b"test")
    
    mock_sheet_data = MagicMock()
    mock_sheet_data.columns = ["id", "name"]
    mock_sheet_data.rows = [{"id": 1, "name": "Alice"}]
    
    def mock_read_side_effect(path, target_sheets=None, keep_na_strings=None):
        if "broken" in str(path):
            raise Exception("Corrupted Excel file")
        return {"Customers": MagicMock()}
    
    with patch('src.services.orchestrator.read_excel_file') as mock_read:
        with patch('src.services.orchestrator.normalize_sheet') as mock_normalize:
            mock_read.side_effect = mock_read_side_effect
            mock_normalize.return_value = mock_sheet_data
            
            result = process_all(config, cursor=None)
    
    assert result.success_files == 1
    assert result.failed_files == 1
    assert result.total_inserted_rows == 1  # Only from successful file
    assert len(result.file_stats) == 2
    
    # Check that one succeeded and one failed
    statuses = {stat.status for stat in result.file_stats}
    assert "success" in statuses
    assert "failed" in statuses


def test_process_all_with_database_transaction_rollback(
    temp_workdir: Path, write_config: Path
) -> None:
    """Test T021: Database transaction rollback on file-level failure."""
    config = load_config(write_config)
    data_dir = temp_workdir / "data"
    
    # Create test Excel files
    (data_dir / "success.xlsx").write_bytes(b"test")
    (data_dir / "failure.xlsx").write_bytes(b"test")
    
    # Mock database cursor
    mock_cursor = MagicMock()
    
    mock_sheet_data = MagicMock()
    mock_sheet_data.columns = ["id", "name"]
    mock_sheet_data.rows = [{"id": 1, "name": "Test"}]
    
    # Mock batch_insert to return successful results
    mock_insert_result = MagicMock()
    mock_insert_result.inserted_rows = 1
    
    def mock_read_side_effect(path, target_sheets=None, keep_na_strings=None):
        if "failure" in str(path):
            raise Exception("Simulated file processing failure")
        return {"Customers": MagicMock()}
    
    with patch('src.services.orchestrator.read_excel_file') as mock_read:
        with patch('src.services.orchestrator.normalize_sheet') as mock_normalize:
            with patch('src.services.orchestrator.batch_insert') as mock_batch_insert:
                mock_read.side_effect = mock_read_side_effect
                mock_normalize.return_value = mock_sheet_data
                mock_batch_insert.return_value = mock_insert_result
                
                result = process_all(config, cursor=mock_cursor)
    
    # Verify transaction management calls
    execute_calls = mock_cursor.execute.call_args_list
    
    # Should have: BEGIN (success file), COMMIT (success file), 
    # BEGIN (failure file), ROLLBACK (failure file)
    begin_calls = [call for call in execute_calls if call[0][0] == "BEGIN"]
    commit_calls = [call for call in execute_calls if call[0][0] == "COMMIT"]
    rollback_calls = [call for call in execute_calls if call[0][0] == "ROLLBACK"]
    
    assert len(begin_calls) == 2  # One for each file
    assert len(commit_calls) == 1  # Only for successful file
    assert len(rollback_calls) == 1  # Only for failed file
    
    # Verify processing results
    assert result.success_files == 1
    assert result.failed_files == 1
    assert result.total_inserted_rows == 1  # Only from successful file


def test_process_all_transaction_begin_failure(temp_workdir: Path, write_config: Path) -> None:
    """Test T021: Handle failure to begin transaction."""
    config = load_config(write_config)
    data_dir = temp_workdir / "data"
    
    # Create test Excel file
    (data_dir / "test.xlsx").write_bytes(b"test")
    
    # Mock database cursor that fails on BEGIN
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("Cannot begin transaction")
    
    result = process_all(config, cursor=mock_cursor)
    
    # Should fail gracefully and record error
    assert result.success_files == 0
    assert result.failed_files == 1
    assert result.total_inserted_rows == 0
    
    # Verify BEGIN was attempted
    mock_cursor.execute.assert_called_with("BEGIN")


def test_process_all_config_conversion_error(temp_workdir: Path) -> None:
    """Test error handling during config conversion."""
    from unittest.mock import Mock

    from src.models.config_models import DatabaseConfig, ImportConfig
    
    # Create a config with invalid sheet_mappings that will trigger conversion error
    mock_config = Mock(spec=ImportConfig)
    mock_config.sheet_mappings = {"Customers": "not a dict"}  # This should cause ProcessingError
    mock_config.sequences = {}
    mock_config.fk_propagations = {}
    mock_config.source_directory = "./data"
    mock_config.database = DatabaseConfig(
        host="localhost", port=5432, user="user", password="pass", database="db", dsn=None
    )
    
    with pytest.raises(ProcessingError, match="Invalid mapping data"):
        process_all(mock_config, cursor=None)


def test_process_all_directory_scanning_error(temp_workdir: Path, sample_config_yaml: str) -> None:
    """Test error handling during directory scanning."""
    # Create config with non-existent directory
    invalid_config = sample_config_yaml.replace(
        "source_directory: ./data",
        "source_directory: /non/existent/path"
    )
    
    config_path = temp_workdir / "config" / "import.yml"
    config_path.write_text(invalid_config, encoding="utf-8")
    
    from src.config.loader import load_config
    config = load_config(config_path)
    
    with pytest.raises(ProcessingError, match="Directory not found"):
        process_all(config, cursor=None)


def test_process_single_file_with_parent_returning_and_child_fk_propagation(temp_workdir: Path, write_config: Path) -> None:
    """Test parent table processed with RETURNING and child table without.

    Scenario:
      - Parent sheet requires RETURNING because child depends on its PK.
      - sequences に parent PK 情報 (table.col 形式) を与え、cursor.description を利用して PK インデックス推定を通過。
      - batch_insert は parent で returning=True, child で returning=False で呼ばれる。
    """
    from src.config.loader import load_config
    from src.models.processing_result import ProcessingResult
    from src.services.orchestrator import process_all
    from src.db.batch_insert import InsertResult
    import types
    from unittest.mock import patch, MagicMock

    # 元の config 読み込み後に FK 設定 / sequences を上書き
    config = load_config(write_config)
    # 既存シートマッピングに Parent / Child を追加 (簡易)
    # loader が返す形に合わせ dict で追加 (SheetMappingConfig ではなく)
    config.sheet_mappings['Parents'] = {
        'table': 'parents',
        'sequence_columns': ['id'],
        'fk_propagation_columns': [],
        'default_values': None,
    }
    config.sheet_mappings['Children'] = {
        'table': 'children',
        'sequence_columns': ['id'],
        'fk_propagation_columns': ['parent_id'],
        'default_values': None,
    }
    # sequences: 親 PK を table.col 形式で登録
    config.sequences['parents.id'] = 'parents_id_seq'
    # FK 伝播設定: parents.name -> children.parent_id (identifier name, fk 列 parent_id)
    config.fk_propagations['parents.name'] = 'children.parent_id'

    data_dir = temp_workdir / 'data'
    (data_dir / 'parents.xlsx').write_bytes(b"test")
    (data_dir / 'children.xlsx').write_bytes(b"test")

    # モック DataFrame 正規化後オブジェクト (normalize_sheet 戻り値互換)
    parent_sheet = MagicMock()
    parent_sheet.columns = ['id', 'name']
    parent_sheet.rows = [
        {'id': None, 'name': 'Alice'},
        {'id': None, 'name': 'Bob'},
    ]
    child_sheet = MagicMock()
    child_sheet.columns = ['id', 'parent_id', 'value']
    child_sheet.rows = [
        {'id': None, 'parent_id': None, 'value': 10},
        {'id': None, 'parent_id': None, 'value': 11},
    ]

    # read_excel_file: ファイル別にシート名→ダミー DataFrame (後で normalize で置換)
    def mock_read_side_effect(path, target_sheets=None, keep_na_strings=None):
        if 'parents' in str(path):
            return {'Parents': MagicMock()}
        return {'Children': MagicMock()}

    # batch_insert 振る舞い: parent で returning, child で non-returning を記録
    parent_returned = [(1, 'Alice'), (2, 'Bob')]
    inserted_calls: list[tuple] = []

    def mock_batch_insert(cursor, table, columns, rows, returning=False, page_size=1000, metrics_callback=None):  # noqa: D401
        inserted_calls.append((table, returning, list(rows)))
        if returning:
            return InsertResult(inserted_rows=len(rows), returned_values=parent_returned)
        return InsertResult(inserted_rows=len(rows), returned_values=None)

    # cursor モック: description で列名提供
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    # parent RETURNING の後 fetchall() を呼ばれるので side_effect ではなく batch_insert 内で処理済ため不要
    # description を parent の RETURNING * 結果想定列順 ['id','name'] に設定
    mock_cursor.description = [('id',), ('name',)]

    with patch('src.services.orchestrator.read_excel_file') as mock_read, \
         patch('src.services.orchestrator.normalize_sheet') as mock_norm, \
         patch('src.services.orchestrator.batch_insert', side_effect=mock_batch_insert):
        mock_read.side_effect = mock_read_side_effect
        # Parents → Children の順に normalize 呼び出し (ファイル列挙順依存). Return appropriate object by sheet name param.
        def norm_side_effect(df, sheet_name, expected_columns=None, default_values=None):
            return parent_sheet if sheet_name == 'Parents' else child_sheet
        mock_norm.side_effect = norm_side_effect

        result = process_all(config, cursor=mock_cursor)

    # 検証: parent returning=True, child returning=False
    assert any(t == 'parents' and r is True for t, r, _ in inserted_calls)
    assert any(t == 'children' and r is False for t, r, _ in inserted_calls)
    # 成功数 2
    assert result.success_files == 2
    # 親マップ由来で children も 2 行挿入
    assert result.total_inserted_rows == 4
