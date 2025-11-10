from __future__ import annotations

import pytest

from src.db.batch_insert import BatchInsertError, InsertResult, batch_insert


class DummyCursor:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.fetched: list[tuple] = [(1,), (2,)]
        self.template: str | None = None
    def fetchall(self):
        return self.fetched

# We monkeypatch execute_values symbol inside module to avoid needing
# psycopg2 real dependency for logic test

@pytest.fixture(autouse=True)
def patch_execute_values(monkeypatch):
    import src.db.batch_insert as bi
    def fake_execute_values(cursor, sql, rows, page_size=1000, template=None):  # noqa: D401
        cursor.queries.append(sql)
        if template:
            cursor.template = template  # Store template for assertion in tests
        # simulate doing nothing else
    monkeypatch.setattr(bi, "execute_values", fake_execute_values)
    return fake_execute_values


def test_batch_insert_basic():
    cur = DummyCursor()
    res = batch_insert(
        cur, table="customers", columns=["id", "name"], rows=[[1, "Alice"], [2, "Bob"]]
    )
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 2
    assert res.returned_values is None


def test_batch_insert_returning():
    cur = DummyCursor()
    res = batch_insert(cur, table="customers", columns=["id"], rows=[[1], [2]], returning=True)
    assert res.returned_values == [(1,), (2,)]


def test_batch_insert_empty_rows():
    cur = DummyCursor()
    res = batch_insert(cur, table="customers", columns=["id"], rows=[], returning=False)
    assert res.inserted_rows == 0


def test_batch_insert_missing_driver(monkeypatch):
    import src.db.batch_insert as bi
    # Force execute_values None path
    monkeypatch.setattr(bi, "execute_values", None)
    with pytest.raises(BatchInsertError):
        batch_insert(DummyCursor(), table="t", columns=["c"], rows=[[1]])


def test_batch_insert_with_metrics_callback():
    """Test T023: metrics callback functionality."""
    cur = DummyCursor()
    captured_metrics = []
    
    def metrics_callback(metrics):
        captured_metrics.append(metrics)
    
    res = batch_insert(
        cur, 
        table="customers", 
        columns=["id", "name"], 
        rows=[[1, "Alice"], [2, "Bob"]], 
        metrics_callback=metrics_callback
    )
    
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 2
    assert len(captured_metrics) == 1
    
    metrics = captured_metrics[0]
    assert metrics.batch_size == 2
    assert metrics.elapsed_seconds >= 0  # Should be very small but >= 0
    assert metrics.end_time >= metrics.start_time
    assert metrics.elapsed_seconds == metrics.end_time - metrics.start_time


def test_batch_insert_without_metrics_callback():
    """Test T023: ensure backward compatibility when no callback provided."""
    cur = DummyCursor()
    res = batch_insert(cur, table="customers", columns=["id"], rows=[[1], [2]])
    
    # Should work exactly as before
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 2
    assert res.returned_values is None


def test_batch_insert_empty_rows_with_metrics():
    """Test T023: metrics callback with empty rows."""
    cur = DummyCursor()
    captured_metrics = []
    
    def metrics_callback(metrics):
        captured_metrics.append(metrics)
    
    res = batch_insert(
        cur, 
        table="customers", 
        columns=["id"], 
        rows=[], 
        metrics_callback=metrics_callback
    )
    
    assert res.inserted_rows == 0
    # No metrics should be captured for empty rows (no execute_values call)
    assert len(captured_metrics) == 0


def test_batch_insert_with_blob_columns():
    """Test blob columns with pg_read_binary_file."""
    cur = DummyCursor()
    res = batch_insert(
        cur,
        table="files",
        columns=["id", "name", "content"],
        rows=[[1, "file1.txt", "/path/to/file1.txt"], [2, "file2.pdf", "/path/to/file2.pdf"]],
        blob_columns={"content"},
    )
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 2
    # Verify template was set with pg_read_binary_file for content column
    assert cur.template == "(%s,%s,pg_read_binary_file(%s))"
    # Verify SQL doesn't include VALUES %s (uses template instead)
    assert "VALUES %s" not in cur.queries[0]


def test_batch_insert_with_multiple_blob_columns():
    """Test multiple blob columns."""
    cur = DummyCursor()
    res = batch_insert(
        cur,
        table="files",
        columns=["id", "file1", "file2"],
        rows=[[1, "/path/to/file1.txt", "/path/to/file2.txt"]],
        blob_columns={"file1", "file2"},
    )
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 1
    # Both file columns should use pg_read_binary_file
    assert cur.template == "(%s,pg_read_binary_file(%s),pg_read_binary_file(%s))"


def test_batch_insert_with_blob_and_returning():
    """Test blob columns with RETURNING clause."""
    cur = DummyCursor()
    res = batch_insert(
        cur,
        table="files",
        columns=["id", "content"],
        rows=[[1, "/path/to/file.txt"]],
        returning=True,
        blob_columns={"content"},
    )
    assert res.returned_values == [(1,), (2,)]
    assert "RETURNING *" in cur.queries[0]
    assert cur.template == "(%s,pg_read_binary_file(%s))"


def test_batch_insert_without_blob_columns():
    """Test normal insert without blob columns still works."""
    cur = DummyCursor()
    res = batch_insert(
        cur,
        table="customers",
        columns=["id", "name"],
        rows=[[1, "Alice"]],
        blob_columns=None,
    )
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 1
    # Should use normal VALUES %s format
    assert cur.template is None
    assert "VALUES %s" in cur.queries[0]
