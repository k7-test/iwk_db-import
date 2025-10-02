from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.models.processing_result import FileStat, MetricsSnapshot, ProcessingResult

"""Unit tests for processing result models (T019).

Tests the dataclass models defined in src/models/processing_result.py to ensure
they correctly implement the data-model.md specifications.
"""


class TestFileStat:
    """Test FileStat dataclass."""
    
    def test_file_stat_creation(self):
        """Test FileStat can be created with required fields."""
        stat = FileStat(
            file_name="test.xlsx",
            status="success", 
            inserted_rows=100,
            elapsed_seconds=1.5
        )
        
        assert stat.file_name == "test.xlsx"
        assert stat.status == "success"
        assert stat.inserted_rows == 100
        assert stat.elapsed_seconds == 1.5
    
    def test_file_stat_immutable(self):
        """Test FileStat is frozen/immutable."""
        stat = FileStat("test.xlsx", "success", 100, 1.5)
        
        with pytest.raises(AttributeError):
            stat.file_name = "other.xlsx"


class TestProcessingResult:
    """Test ProcessingResult dataclass."""
    
    def test_processing_result_creation(self):
        """Test ProcessingResult can be created with required fields."""
        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 10, 1, 30, tzinfo=UTC)
        
        result = ProcessingResult(
            success_files=2,
            failed_files=1,
            total_inserted_rows=250,
            skipped_sheets=0,
            start_time=start,
            end_time=end, 
            elapsed_seconds=90.0,
            throughput_rows_per_sec=2.78
        )
        
        assert result.success_files == 2
        assert result.failed_files == 1
        assert result.total_inserted_rows == 250
        assert result.skipped_sheets == 0
        assert result.start_time == start
        assert result.end_time == end
        assert result.elapsed_seconds == 90.0
        assert result.throughput_rows_per_sec == 2.78
        assert result.file_stats is None  # Optional field defaults to None
    
    def test_processing_result_with_file_stats(self):
        """Test ProcessingResult with optional file_stats list."""
        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 10, 1, 30, tzinfo=UTC)
        
        file_stats = [
            FileStat("file1.xlsx", "success", 150, 45.0),
            FileStat("file2.xlsx", "success", 100, 45.0)
        ]
        
        result = ProcessingResult(
            success_files=2,
            failed_files=0,
            total_inserted_rows=250,
            skipped_sheets=0,
            start_time=start,
            end_time=end,
            elapsed_seconds=90.0,
            throughput_rows_per_sec=2.78,
            file_stats=file_stats
        )
        
        assert result.file_stats == file_stats
        assert len(result.file_stats) == 2
        assert result.file_stats[0].file_name == "file1.xlsx"
    
    def test_processing_result_immutable(self):
        """Test ProcessingResult is frozen/immutable."""
        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 10, 1, 30, tzinfo=UTC)
        
        result = ProcessingResult(
            success_files=2, failed_files=1, total_inserted_rows=250,
            skipped_sheets=0, start_time=start, end_time=end,
            elapsed_seconds=90.0, throughput_rows_per_sec=2.78
        )
        
        with pytest.raises(AttributeError):
            result.success_files = 3


class TestMetricsSnapshot:
    """Test MetricsSnapshot dataclass."""
    
    def test_metrics_snapshot_creation(self):
        """Test MetricsSnapshot can be created with required fields."""
        last_update = datetime(2024, 1, 1, 10, 5, 30, tzinfo=UTC)
        
        snapshot = MetricsSnapshot(
            current_file_index=1,
            total_files=3,
            current_sheet="Sheet1",
            processed_rows_in_file=50,
            last_update=last_update
        )
        
        assert snapshot.current_file_index == 1
        assert snapshot.total_files == 3
        assert snapshot.current_sheet == "Sheet1"
        assert snapshot.processed_rows_in_file == 50
        assert snapshot.last_update == last_update
    
    def test_metrics_snapshot_immutable(self):
        """Test MetricsSnapshot is frozen/immutable."""
        snapshot = MetricsSnapshot(
            current_file_index=1, total_files=3, current_sheet="Sheet1",
            processed_rows_in_file=50, 
            last_update=datetime(2024, 1, 1, 10, 5, 30, tzinfo=UTC)
        )
        
        with pytest.raises(AttributeError):
            snapshot.current_file_index = 2


class TestModelIntegration:
    """Test integration between models."""
    
    def test_processing_result_with_file_stats_integration(self):
        """Test that ProcessingResult correctly aggregates FileStat data."""
        # Create file stats that should match the totals
        file_stats = [
            FileStat("file1.xlsx", "success", 75, 30.0),
            FileStat("file2.xlsx", "success", 125, 45.0),
            FileStat("file3.xlsx", "failed", 0, 15.0)  # Failed file contributes 0 rows
        ]
        
        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 10, 1, 30, tzinfo=UTC)
        
        result = ProcessingResult(
            success_files=2,  # 2 succeeded
            failed_files=1,   # 1 failed
            total_inserted_rows=200,  # 75 + 125 = 200 (failed files don't contribute)
            skipped_sheets=0,
            start_time=start,
            end_time=end,
            elapsed_seconds=90.0,
            throughput_rows_per_sec=200 / 90.0,  # total_rows / elapsed_seconds
            file_stats=file_stats
        )
        
        # Verify consistency between aggregated data and file stats
        success_files = sum(1 for stat in file_stats if stat.status == "success")
        failed_files = sum(1 for stat in file_stats if stat.status == "failed")
        total_rows = sum(stat.inserted_rows for stat in file_stats if stat.status == "success")
        
        assert result.success_files == success_files
        assert result.failed_files == failed_files
        assert result.total_inserted_rows == total_rows