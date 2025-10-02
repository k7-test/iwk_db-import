from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd
import pytest

from src.db.batch_insert import batch_insert

"""Performance test: batch size experiment harness (T013).

Tests batch_insert function with different batch sizes (500, 1000, 2000) to log
(not assert) metrics for performance tuning research. Skipped by default; 
developer opt-in via pytest -k "batch_size_experiment" or similar.

Based on research.md R-006 experiment plan for batch size tuning.
"""


class MockCursor:
    """Mock cursor for testing batch_insert without real database."""
    
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.fetched: list[tuple] = []
        self.call_count = 0
        self.total_processed_rows = 0
    
    def fetchall(self) -> list[tuple]:
        return self.fetched


def generate_synthetic_dataframe(rows: int = 10_000, cols: int = 20) -> pd.DataFrame:
    """Generate representative synthetic DataFrame for batch size experiments.
    
    Creates mixed data types similar to typical Excel import data.
    Smaller than throughput test to focus on batch size effects.
    """
    np.random.seed(42)  # Reproducible data for consistent testing
    
    data = {}
    
    # String columns (30% of columns)
    string_cols = max(1, int(cols * 0.3))
    for i in range(string_cols):
        string_data = [
            f"Item_{np.random.randint(1000, 9999)}_{chr(65 + (j % 26))}" 
            for j in range(rows)
        ]
        data[f"name_col_{i}"] = string_data
    
    # Numeric columns (50% of columns)  
    numeric_cols = max(1, int(cols * 0.5))
    for i in range(numeric_cols):
        if i % 3 == 0:
            # Integer IDs
            data[f"id_col_{i}"] = np.random.randint(1, 100000, rows)
        elif i % 3 == 1:
            # Decimal amounts
            data[f"amount_col_{i}"] = np.round(np.random.uniform(0.01, 9999.99, rows), 2)
        else:
            # Quantities
            data[f"qty_col_{i}"] = np.random.randint(1, 1000, rows)
    
    # Boolean columns (remaining)
    remaining_cols = cols - string_cols - numeric_cols
    for i in range(max(0, remaining_cols)):
        data[f"flag_col_{i}"] = np.random.choice([True, False], rows)
    
    return pd.DataFrame(data)


@pytest.fixture
def mock_execute_values_with_timing(monkeypatch):
    """Mock execute_values to simulate database operations with realistic timing."""
    import src.db.batch_insert as bi
    
    def fake_execute_values(cursor: MockCursor, sql: str, rows: list, page_size: int = 1000):
        """Simulate execute_values with timing proportional to batch size."""
        cursor.queries.append(sql)
        cursor.call_count += 1
        cursor.total_processed_rows += len(rows)
        
        # Simulate processing time based on batch size
        # Smaller batches have more overhead per row, larger batches more efficient
        base_time_per_row = 0.0001  # 0.1ms base per row
        overhead_per_batch = 0.001  # 1ms overhead per batch call
        
        # Simulate the fact that execute_values processes in chunks of page_size
        num_chunks = (len(rows) + page_size - 1) // page_size
        total_time = base_time_per_row * len(rows) + overhead_per_batch * num_chunks
        
        time.sleep(total_time)
    
    monkeypatch.setattr(bi, "execute_values", fake_execute_values)
    return fake_execute_values


@pytest.mark.skipif(
    not os.environ.get("RUN_BATCH_EXPERIMENT", False),
    reason="Batch size experiment - developer opt-in only (set RUN_BATCH_EXPERIMENT=1)"
)
def test_batch_size_experiment_comprehensive(mock_execute_values_with_timing):
    """Comprehensive batch size experiment testing 500, 1000, 2000 batch sizes.
    
    Logs metrics for each batch size to support research decisions.
    Does not assert performance requirements - focuses on comparative analysis.
    """
    # Test parameters
    test_rows = 10_000
    test_cols = 20
    batch_sizes = [500, 1000, 2000]  # As specified in research.md R-006
    
    # Generate test data once
    df = generate_synthetic_dataframe(rows=test_rows, cols=test_cols)
    columns = df.columns.tolist()
    rows_data = df.values.tolist()
    
    print("\n=== Batch Size Experiment ===")
    print(f"Dataset: {test_rows:,} rows × {test_cols} columns")
    print(f"Batch sizes to test: {batch_sizes}")
    print()
    
    results = []
    
    for batch_size in batch_sizes:
        print(f"Testing batch size: {batch_size}")
        
        # Setup fresh cursor for each test
        cursor = MockCursor()
        
        # Measure performance 
        start_time = time.perf_counter()
        
        # Call batch_insert with current batch size
        result = batch_insert(
            cursor=cursor,
            table="test_table", 
            columns=columns,
            rows=rows_data,
            returning=False,
            page_size=batch_size
        )
        
        elapsed_sec = time.perf_counter() - start_time
        
        # Calculate metrics
        throughput_rps = test_rows / elapsed_sec
        avg_rows_per_call = (
            cursor.total_processed_rows / cursor.call_count if cursor.call_count > 0 else 0
        )
        
        # Store results for comparison
        batch_result = {
            'batch_size': batch_size,
            'elapsed_sec': elapsed_sec,
            'throughput_rps': throughput_rps,
            'total_calls': cursor.call_count,
            'avg_rows_per_call': avg_rows_per_call,
            'inserted_rows': result.inserted_rows
        }
        results.append(batch_result)
        
        # Log detailed metrics
        print(f"  Elapsed time: {elapsed_sec:.4f}s")
        print(f"  Throughput: {throughput_rps:.1f} rows/sec")
        print(f"  DB calls made: {cursor.call_count}")
        print(f"  Avg rows per call: {avg_rows_per_call:.1f}")
        print(f"  Rows processed: {result.inserted_rows:,}")
        print()
    
    # Comparative analysis
    print("=== Comparative Analysis ===")
    best_throughput = max(results, key=lambda x: x['throughput_rps'])
    fastest_elapsed = min(results, key=lambda x: x['elapsed_sec'])
    fewest_calls = min(results, key=lambda x: x['total_calls'])
    
    print(f"Best throughput: {best_throughput['batch_size']} "
          f"({best_throughput['throughput_rps']:.1f} rows/sec)")
    print(f"Fastest elapsed: {fastest_elapsed['batch_size']} "
          f"({fastest_elapsed['elapsed_sec']:.4f}s)")
    print(f"Fewest DB calls: {fewest_calls['batch_size']} "
          f"({fewest_calls['total_calls']} calls)")
    
    # Performance ratios for research
    baseline_500 = next(r for r in results if r['batch_size'] == 500)
    print("\nPerformance vs batch size 500:")
    for result in results:
        if result['batch_size'] != 500:
            throughput_ratio = result['throughput_rps'] / baseline_500['throughput_rps']
            elapsed_ratio = baseline_500['elapsed_sec'] / result['elapsed_sec'] 
            print(f"  {result['batch_size']:,}: {throughput_ratio:.2f}x throughput, "
                  f"{elapsed_ratio:.2f}x faster")
    
    print("\n=== Research Recommendations ===")
    # Decision logic based on the findings
    if best_throughput['batch_size'] == 1000:
        print("✓ Current default (1000) appears optimal")
    else:
        print(f"→ Consider changing default from 1000 to {best_throughput['batch_size']}")
    
    # Network round-trip analysis
    calls_1000 = next(r for r in results if r['batch_size'] == 1000)['total_calls']
    calls_2000 = next(r for r in results if r['batch_size'] == 2000)['total_calls']
    if calls_2000 < calls_1000:
        print(f"→ Batch size 2000 reduces DB round trips: {calls_1000} → {calls_2000}")
    
    # All validations pass - this test logs rather than asserts
    assert len(results) == len(batch_sizes), "Should test all batch sizes"
    print("\n✓ Batch size experiment completed successfully")


@pytest.mark.skipif(
    not os.environ.get("RUN_BATCH_EXPERIMENT", False),
    reason="Batch size experiment - developer opt-in only (set RUN_BATCH_EXPERIMENT=1)"
)
def test_batch_size_experiment_memory_focused(mock_execute_values_with_timing):
    """Memory-focused batch size experiment with smaller dataset.
    
    Tests memory efficiency patterns for different batch sizes
    using a smaller dataset to focus on per-batch overhead.
    """
    # Smaller dataset to highlight batch overhead effects
    test_rows = 2_000
    test_cols = 10
    batch_sizes = [100, 500, 1000, 2000]  # Include smaller size for overhead analysis
    
    df = generate_synthetic_dataframe(rows=test_rows, cols=test_cols)
    columns = df.columns.tolist()
    rows_data = df.values.tolist()
    
    print("\n=== Memory-Focused Batch Size Experiment ===")
    print(f"Dataset: {test_rows:,} rows × {test_cols} columns (smaller for overhead analysis)")
    print()
    
    for batch_size in batch_sizes:
        cursor = MockCursor()
        
        start_time = time.perf_counter()
        batch_insert(
            cursor=cursor,
            table="memory_test_table", 
            columns=columns,
            rows=rows_data,
            returning=False,
            page_size=batch_size
        )
        elapsed_sec = time.perf_counter() - start_time
        
        # Focus on overhead metrics
        expected_batches = (test_rows + batch_size - 1) // batch_size
        overhead_per_batch = elapsed_sec / expected_batches if expected_batches > 0 else 0
        
        print(f"Batch size {batch_size:,}:")
        print(f"  Expected batches: {expected_batches}")
        print(f"  Actual DB calls: {cursor.call_count}")
        print(f"  Total time: {elapsed_sec:.4f}s")
        print(f"  Overhead per batch: {overhead_per_batch*1000:.2f}ms")
        print(f"  Rows per second: {test_rows/elapsed_sec:.1f}")
        print()
    
    print("✓ Memory-focused experiment completed")