from __future__ import annotations
import json
from pathlib import Path
from src.logging.error_log import ErrorRecord, ErrorLogBuffer


def test_error_record_creation_and_json_line():
    rec = ErrorRecord.create(
        file="file.xlsx",
        sheet="Sheet1",
        row=10,
        error_type="CONSTRAINT_VIOLATION",
        db_message="duplicate key"
    )
    line = rec.to_json_line()
    data = json.loads(line)
    assert data["file"] == "file.xlsx"
    assert data["sheet"] == "Sheet1"
    assert data["row"] == 10
    assert data["error_type"] == "CONSTRAINT_VIOLATION"
    assert "timestamp" in data and data["timestamp"].endswith("Z")
    assert set(data.keys()) == {"timestamp", "file", "sheet", "row", "error_type", "db_message"}


def test_error_log_buffer_flush(temp_workdir: Path):
    buf = ErrorLogBuffer()
    buf.append(ErrorRecord.create("f1.xlsx", "S", 1, "CONSTRAINT_VIOLATION", "dup"))
    buf.append(ErrorRecord.create("f1.xlsx", "S", 2, "MISSING_COLUMN", "col missing"))
    path = buf.flush()
    assert path.exists()
    # ファイル内容検証
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    for raw in lines:
        obj = json.loads(raw)
        assert set(obj.keys()) == {"timestamp", "file", "sheet", "row", "error_type", "db_message"}
    # flush 後バッファクリア
    assert len(buf) == 0


def test_error_log_buffer_multiple_flushes(temp_workdir: Path):
    buf = ErrorLogBuffer()
    first = ErrorRecord.create("f.xlsx", "S", 1, "CONSTRAINT_VIOLATION", "dup")
    buf.append(first)
    path = buf.flush()
    size1 = path.stat().st_size
    # 再追加して再flush
    buf.append(ErrorRecord.create("f.xlsx", "S", 2, "CONSTRAINT_VIOLATION", "dup2"))
    path2 = buf.flush()
    assert path == path2
    size2 = path2.stat().st_size
    assert size2 > size1
