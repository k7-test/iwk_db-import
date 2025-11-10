from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.cli import main as cli_main
from src.logging.init import reset_logging
from src.models.processing_result import ProcessingResult


def test_cli_live_mode_success(temp_workdir: Path, write_config: Path, capsys):
    """Test CLI live DB path (mocked connection) to raise coverage of live branch.

    - Patches _db_connection context manager to yield a mock cursor
    - Ensures mode=live appears in output and exit code is success.
    """
    reset_logging()

    mock_result = ProcessingResult(
        success_files=1,
        failed_files=0,
        total_inserted_rows=5,
        skipped_sheets=0,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(seconds=0.5),
        elapsed_seconds=0.5,
        throughput_rows_per_sec=10.0,
    )

    class DummyCtx:
        def __init__(self, cursor):
            self.cursor = cursor
        def __enter__(self):
            return self.cursor
        def __exit__(self, exc_type, exc, tb):
            return False

    mock_cursor = MagicMock()

    with patch('src.cli.__main__._db_connection', return_value=DummyCtx(mock_cursor)), \
         patch('src.cli.__main__.process_all', return_value=mock_result):
        # Move into temp working directory with config
        import os
        cwd_before = os.getcwd()
        try:
            os.chdir(temp_workdir)
            code = cli_main([])
        finally:
            os.chdir(cwd_before)

    captured = capsys.readouterr()
    out = captured.out
    assert code == 0
    assert 'mode=live' in out
