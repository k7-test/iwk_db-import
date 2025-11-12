from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config.loader import load_config
from src.db.batch_insert import BatchMetrics, batch_insert
from src.excel.reader import MissingColumnsError
from src.models.config_models import DatabaseConfig, ImportConfig
from src.services.fk_propagation import build_fk_propagation_maps, needs_returning
from src.services.orchestrator import process_all


def test_orchestrator_commit_failure_triggers_rollback(temp_workdir: Path, write_config: Path):
    cfg = load_config(write_config)
    data_dir = temp_workdir / 'data'
    (data_dir / 'only.xlsx').write_bytes(b'test')

    # Sheet mapping: simple
    cfg.sheet_mappings['Only'] = {
        'table': 'only_table',
        'sequence_columns': [],
        'fk_propagation_columns': [],
        'default_values': None,
    }

    sheet_mock = MagicMock()
    sheet_mock.columns = ['id']
    sheet_mock.rows = [{'id': 1}]

    mock_cursor = MagicMock()
    # BEGIN succeeds, COMMIT fails
    def exec_side_effect(sql):
        if sql == 'COMMIT':
            raise Exception('commit fail')
    mock_cursor.execute.side_effect = exec_side_effect

    insert_result = MagicMock(inserted_rows=1, returned_values=None)

    with patch('src.services.orchestrator.read_excel_file', return_value={'Only': MagicMock()}), \
         patch('src.services.orchestrator.normalize_sheet', return_value=sheet_mock), \
         patch('src.services.orchestrator.batch_insert', return_value=insert_result):
        result = process_all(cfg, cursor=mock_cursor)

    # Should be marked failed due to commit failure
    assert result.failed_files == 1
    assert result.success_files == 0


def test_orchestrator_sheet_missing_columns(temp_workdir: Path, write_config: Path):
    cfg = load_config(write_config)
    data_dir = temp_workdir / 'data'
    (data_dir / 'miss.xlsx').write_bytes(b'test')

    # mapping expects column 'required'
    cfg.sheet_mappings['Miss'] = {
        'table': 'miss_table',
        'sequence_columns': [],
        'fk_propagation_columns': [],
        'default_values': None,
    }

    # normalize_sheet で MissingColumnsError を投げる
    with patch('src.services.orchestrator.read_excel_file', return_value={'Miss': MagicMock()}), \
         patch('src.services.orchestrator.normalize_sheet', side_effect=MissingColumnsError('sheet "Miss" missing columns: ["required"]')):
        result = process_all(cfg, cursor=None)

    # ファイルは失敗扱い
    assert result.failed_files == 1
    assert result.success_files == 0


def test_cli_inspect_data_mode(temp_workdir: Path, write_config: Path, capsys):
    from src.cli import main as cli_main
    from src.logging.init import reset_logging
    reset_logging()
    # config 内に data ディレクトリは存在するが xlsx を置かない: inspect で 0 ファイル
    code = 0
    import os
    cwd_before = os.getcwd()
    try:
        os.chdir(temp_workdir)
        code = cli_main(['--inspect-data'])
    finally:
        os.chdir(cwd_before)
    out = capsys.readouterr().out
    assert code == 0
    assert 'inspect:' in out


def test_batch_insert_metrics_callback(monkeypatch):
    # execute_values を完全モックして cursor.connection 依存を排除
    from src.db import batch_insert as bi_mod
    calls: list[tuple] = []
    def fake_execute_values(cur, sql, rows, page_size=100, fetch=False):  # noqa: D401
        calls.append((sql, list(rows)))
        # fetch=True の場合を想定しない (batch_insert 後で fetchall 呼ぶ)
        return None
    monkeypatch.setattr(bi_mod, 'execute_values', fake_execute_values)

    class DummyCursor:
        def fetchall(self):
            return [(1,), (2,)]
    cur = DummyCursor()
    metrics: list[BatchMetrics] = []
    def cb(m: BatchMetrics):
        metrics.append(m)
    res = batch_insert(cur, 't', ['col'], [(1,), (2,)], returning=True, metrics_callback=cb)
    assert res.inserted_rows == 2
    assert res.returned_values == [(1,), (2,)]
    assert calls and 'INSERT INTO t' in calls[0][0]
    assert metrics and metrics[0].batch_size == 2 and metrics[0].elapsed_seconds >= 0.0


def test_batch_insert_empty_rows_short_circuit(monkeypatch):
    from src.db import batch_insert as bi_mod
    # execute_values が呼ばれないことを検証するため sentinel をセット
    called = {'flag': False}
    def fake_execute_values(*a, **k):  # pragma: no cover - should not be invoked
        called['flag'] = True
    monkeypatch.setattr(bi_mod, 'execute_values', fake_execute_values)
    class C: pass
    cur = C()
    res = bi_mod.batch_insert(cur, 't', ['c'], [], returning=False)
    assert res.inserted_rows == 0
    assert res.returned_values is None
    assert called['flag'] is False


def test_orchestrator_error_log_flush_failure(temp_workdir: Path, write_config: Path):
    """Covers error_log.flush() 例外握りつぶしパス."""
    cfg = load_config(write_config)
    data_dir = temp_workdir / 'data'
    (data_dir / 'flush.xlsx').write_bytes(b'test')
    cfg.sheet_mappings['Flush'] = {
        'table': 'flush_table',
        'sequence_columns': [],
        'fk_propagation_columns': [],
        'default_values': None,
    }
    sheet_mock = MagicMock()
    sheet_mock.columns = ['id']
    sheet_mock.rows = [{'id': 1}]
    with patch('src.services.orchestrator.read_excel_file', return_value={'Flush': MagicMock()}), \
         patch('src.services.orchestrator.normalize_sheet', return_value=sheet_mock), \
         patch('src.services.orchestrator.batch_insert', return_value=MagicMock(inserted_rows=1, returned_values=None)), \
         patch('src.services.orchestrator.ErrorLogBuffer.flush', side_effect=Exception('flush boom')):
        result = process_all(cfg, cursor=None)
    assert result.success_files == 1


def test_fk_propagation_build_maps_list_format():
    config = ImportConfig(
        source_directory='data',
        sheet_mappings={},
        sequences={'parents.id': 'seq'},
        fk_propagations=[{'parent': 'parents.name', 'child': 'children.parent_id'}],
        timezone='UTC',
        database=DatabaseConfig(host=None, port=None, user=None, password=None, database=None, dsn=None)
    )
    maps = build_fk_propagation_maps(config)
    assert len(maps) == 1
    assert maps[0].parent_table == 'parents'
    assert maps[0].parent_identifier_column == 'name'
    assert maps[0].child_fk_column == 'parent_id'
    assert maps[0].parent_pk_column in {'id', 'name'}  # fallback vs inference
    # needs_returning True before child processed
    assert needs_returning('parents', config, processed_tables=set()) is True
    # After child processed -> False
    assert needs_returning('parents', config, processed_tables={'children'}) is False

