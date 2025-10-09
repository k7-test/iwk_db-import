from __future__ import annotations

import logging
from io import StringIO
from unittest.mock import patch

from src.logging.error_log import ErrorLogBuffer
from src.logging.init import get_logger, setup_logging
from src.models.error_record import ErrorRecord


def test_setup_logging_creates_logger_with_labeled_formatter():
    """Test that setup_logging creates a logger with labeled format."""
    logger = setup_logging()
    
    # Check logger configuration
    assert logger.name == "excel_pg_importer"
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1
    
    # Check handler configuration
    handler = logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    # Note: handler.stream might be different due to test environment


def test_logging_labeled_prefixes():
    """Test that logging outputs have correct labeled prefixes (INFO|WARN|ERROR|SUMMARY)."""
    import logging
    
    # Reset global logger to ensure clean state
    import src.logging.init
    src.logging.init.reset_logging()
    
    # Create a StringIO to capture output
    captured_output = StringIO()
    
    # Create a fresh logger with custom handler
    logger = logging.getLogger("test_excel_pg_importer")
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add custom SUMMARY level
    logging.addLevelName(25, "SUMMARY")
    
    # Create handler with our formatter
    from src.logging.init import LabeledFormatter
    handler = logging.StreamHandler(captured_output)
    handler.setLevel(logging.INFO)
    formatter = LabeledFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    
    # Test different log levels
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    logger.log(25, "Test summary message")  # Custom SUMMARY level
    
    # Get captured output
    output = captured_output.getvalue()
    lines = output.strip().split('\n')
    
    assert len(lines) == 4
    assert lines[0] == "INFO Test info message"
    assert lines[1] == "WARN Test warning message"
    assert lines[2] == "ERROR Test error message"
    assert lines[3] == "SUMMARY Test summary message"


def test_get_logger_returns_configured_logger():
    """Test that get_logger returns the configured logger instance."""
    # Setup logging first
    setup_logger = setup_logging()
    
    # Get logger
    logger = get_logger()
    
    assert logger is setup_logger
    assert logger.name == "excel_pg_importer"


def test_error_log_buffer_integration():
    """Test integration with ErrorLogBuffer."""
    logger = setup_logging()
    error_buffer = ErrorLogBuffer()
    
    # Test that logger and error buffer can work together
    record = ErrorRecord.create("test.xlsx", "Sheet1", 1, "TEST_ERROR", "test message")
    error_buffer.append(record)
    
    assert len(error_buffer) == 1
    
    # Logger should still work independently
    logger.info("Processing test.xlsx")
    
    # This test ensures both systems can coexist


def test_setup_logging_idempotent():
    """Test that calling setup_logging multiple times is safe."""
    logger1 = setup_logging()
    logger2 = setup_logging()
    
    # Should return the same logger instance
    assert logger1 is logger2
    
    # Should not create additional handlers
    assert len(logger1.handlers) == 1


def test_logging_with_progress_bar_disabled():
    """Test that logging works when progress bar should be disabled."""
    with patch('sys.stdout.isatty', return_value=False):
        logger = setup_logging()
        logger.info("Test message when not TTY")
        
        # Should still work normally
        assert logger.level == logging.INFO


def test_summary_level_logging():
    """Test custom SUMMARY level (25) logging."""
    logger = setup_logging()
    
    # Test that SUMMARY level is properly configured
    assert logging.getLevelName(25) == "SUMMARY"
    
    # Test logging at SUMMARY level
    with patch.object(logger, '_log') as mock_log:
        test_summary = (
            "files=1/1 success=1 failed=0 rows=100 skipped_sheets=0 "
            "elapsed_sec=1.5 throughput_rps=66.7"
        )
        logger.log(25, test_summary)
        mock_log.assert_called_once()


def test_log_summary_convenience_function():
    """Test the log_summary convenience function."""
    import logging
    
    # Reset global logger
    import src.logging.init
    src.logging.init._logger = None
    
    # Create a StringIO to capture output
    captured_output = StringIO()
    
    # Create a fresh logger with custom handler
    logger = logging.getLogger("excel_pg_importer")
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add custom SUMMARY level
    logging.addLevelName(25, "SUMMARY")
    
    # Create handler with our formatter
    from src.logging.init import LabeledFormatter, log_summary
    handler = logging.StreamHandler(captured_output)
    handler.setLevel(logging.INFO)
    formatter = LabeledFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    
    # Set as global logger
    src.logging.init._logger = logger
    
    # Test log_summary function
    log_summary(
        "files=2/2 success=2 failed=0 rows=150 skipped_sheets=0 elapsed_sec=2.5 throughput_rps=60.0"
    )
    
    # Get captured output
    output = captured_output.getvalue()
    lines = output.strip().split('\n')
    
    assert len(lines) == 1
    expected_line = (
        "SUMMARY files=2/2 success=2 failed=0 rows=150 skipped_sheets=0 "
        "elapsed_sec=2.5 throughput_rps=60.0"
    )
    assert lines[0] == expected_line