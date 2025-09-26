from __future__ import annotations
from pathlib import Path
from src.cli import main as cli_main


def test_cli_no_files_success(write_config, temp_workdir: Path, capsys):
    import os
    # Remove created dummy excel files if fixture added them (safety)
    data_dir = temp_workdir / 'data'
    for f in data_dir.glob('*.xlsx'):
        f.unlink()
    cwd_before = os.getcwd()
    try:
        os.chdir(temp_workdir)
        code = cli_main([])
    finally:
        os.chdir(cwd_before)
    out = capsys.readouterr().out
    assert code == 0
    assert 'SUMMARY files=0/0 success=0 failed=0 rows=0' in out


def test_cli_directory_missing(write_config, temp_workdir: Path, capsys):
    import os
    # break source_directory in config
    cfg_path = temp_workdir / 'config' / 'import.yml'
    text = cfg_path.read_text(encoding='utf-8').replace('./data', './missing_dir')
    cfg_path.write_text(text, encoding='utf-8')
    cwd_before = os.getcwd()
    try:
        os.chdir(temp_workdir)
        code = cli_main([])
    finally:
        os.chdir(cwd_before)
    out = capsys.readouterr().out
    assert code == 1
    assert 'ERROR directory not found:' in out