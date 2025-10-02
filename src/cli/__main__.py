from __future__ import annotations

import sys
from pathlib import Path

from src.config.loader import ConfigError, load_config
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



def main(argv: list[str] | None = None) -> int:
    # Initialize logging system with labeled prefixes
    logger = setup_logging()
    
    argv = argv or sys.argv[1:]
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

    logger.info(f"Processing files from: {directory}")

    # Process all files using orchestrator
    try:
        result = process_all(cfg, cursor=None)  # Mock mode for now
    except ProcessingError as e:
        logger.error(f"processing: {e}")
        return EXIT_FATAL
    
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
