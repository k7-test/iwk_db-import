from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.models.error_record import ErrorRecord

"""Error log generation & buffering module (Phase 1 scaffold).

FR-018 / FR-030 / QR-009 対応:
- JSON Lines 固定スキーマ (追加キー禁止)
- 起動ごとに `logs/errors-YYYYMMDD-HHMMSS.log` (UTC) を生成 (必要時)
- バッファリングしてファイル単位/flush タイミングで書き出し

現段階: 最低限の API 定義とシリアライズ。I/O, 実際の flush タイミング、例外処理は後続実装で拡張。
"""

__all__ = [
    "ErrorRecord",
    "ErrorLogBuffer",
]

LOGS_DIR = Path("./logs")
TIMESTAMP_FMT = "%Y%m%d-%H%M%S"



class ErrorLogBuffer:
    """In-memory buffer for error records. Flush writes JSON Lines.

    初版では:
    - flush() 呼び出し時にファイル (なければ生成) へ一括追記
    - ファイルパスは初回アクセスで決定
    - スレッド安全性不要 (シリアル実行)
    """
    def __init__(self) -> None:
        self._records: list[ErrorRecord] = []
        self._file_path: Path | None = None

    @property
    def file_path(self) -> Path:
        if self._file_path is None:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime(TIMESTAMP_FMT)
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
