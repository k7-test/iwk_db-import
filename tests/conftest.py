# Shared pytest fixtures (Phase 1 scaffolding)
from __future__ import annotations
import os
import tempfile
from pathlib import Path
import json
import pytest

@pytest.fixture()
def temp_workdir(monkeypatch) -> Path:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "config").mkdir()
        (p / "data").mkdir()
        (p / "logs").mkdir()
        monkeypatch.chdir(p)
        yield p

@pytest.fixture()
def sample_config_yaml() -> str:
    return """source_directory: ./data
sheet_mappings:
  Customers:
    table: customers
    sequence_columns: [id]
  Orders:
    table: orders
    sequence_columns: [id]
    fk_propagation_columns: [customer_id]
sequences:
  id: customers_id_seq
fk_propagations:
  customer_id: id
timezone: UTC
database:
  host: localhost
  port: 5432
  user: appuser
  password: secret
  database: appdb
"""

@pytest.fixture()
def write_config(temp_workdir: Path, sample_config_yaml: str) -> Path:
    cfg = temp_workdir / "config" / "import.yml"
    cfg.write_text(sample_config_yaml, encoding="utf-8")
    return cfg

@pytest.fixture()
def dummy_excel_files(temp_workdir: Path) -> list[Path]:
    # Placeholder: real creation will use pandas later
    # For now we just create empty placeholder files to test scanning logic.
    files = []
    for name in ["customers.xlsx", "orders.xlsx"]:
        f = temp_workdir / "data" / name
        f.write_bytes(b"")
        files.append(f)
    return files

@pytest.fixture()
def capture_logs(monkeypatch, tmp_path: Path):
    logs = []
    def fake_log(msg: str):
        logs.append(msg)
    # monkeypatch.setattr("src.logging.core.log", fake_log)  # will patch when module exists
    return logs
