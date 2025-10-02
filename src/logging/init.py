from __future__ import annotations

import logging
import sys

"""Logging initialization with labeled prefixes.

T025 Implement logging initialization with labeled prefixes (INFO|WARN|ERROR|SUMMARY) 
and integrate error log buffer.

This module provides logging setup according to:
- QR-003: ラベル統一 (INFO|WARN|ERROR|SUMMARY prefixes)
- R-002: Use standard logging (no loguru)
- FR-030: Structured error logging

Integration with error log buffer from src.logging.error_log module.
"""

__all__ = [
    "setup_logging", 
    "get_logger",
]

# Custom SUMMARY level (between INFO=20 and WARNING=30)
SUMMARY_LEVEL = 25

# Global logger instance
_logger: logging.Logger | None = None


class LabeledFormatter(logging.Formatter):
    """Custom formatter that adds labeled prefixes to log messages.
    
    Formats log messages with labels according to QR-003:
    - INFO: for informational messages
    - WARN: for warning messages  
    - ERROR: for error messages
    - SUMMARY: for summary output
    """
    
    LEVEL_LABELS = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO", 
        logging.WARNING: "WARN",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
        SUMMARY_LEVEL: "SUMMARY",
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Get the appropriate label for the log level
        level_label = self.LEVEL_LABELS.get(record.levelno, record.levelname)
        
        # Format: LABEL message
        return f"{level_label} {record.getMessage()}"


def setup_logging() -> logging.Logger:
    """Setup logging with labeled prefixes for the application.
    
    Configures logging according to requirements:
    - QR-003: INFO|WARN|ERROR|SUMMARY labeled prefixes
    - R-002: Standard logging (no external dependencies)
    - Output to stdout for consistency with CLI contract
    
    Returns:
        Configured logger instance for the application
    """
    global _logger
    
    # Return existing logger if already configured (idempotent)
    if _logger is not None:
        return _logger
    
    # Add custom SUMMARY level to logging
    logging.addLevelName(SUMMARY_LEVEL, "SUMMARY")
    
    # Create logger
    logger = logging.getLogger("excel_pg_importer")
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers to avoid duplication
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # Set custom formatter
    formatter = LabeledFormatter()
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Prevent propagation to root logger to avoid duplicate output
    logger.propagate = False
    
    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """Get the configured application logger.
    
    Returns:
        The configured logger instance. Calls setup_logging() if not already configured.
    """
    if _logger is None:
        return setup_logging()
    return _logger


def log_summary(message: str) -> None:
    """Log a message at SUMMARY level.
    
    Convenience function for logging SUMMARY level messages.
    
    Args:
        message: The summary message to log
    """
    logger = get_logger()
    logger.log(SUMMARY_LEVEL, message)


def reset_logging() -> None:
    """Reset the global logger state. Mainly for testing purposes."""
    global _logger
    _logger = None