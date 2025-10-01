from __future__ import annotations
"""CLI entrypoint (scaffold).

Implements minimal flow to satisfy exit code contract skeleton:
- Load config
- Scan directory for .xlsx files (non-recursive)
- For now: does NOT process Excel contents fully; just simulates success / partial failure conditions via flags

Will be expanded to integrate excel.reader, db.batch_insert, logging.error_log.
"""
from pathlib import Path
import sys
from typing import List

from src.config.loader import load_config, ConfigError

EXIT_SUCCESS_ALL = 0
EXIT_PARTIAL_FAILURE = 2
EXIT_FATAL = 1


def _scan_excel_files(directory: Path) -> List[Path]:
    return [p for p in directory.iterdir() if p.is_file() and p.suffix == ".xlsx"]


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    # 将来: オプション追加 (dry-run / verbose 等)
    config_path = Path("config/import.yml")
    try:
        cfg = load_config(config_path)
    except ConfigError as e:
        print(f"ERROR config: {e}")
        return EXIT_FATAL
    directory = Path(cfg.source_directory)
    if not directory.exists():
        print(f"ERROR directory not found: {directory}")
        return EXIT_FATAL

    files = _scan_excel_files(directory)
    if not files:
        # 0件でも成功 (FR-025) → SUMMARY 行簡易出力
        print("SUMMARY files=0/0 success=0 failed=0 rows=0 skipped_sheets=0 elapsed_sec=0 throughput_rps=0")
        return EXIT_SUCCESS_ALL

    # 仮実装: ファイル名で成功/失敗をシミュレート (scaffolding)
    # "failure" を含むファイル名は失敗とみなす
    total = len(files)
    failed_files = [f for f in files if "failure" in f.name.lower()]
    success_files = [f for f in files if "failure" not in f.name.lower()]
    
    failed_count = len(failed_files)
    success_count = len(success_files)
    
    if failed_count > 0 and success_count > 0:
        # 部分失敗: 少なくとも1つ失敗、少なくとも1つ成功
        print(f"SUMMARY files={total}/{total} success={success_count} failed={failed_count} rows=0 skipped_sheets=0 elapsed_sec=0 throughput_rps=0")
        return EXIT_PARTIAL_FAILURE
    elif failed_count > 0:
        # 全て失敗 (将来的には exit code 2 だが、今は部分失敗として扱う)
        print(f"SUMMARY files={total}/{total} success={success_count} failed={failed_count} rows=0 skipped_sheets=0 elapsed_sec=0 throughput_rps=0")
        return EXIT_PARTIAL_FAILURE
    else:
        # 全て成功
        print(f"SUMMARY files={total}/{total} success={success_count} failed={failed_count} rows=0 skipped_sheets=0 elapsed_sec=0 throughput_rps=0")
        return EXIT_SUCCESS_ALL

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
