from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.models.processing_result import (
    BatchStatsAccumulator,
    FileStat,
    MetricsSnapshot,
    ProcessingResult,
)

"""Unit tests for processing result models (T019, T029).

Tests the dataclass models defined in src/models/processing_result.py to ensure
they correctly implement the data-model.md specifications.
Includes tests for batch timing statistics accumulation (T029).
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
        # T029: Test batch timing defaults
        assert stat.total_batches == 0
        assert stat.avg_batch_seconds == 0.0
        assert stat.p95_batch_seconds == 0.0
    
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


class TestFileStatWithBatchTimings:
    """Test FileStat with batch timing statistics (T029)."""
    
    def test_file_stat_with_batch_stats(self):
        """Test FileStat creation with batch timing statistics."""
        stat = FileStat(
            file_name="test.xlsx",
            status="success",
            inserted_rows=1000,
            elapsed_seconds=30.0,
            total_batches=10,
            avg_batch_seconds=2.5,
            p95_batch_seconds=3.2
        )
        
        assert stat.total_batches == 10
        assert stat.avg_batch_seconds == 2.5
        assert stat.p95_batch_seconds == 3.2


class TestBatchStatsAccumulator:
    """Test BatchStatsAccumulator helper class (T029)."""
    
    def test_empty_accumulator(self):
        """Test accumulator with no batch times."""
        accumulator = BatchStatsAccumulator()
        total, avg, p95 = accumulator.get_stats()
        
        assert total == 0
        assert avg == 0.0
        assert p95 == 0.0
    
    def test_single_batch(self):
        """Test accumulator with single batch time."""
        accumulator = BatchStatsAccumulator()
        accumulator.add_batch_time(2.5)
        
        total, avg, p95 = accumulator.get_stats()
        
        assert total == 1
        assert avg == 2.5
        assert p95 == 2.5  # For single value, p95 equals the value
    
    def test_multiple_batches(self):
        """Test accumulator with multiple batch times."""
        accumulator = BatchStatsAccumulator()
        batch_times = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 10.0]  # 10 values
        
        for time in batch_times:
            accumulator.add_batch_time(time)
        
        total, avg, p95 = accumulator.get_stats()
        
        assert total == 10
        assert avg == 3.7  # (1.0 + 1.5 + ... + 10.0) / 10
        # p95 should be close to 10.0 (95th percentile of these values)
        assert p95 >= 5.0  # Should be in upper range
    
    def test_accumulator_consistency(self):
        """Test that adding times one by one gives consistent results."""
        accumulator1 = BatchStatsAccumulator()
        accumulator2 = BatchStatsAccumulator()
        
        times = [1.2, 2.8, 1.9, 3.1, 2.5]
        
        # Add all at once vs one by one
        for time in times:
            accumulator1.add_batch_time(time)
        
        for time in times:
            accumulator2.add_batch_time(time)
        
        stats1 = accumulator1.get_stats()
        stats2 = accumulator2.get_stats()
        
        assert stats1 == stats2


class TestBatchTimingIntegration:
    """Test integration between batch_insert timing and FileStat accumulation (T029)."""
    
    def test_batch_metrics_callback_integration(self):
        """Test that BatchStatsAccumulator can be used with batch_insert metrics callback."""
        from src.db.batch_insert import BatchMetrics
        
        # Simulate the pattern that would be used in production
        accumulator = BatchStatsAccumulator()
        
        def metrics_callback(metrics: BatchMetrics) -> None:
            """Callback that would be passed to batch_insert."""
            accumulator.add_batch_time(metrics.elapsed_seconds)
        
        # Simulate several batch insert operations with different timing
        mock_batch_metrics = [
            BatchMetrics(batch_size=1000, elapsed_seconds=1.2, start_time=0.0, end_time=1.2),
            BatchMetrics(batch_size=1000, elapsed_seconds=1.8, start_time=1.2, end_time=3.0),
            BatchMetrics(batch_size=500, elapsed_seconds=0.9, start_time=3.0, end_time=3.9),
        ]
        
        # Process each batch through callback
        for metrics in mock_batch_metrics:
            metrics_callback(metrics)
        
        # Get accumulated statistics
        total_batches, avg_batch_seconds, p95_batch_seconds = accumulator.get_stats()
        
        assert total_batches == 3
        assert avg_batch_seconds == (1.2 + 1.8 + 0.9) / 3  # 1.3
        assert p95_batch_seconds >= 0.9  # Should be >= minimum value
        
        # Now create a FileStat with these accumulated statistics
        file_stat = FileStat(
            file_name="test_file.xlsx",
            status="success",
            inserted_rows=2500,  # 1000 + 1000 + 500
            elapsed_seconds=3.9,  # Total file processing time
            total_batches=total_batches,
            avg_batch_seconds=avg_batch_seconds,
            p95_batch_seconds=p95_batch_seconds
        )
        
        assert file_stat.total_batches == 3
        assert file_stat.avg_batch_seconds == 1.3
        assert file_stat.inserted_rows == 2500