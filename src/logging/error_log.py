from __future__ import annotations
"""Error log generation & buffering module (Phase 1 scaffold).

FR-018 / FR-030 / QR-009 対応:
- JSON Lines 固定スキーマ (追加キー禁止)
- 起動ごとに `logs/errors-YYYYMMDD-HHMMSS.log` (UTC) を生成 (必要時)
- バッファリングしてファイル単位/flush タイミングで書き出し

現段階: 最低限の API 定義とシリアライズ。I/O, 実際の flush タイミング、例外処理は後続実装で拡張。
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List
import json

__all__ = [
    "ErrorRecord",
    "ErrorLogBuffer",
]

LOGS_DIR = Path("./logs")
TIMESTAMP_FMT = "%Y%m%d-%H%M%S"

@dataclass(frozen=True)
class ErrorRecord:
    timestamp: str  # ISO8601 UTC
    file: str
    sheet: str
    row: int  # 行番号。不明な場合 -1 許容
    error_type: str  # UPPER_SNAKE
    db_message: str

    @staticmethod
    def create(file: str, sheet: str, row: int, error_type: str, db_message: str) -> "ErrorRecord":
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return ErrorRecord(
            timestamp=ts,
            file=file,
            sheet=sheet,
            row=row,
            error_type=error_type,
            db_message=db_message,
        )

    def to_json_line(self) -> str:
        # 追加キー阻止: dataclass -> dict して json.dumps
        return json.dumps(asdict(self), ensure_ascii=False)

class ErrorLogBuffer:
    """In-memory buffer for error records. Flush writes JSON Lines.

    初版では:
    - flush() 呼び出し時にファイル (なければ生成) へ一括追記
    - ファイルパスは初回アクセスで決定
    - スレッド安全性不要 (シリアル実行)
    """
    def __init__(self) -> None:
        self._records: List[ErrorRecord] = []
        self._file_path: Path | None = None

    @property
    def file_path(self) -> Path:
        if self._file_path is None:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime(TIMESTAMP_FMT)
            self._file_path = LOGS_DIR / f"errors-{stamp}.log"
        return self._file_path

    def append(self, record: ErrorRecord) -> None:
        self._records.append(record)

    def __len__(self) -> int:  # pragma: no cover (trivial)
        return len(self._records)

    def flush(self) -> Path:
        if not self._records:
            return self.file_path  # 空でもファイルパス確定のみ (要件次第で作成抑止可)
        fp = self.file_path
        with fp.open("a", encoding="utf-8") as f:
            for r in self._records:
                f.write(r.to_json_line() + "\n")
        self._records.clear()
        return fp
