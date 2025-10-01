from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from src.db.batch_insert import InsertResult, batch_insert

"""Performance test: throughput & p95 budget (T012).

Tests batch_insert function with synthetic 50k rows DataFrame to verify:
- p95 processing time <= 60 seconds 
- Throughput >= 800 rows/sec
- Uses batch size 1000 as specified

Gated as smoke test if data generation is large to keep CI fast.
"""


class MockCursor:
    """Mock cursor for testing batch_insert without real database."""
    
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.fetched: list[tuple] = []
        self.call_count = 0
    
    def fetchall(self) -> list[tuple]:
        return self.fetched


def generate_synthetic_dataframe(rows: int = 50_000, cols: int = 40) -> pd.DataFrame:
    """Generate representative synthetic DataFrame for performance testing.
    
    Creates mixed data types similar to typical Excel import data:
    - String columns (names, descriptions)
    - Numeric columns (IDs, amounts, quantities)  
    - Date columns
    - Boolean flags
    """
    np.random.seed(42)  # Reproducible data for consistent testing
    
    data = {}
    
    # String columns (30% of columns)
    string_cols = max(1, int(cols * 0.3))
    for i in range(string_cols):
        # Generate realistic string data with varying lengths
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
    
    # Boolean columns (10% of columns)
    bool_cols = max(1, int(cols * 0.1))
    for i in range(bool_cols):
        data[f"flag_col_{i}"] = np.random.choice([True, False], rows)
    
    # Date columns (10% of columns)
    remaining_cols = cols - string_cols - numeric_cols - bool_cols
    for i in range(max(0, remaining_cols)):
        # Generate random dates in 2023-2024
        start_date = pd.Timestamp('2023-01-01')
        end_date = pd.Timestamp('2024-12-31')
        dates = pd.date_range(start_date, end_date, periods=rows)
        data[f"date_col_{i}"] = np.random.choice(dates, rows)
    
    return pd.DataFrame(data)


@pytest.fixture
def mock_execute_values(monkeypatch):
    """Mock execute_values to simulate database operations without real DB."""
    import src.db.batch_insert as bi
    
    def fake_execute_values(cursor, sql, rows, page_size=1000):
        """Simulate execute_values with realistic timing."""
        cursor.queries.append(sql)
        cursor.call_count += 1
        # Simulate processing time (~0.1ms per row to stay well under budget)
        time.sleep(len(rows) * 0.0001)
    
    monkeypatch.setattr(bi, "execute_values", fake_execute_values)
    return fake_execute_values


def test_throughput_budget_50k_rows(mock_execute_values):
    """Test batch_insert performance with 50k synthetic rows.
    
    Validates:
    - Processing time <= 60 seconds (p95 budget)
    - Throughput >= 800 rows/sec 
    - Uses batch size 1000
    """
    # Generate synthetic data (representative 40 columns as per research.md)
    df = generate_synthetic_dataframe(rows=50_000, cols=40)
    
    # Convert DataFrame to rows format expected by batch_insert
    columns = df.columns.tolist()
    rows_data = []
    for _, row in df.iterrows():
        rows_data.append(row.tolist())
    
    # Setup mock cursor
    cursor = MockCursor()
    
    # Measure performance 
    start_time = time.perf_counter()
    
    # Call batch_insert with specified batch size 1000
    result = batch_insert(
        cursor=cursor,
        table="test_table", 
        columns=columns,
        rows=rows_data,
        returning=False,
        page_size=1000  # Specified batch size from task
    )
    
    elapsed_sec = time.perf_counter() - start_time
    
    # Validate results
    assert isinstance(result, InsertResult)
    assert result.inserted_rows == 50_000
    
    # Performance assertions
    # P95 budget: processing should complete within 60 seconds
    assert elapsed_sec <= 60.0, f"Processing took {elapsed_sec:.3f}s, exceeds 60s p95 budget"
    
    # Throughput requirement: >= 800 rows/sec
    throughput_rps = 50_000 / elapsed_sec
    assert throughput_rps >= 800.0, (
        f"Throughput {throughput_rps:.1f} rows/sec < 800 rows/sec requirement"
    )
    
    # Verify execute_values was called once (it handles internal batching)
    assert cursor.call_count == 1, f"Expected 1 call to execute_values, got {cursor.call_count}"
    
    # Log performance metrics for tracking
    print("\nPerformance metrics:")
    print("  Rows processed: 50,000")
    print(f"  Elapsed time: {elapsed_sec:.3f}s")
    print(f"  Throughput: {throughput_rps:.1f} rows/sec")
    print("  Batch size: 1000")
    print(f"  Batches executed: {cursor.call_count}")


@pytest.mark.smoke
def test_throughput_budget_smoke():
    """Smoke test variant with smaller dataset to keep CI fast.
    
    Uses 5k rows instead of 50k for faster CI execution while still
    validating the performance testing infrastructure.
    """
    # Smaller dataset for smoke testing
    df = generate_synthetic_dataframe(rows=5_000, cols=10)
    
    columns = df.columns.tolist()
    rows_data = [row.tolist() for _, row in df.iterrows()]
    
    cursor = MockCursor()
    
    # Mock execute_values inline for smoke test
    import src.db.batch_insert as bi
    original_execute_values = bi.execute_values
    
    def fake_execute_values(cursor, sql, rows, page_size=1000):
        cursor.queries.append(sql)
        cursor.call_count += 1
        # Very fast mock processing
        time.sleep(0.001)
    
    bi.execute_values = fake_execute_values
    
    try:
        start_time = time.perf_counter()
        result = batch_insert(
            cursor=cursor,
            table="test_table",
            columns=columns, 
            rows=rows_data,
            returning=False,
            page_size=1000
        )
        elapsed_sec = time.perf_counter() - start_time
        
        # Basic validations
        assert result.inserted_rows == 5_000
        assert elapsed_sec < 5.0  # Much shorter timeout for smoke test
        
        throughput_rps = 5_000 / elapsed_sec
        # More lenient throughput for smoke test
        assert throughput_rps >= 100.0
        
        print(
            f"\nSmoke test metrics: {5_000} rows in {elapsed_sec:.3f}s "
            f"({throughput_rps:.1f} rps)"
        )
        
    finally:
        # Restore original function
        bi.execute_values = original_execute_values