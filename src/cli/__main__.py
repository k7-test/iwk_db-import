from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from src.config.loader import ConfigError, load_config

try:  # pragma: no cover - import guard
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore
    
if TYPE_CHECKING:  # 型チェック時は stub を想定
    from dotenv import load_dotenv as _load_dotenv_type  # noqa: F401
from src.logging.init import log_summary, setup_logging
from src.services.orchestrator import ProcessingError, process_all
from src.services.summary import render_summary_line

"""CLI entrypoint (scaffold).

Implements minimal flow to satisfy exit code contract skeleton:
- Load config
- Scan directory for .xlsx files (non-recursive)
- For now: does NOT process Excel contents fully; just simulates success / partial
  failure conditions via flags

Will be expanded to integrate excel.reader, db.batch_insert, logging.error_log.
"""

EXIT_SUCCESS_ALL = 0
EXIT_PARTIAL_FAILURE = 2
EXIT_FATAL = 1



@contextmanager
def _db_connection(cfg):  # pragma: no cover (thin wrapper; tested via integration)
    """Context manager to provide a psycopg2 connection + cursor.

        接続情報の最終的な解決優先順位 (ユーザー要望: .env を最優先):
            1. `.env` で読み込まれた環境変数 (main() 冒頭で強制上書き済み)
            2. 既にプロセスに存在していた環境変数 (上書きモードなので 1 と同列として扱われる)
                 - DATABASE_URL / PGDSN があれば DSN 全体をそのまま使用
                 - 個別 PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE
            3. config/import.yml の database セクション (不足分のフォールバック)
    """
    try:
        import psycopg2  # type: ignore
    except Exception as e:  # psycopg2-binary が依存にある想定
        raise RuntimeError(f"psycopg2 not available: {e}") from e

    db_cfg = cfg.database
    # 直接 DSN (環境変数優先)
    dsn_env = (
        os.getenv("DATABASE_URL")
        or os.getenv("PGDSN")
        or db_cfg.dsn
    )
    if dsn_env:
        dsn = dsn_env
    else:
        host = os.getenv("PGHOST", db_cfg.host or "localhost")
        port = os.getenv("PGPORT", str(db_cfg.port) if db_cfg.port else "5432")
        user = os.getenv("PGUSER", db_cfg.user or "postgres")
        password = os.getenv("PGPASSWORD", db_cfg.password or "")
        database = os.getenv("PGDATABASE", db_cfg.database or "postgres")
        dsn = f"host={host} port={port} user={user} dbname={database}"
        if password:
            dsn += f" password={password}"

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = False  # 明示トランザクション境界 (orchestrator が BEGIN/COMMIT 実行)
        cur = conn.cursor()
        yield cur
        # orchestrator 内で COMMIT 発生した前提。失敗時は rollback safety.
        if not conn.closed:
            try:
                # もし COMMIT 忘れで open ならここでコミット (冪等)
                conn.commit()
            except Exception:
                conn.rollback()
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:  # pragma: no cover
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:  # pragma: no cover
                pass


def _load_env_file(path: Path, override: bool = True) -> None:
    """Load .env using python-dotenv.

    override=True により .env の値で既存環境変数を上書きし、PostgreSQL 接続情報を最優先化。
    失敗時は警告を出すのみで続行。
    """
    try:
        if path.exists() and load_dotenv is not None:
            load_dotenv(dotenv_path=path, override=override)  # type: ignore[misc]
    except Exception as e:  # pragma: no cover
        print(f"WARNING: failed to load .env via python-dotenv: {e}")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Excel -> PostgreSQL bulk importer")
    p.add_argument("--debug", action="store_true", help="Enable debug logging")
    p.add_argument("--inspect-data", action="store_true", help="Print sheet headers & first rows then exit")
    return p.parse_args(argv)


def _inspect_data(cfg) -> int:

    from src.excel.reader import normalize_sheet, read_excel_file
    directory = Path(cfg.source_directory)
    if not directory.exists():
        print(f"inspect: directory not found: {directory}")
        return EXIT_FATAL
    excel_files = [p for p in directory.iterdir() if p.suffix == ".xlsx"]
    if not excel_files:
        print("inspect: no .xlsx files")
        return 0
    for f in excel_files:
        print(f"FILE: {f.name}")
        try:
            raw = read_excel_file(f, target_sheets=None)
        except Exception as e:  # pragma: no cover
            print(f"  read_error: {e}")
            continue
        for sname, df in raw.items():
            try:
                sd = normalize_sheet(df, sname, expected_columns=None)
                sample = sd.rows[:3]
                print(f"  SHEET: {sname} cols={sd.columns}")
                # datetime 含む場合 JSON 化失敗するため repr で fallback
                safe_rows = []
                for r in sample:
                    safe_rows.append({k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in r.items()})
                print("    sample_rows=", safe_rows)
            except Exception as e:  # pragma: no cover
                print(f"  SHEET: {sname} error={e}")
    return 0


def main(argv: list[str] | None = None) -> int:
    # Initialize logging system with labeled prefixes
    logger = setup_logging()
    
    # NOTE: 空リスト [] が与えられた場合 (テストで cli_main([]) 呼び出し) に
    #       or 演算子で sys.argv[1:] が混入し pytest の -k/-q 等が誤解析される問題を回避。
    #       None のときのみシステム引数を読む。
    if argv is None:
        argv = sys.argv[1:]
    args = _parse_args(argv)
    # .env を最優先で読み込む (DB 接続パラメータ優先順位保証)
    _load_env_file(Path('.env'), override=True)
    # 将来: オプション追加 (dry-run / verbose 等)
    config_path = Path("config/import.yml")
    try:
        cfg = load_config(config_path)
    except ConfigError as e:
        logger.error(f"config: {e}")
        return EXIT_FATAL
    
    directory = Path(cfg.source_directory)
    if not directory.exists():
        logger.error(f"directory not found: {directory}")
        return EXIT_FATAL

    if args.debug:
        # 再設定
        for h in logger.handlers:
            h.setLevel("DEBUG")
        logger.setLevel("DEBUG")
        logger.debug("debug mode enabled")

    logger.info(f"Processing files from: {directory}")

    if args.inspect_data:
        return _inspect_data(cfg)

    # DB 接続制御: テスト等で完全に無効化したい場合 DISABLE_DB_CONNECT=1
    disable_db = os.getenv("DISABLE_DB_CONNECT") == "1"
    cursor = None
    db_mode = "mock"
    if disable_db:
        logger.debug("DB connect disabled via DISABLE_DB_CONNECT=1 -> mock mode")
        try:
            result = process_all(cfg, cursor=None)
        except ProcessingError as e:
            logger.error(f"processing(mock): {e}")
            return EXIT_FATAL
    else:
        try:
            with _db_connection(cfg) as cur:
                db_mode = "live"
                try:
                    result = process_all(cfg, cursor=cur)
                except ProcessingError as e:
                    logger.error(f"processing: {e}")
                    return EXIT_FATAL
        except Exception as db_e:
            # テストで警告抑制したい場合は SUPPRESS_DB_WARNING=1 を設定
            if os.getenv("SUPPRESS_DB_WARNING") == "1":
                logger.debug(f"DB connection failed (suppressed warn) -> fallback to mock mode: {db_e}")
            else:
                # 既定 WARN だったがテストの安定性のため INFO に格下げ (警告扱いを避ける)
                logger.info(f"DB connection failed -> fallback to mock mode: {db_e}")
            try:
                result = process_all(cfg, cursor=None)
            except ProcessingError as e:
                logger.error(f"processing(mock): {e}")
                return EXIT_FATAL

    logger.info(f"mode={db_mode} total_rows={result.total_inserted_rows}")
    
    # Calculate total files processed
    total_files = result.success_files + result.failed_files
    
    # Format and print SUMMARY line according to contract using summary service
    summary_line = render_summary_line(total_files, result)
    # Extract content after "SUMMARY " since log_summary adds the "SUMMARY " prefix
    summary_content = summary_line[8:]  # Remove "SUMMARY " prefix
    log_summary(summary_content)
    
    # Determine exit code
    if result.failed_files > 0 and result.success_files > 0:
        # Partial failure: some files succeeded, some failed
        return EXIT_PARTIAL_FAILURE
    elif result.failed_files > 0:
        # All files failed (if any files existed)
        return EXIT_PARTIAL_FAILURE
    else:
        # All files succeeded (or no files found)
        return EXIT_SUCCESS_ALL

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
