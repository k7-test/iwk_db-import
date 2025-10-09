from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from src.services.progress import ProgressTracker, SheetProgressIndicator, is_tty_enabled


def test_is_tty_enabled_returns_stdout_isatty():
    """Test that is_tty_enabled returns sys.stdout.isatty()."""
    with patch('sys.stdout.isatty', return_value=True):
        assert is_tty_enabled() is True
    
    with patch('sys.stdout.isatty', return_value=False):
        assert is_tty_enabled() is False


class TestProgressTracker:
    """Test cases for ProgressTracker class."""
    
    def test_init_with_tty_enabled(self):
        """Test ProgressTracker initialization when TTY is enabled."""
        with patch('src.services.progress.is_tty_enabled', return_value=True), \
             patch('src.services.progress.tqdm') as mock_tqdm:
            
            tracker = ProgressTracker(5, description="Test files")
            
            assert tracker.total_files == 5
            assert tracker.description == "Test files"
            assert tracker.current_file == 0
            assert tracker.enabled is True
            
            # Should create tqdm instance
            mock_tqdm.assert_called_once_with(
                total=5,
                desc="Test files",
                unit="file",
                disable=False,
                leave=True,
                position=0,
                ncols=80,
                ascii=True,
            )
    
    def test_init_with_tty_disabled(self):
        """Test ProgressTracker initialization when TTY is disabled."""
        with patch('src.services.progress.is_tty_enabled', return_value=False):
            tracker = ProgressTracker(5, description="Test files")
            
            assert tracker.total_files == 5
            assert tracker.description == "Test files"
            assert tracker.current_file == 0
            assert tracker.enabled is False
            assert tracker.pbar is None
    
    def test_start_file_with_tty_enabled(self):
        """Test start_file when TTY is enabled."""
        mock_pbar = Mock()
        
        with patch('src.services.progress.is_tty_enabled', return_value=True), \
             patch('src.services.progress.tqdm', return_value=mock_pbar):
            
            tracker = ProgressTracker(3, description="Processing")
            file_path = Path("test.xlsx")
            
            tracker.start_file(file_path)
            
            assert tracker.current_file == 1
            mock_pbar.set_description.assert_called_once_with("Processing (test.xlsx)")
    
    def test_start_file_with_tty_disabled(self):
        """Test start_file when TTY is disabled."""
        with patch('src.services.progress.is_tty_enabled', return_value=False):
            tracker = ProgressTracker(3, description="Processing")
            file_path = Path("test.xlsx")
            
            tracker.start_file(file_path)
            
            assert tracker.current_file == 1
            # Should not raise any errors
    
    def test_finish_file_with_tty_enabled(self):
        """Test finish_file when TTY is enabled."""
        mock_pbar = Mock()
        
        with patch('src.services.progress.is_tty_enabled', return_value=True), \
             patch('src.services.progress.tqdm', return_value=mock_pbar):
            
            tracker = ProgressTracker(3, description="Processing")
            
            tracker.finish_file(success=True)
            
            mock_pbar.update.assert_called_once_with(1)
            mock_pbar.set_description.assert_called_once_with("Processing")
    
    def test_finish_file_with_tty_disabled(self):
        """Test finish_file when TTY is disabled."""
        with patch('src.services.progress.is_tty_enabled', return_value=False):
            tracker = ProgressTracker(3, description="Processing")
            
            tracker.finish_file(success=True)
            
            # Should not raise any errors
    
    def test_set_postfix_with_tty_enabled(self):
        """Test set_postfix when TTY is enabled."""
        mock_pbar = Mock()
        
        with patch('src.services.progress.is_tty_enabled', return_value=True), \
             patch('src.services.progress.tqdm', return_value=mock_pbar):
            
            tracker = ProgressTracker(3)
            tracker.set_postfix(success=2, failed=0, rows=100)
            
            mock_pbar.set_postfix.assert_called_once_with(success=2, failed=0, rows=100)
    
    def test_set_postfix_with_tty_disabled(self):
        """Test set_postfix when TTY is disabled."""
        with patch('src.services.progress.is_tty_enabled', return_value=False):
            tracker = ProgressTracker(3)
            tracker.set_postfix(success=2, failed=0, rows=100)
            
            # Should not raise any errors
    
    def test_close_with_tty_enabled(self):
        """Test close when TTY is enabled."""
        mock_pbar = Mock()
        
        with patch('src.services.progress.is_tty_enabled', return_value=True), \
             patch('src.services.progress.tqdm', return_value=mock_pbar):
            
            tracker = ProgressTracker(3)
            tracker.close()
            
            mock_pbar.close.assert_called_once()
            assert tracker.pbar is None
    
    def test_close_with_tty_disabled(self):
        """Test close when TTY is disabled."""
        with patch('src.services.progress.is_tty_enabled', return_value=False):
            tracker = ProgressTracker(3)
            tracker.close()
            
            # Should not raise any errors
    
    def test_context_manager(self):
        """Test ProgressTracker as context manager."""
        mock_pbar = Mock()
        
        with patch('src.services.progress.is_tty_enabled', return_value=True), \
             patch('src.services.progress.tqdm', return_value=mock_pbar):
            
            with ProgressTracker(3) as tracker:
                assert isinstance(tracker, ProgressTracker)
            
            # Should call close on exit
            mock_pbar.close.assert_called_once()


class TestSheetProgressIndicator:
    """Test cases for SheetProgressIndicator class."""
    
    def test_init(self):
        """Test SheetProgressIndicator initialization."""
        with patch('src.services.progress.is_tty_enabled', return_value=True):
            indicator = SheetProgressIndicator("test.xlsx", 3)
            
            assert indicator.file_name == "test.xlsx"
            assert indicator.total_sheets == 3
            assert indicator.current_sheet == 0
            assert indicator.enabled is True
    
    def test_start_sheet_with_tty_enabled(self):
        """Test start_sheet when TTY is enabled."""
        with patch('src.services.progress.is_tty_enabled', return_value=True), \
             patch('builtins.print') as mock_print:
            
            indicator = SheetProgressIndicator("test.xlsx", 2)
            indicator.start_sheet("Sheet1")
            
            assert indicator.current_sheet == 1
            mock_print.assert_called_once_with("  Sheet 1/2: Sheet1", end="", flush=True)
    
    def test_start_sheet_with_tty_disabled(self):
        """Test start_sheet when TTY is disabled."""
        with patch('src.services.progress.is_tty_enabled', return_value=False), \
             patch('builtins.print') as mock_print:
            
            indicator = SheetProgressIndicator("test.xlsx", 2)
            indicator.start_sheet("Sheet1")
            
            assert indicator.current_sheet == 1
            mock_print.assert_not_called()
    
    def test_finish_sheet_success_with_rows(self):
        """Test finish_sheet with success and rows processed."""
        with patch('src.services.progress.is_tty_enabled', return_value=True), \
             patch('builtins.print') as mock_print:
            
            indicator = SheetProgressIndicator("test.xlsx", 2)
            indicator.finish_sheet(success=True, rows_processed=100)
            
            mock_print.assert_called_once_with(" - 100 rows ✓")
    
    def test_finish_sheet_success_without_rows(self):
        """Test finish_sheet with success but no rows."""
        with patch('src.services.progress.is_tty_enabled', return_value=True), \
             patch('builtins.print') as mock_print:
            
            indicator = SheetProgressIndicator("test.xlsx", 2)
            indicator.finish_sheet(success=True, rows_processed=0)
            
            mock_print.assert_called_once_with(" ✓")
    
    def test_finish_sheet_failure(self):
        """Test finish_sheet with failure."""
        with patch('src.services.progress.is_tty_enabled', return_value=True), \
             patch('builtins.print') as mock_print:
            
            indicator = SheetProgressIndicator("test.xlsx", 2)
            indicator.finish_sheet(success=False, rows_processed=50)
            
            mock_print.assert_called_once_with(" - 50 rows ✗")
    
    def test_finish_sheet_with_tty_disabled(self):
        """Test finish_sheet when TTY is disabled."""
        with patch('src.services.progress.is_tty_enabled', return_value=False), \
             patch('builtins.print') as mock_print:
            
            indicator = SheetProgressIndicator("test.xlsx", 2)
            indicator.finish_sheet(success=True, rows_processed=100)
            
            mock_print.assert_not_called()