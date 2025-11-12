from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from src.cli import main as cli_main
from src.logging.init import reset_logging
from src.models.processing_result import ProcessingResult


def test_cli_debug_mode_mock_disable_db(temp_workdir: Path, write_config: Path, capsys, monkeypatch):
    """--debug 指定時に DEBUG ログ出力と mock モード経路が動作することを検証。

    - DISABLE_DB_CONNECT=1 により DB 接続を強制無効化 (live 分岐は既存テストでカバー済)
    - process_all をパッチして最小の ProcessingResult を返し高速化
    - DEBUG レベルメッセージ 'debug mode enabled' を検出
    """
    reset_logging()

    # 強制 mock モード
    monkeypatch.setenv("DISABLE_DB_CONNECT", "1")

    mock_result = ProcessingResult(
        success_files=0,
        failed_files=0,
        total_inserted_rows=0,
        skipped_sheets=0,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(seconds=0.01),
        elapsed_seconds=0.01,
        throughput_rows_per_sec=0.0,
    )

    with patch('src.cli.__main__.process_all', return_value=mock_result):
        # ワークスペース移動 (fixture が config/import.yml を配置済)
        import os
        cwd_before = os.getcwd()
        try:
            os.chdir(temp_workdir)
            code = cli_main(["--debug"])  # --debug 分岐を通す
        finally:
            os.chdir(cwd_before)

    captured = capsys.readouterr()
    out = captured.out
    assert code == 0
    # DEBUG ラベル付きログ出力を確認
    assert 'DEBUG debug mode enabled' in out
    # mode=mock 行も存在
    assert 'mode=mock' in out
