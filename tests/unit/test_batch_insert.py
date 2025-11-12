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


def test_batch_insert_with_blob_columns(tmp_path):
    """Test blob columns - files are read and binary data is passed."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.pdf"
    file1.write_bytes(b"content1")
    file2.write_bytes(b"content2")
    
    cur = DummyCursor()
    res = batch_insert(
        cur,
        table="files",
        columns=["id", "name", "content"],
        rows=[[1, "file1.txt", "file1.txt"], [2, "file2.pdf", "file2.pdf"]],
        blob_columns={"content"},
        source_directory=str(tmp_path),
    )
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 2
    # No template is used - binary data is passed directly
    assert cur.template is None


def test_batch_insert_with_multiple_blob_columns(tmp_path):
    """Test multiple blob columns."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_bytes(b"content1")
    file2.write_bytes(b"content2")
    
    cur = DummyCursor()
    res = batch_insert(
        cur,
        table="files",
        columns=["id", "file1", "file2"],
        rows=[[1, "file1.txt", "file2.txt"]],
        blob_columns={"file1", "file2"},
        source_directory=str(tmp_path),
    )
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 1
    # No template - binary data is passed directly
    assert cur.template is None


def test_batch_insert_with_blob_and_returning(tmp_path):
    """Test blob columns with RETURNING clause."""
    # Create test file
    file1 = tmp_path / "file.txt"
    file1.write_bytes(b"content")
    
    cur = DummyCursor()
    res = batch_insert(
        cur,
        table="files",
        columns=["id", "content"],
        rows=[[1, "file.txt"]],
        returning=True,
        blob_columns={"content"},
        source_directory=str(tmp_path),
    )
    assert res.returned_values == [(1,), (2,)]
    assert "RETURNING *" in cur.queries[0]
    # No template - binary data is passed directly
    assert cur.template is None


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


def test_batch_insert_blob_file_not_found(tmp_path):
    """Test blob columns with missing file raises error."""
    cur = DummyCursor()
    with pytest.raises(BatchInsertError, match="Failed to read blob file"):
        batch_insert(
            cur,
            table="files",
            columns=["id", "content"],
            rows=[[1, "nonexistent.txt"]],
            blob_columns={"content"},
            source_directory=str(tmp_path),
        )


def test_batch_insert_blob_without_source_directory(tmp_path):
    """Test blob columns without source_directory does not read files."""
    cur = DummyCursor()
    # Without source_directory, blob columns are not processed
    res = batch_insert(
        cur,
        table="files",
        columns=["id", "content"],
        rows=[[1, "file.txt"]],
        blob_columns={"content"},
        source_directory=None,
    )
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 1


def test_batch_insert_blob_with_null_value(tmp_path):
    """Test blob columns with None value."""
    file1 = tmp_path / "file1.txt"
    file1.write_bytes(b"content1")
    
    cur = DummyCursor()
    res = batch_insert(
        cur,
        table="files",
        columns=["id", "content"],
        rows=[[1, "file1.txt"], [2, None]],
        blob_columns={"content"},
        source_directory=str(tmp_path),
    )
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 2


def test_batch_insert_blob_with_mixed_columns(tmp_path):
    """Test blob columns mixed with regular columns."""
    file1 = tmp_path / "file1.txt"
    file1.write_bytes(b"binary_content")
    
    cur = DummyCursor()
    res = batch_insert(
        cur,
        table="documents",
        columns=["id", "title", "content", "author"],
        rows=[[1, "Doc1", "file1.txt", "Alice"]],
        blob_columns={"content"},
        source_directory=str(tmp_path),
    )
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 1


def test_batch_insert_blob_columns_not_in_insert_columns(tmp_path):
    """Test blob columns specified but not in columns list."""
    cur = DummyCursor()
    # blob_columns specifies "content" but columns doesn't include it
    res = batch_insert(
        cur,
        table="documents",
        columns=["id", "title"],
        rows=[[1, "Doc1"]],
        blob_columns={"content"},  # This column is not in columns list
        source_directory=str(tmp_path),
    )
    assert isinstance(res, InsertResult)
    assert res.inserted_rows == 1
    assert cur.template is None
    assert "VALUES %s" in cur.queries[0]
