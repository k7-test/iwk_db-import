from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

from src.cli import main as cli_main
from src.logging.init import reset_logging


def test_cli_inspect_data_branch(temp_workdir: Path, write_config: Path, capsys):
    """--inspect-data 分岐 (早期リターン) をカバーしてカバレッジ向上。

    read_excel_file と normalize_sheet をモックし、_inspect_data ループ内の
    sample_rows 出力ロジック (datetime 変換含む) を通過させる。
    """
    reset_logging()

    # Excel ファイルを 1 つ生成
    data_dir = temp_workdir / 'data'
    (data_dir / 'sample.xlsx').write_bytes(b"test")

    # 正規化後オブジェクト (必要プロパティのみ)
    norm_obj = MagicMock()
    norm_obj.columns = ['col1', 'col2']
    norm_obj.rows = [
        {'col1': 'v1', 'col2': 123},
        {'col1': 'v2', 'col2': 456},
    ]

    # CLI 内の _inspect_data では from src.excel.reader import read_excel_file, normalize_sheet
    # をローカル import しているため直接パッチ不可。orchestrator ルートの関数をパッチし、
    # 実体の呼び出しを差し替える。
    with patch('src.excel.reader.read_excel_file', return_value={'SheetA': MagicMock()}), \
        patch('src.excel.reader.normalize_sheet', return_value=norm_obj):
        import os
        cwd_before = os.getcwd()
        try:
            os.chdir(temp_workdir)
            code = cli_main(["--inspect-data"])
        finally:
            os.chdir(cwd_before)

    captured = capsys.readouterr()
    out = captured.out
    assert code == 0
    assert 'FILE: sample.xlsx' in out
    assert 'SHEET: SheetA cols=' in out
    assert 'sample_rows=' in out  # サンプル行表示
