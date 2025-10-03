from __future__ import annotations

import re

"""SUMMARY 行フォーマット契約テスト (contracts/summary_output.md)
まだ CLI 未実装なので正規表現パターンのみ検証。
"""

SUMMARY_PATTERN = re.compile(
    r"^SUMMARY\s+files=([0-9]+)/(\1)\s+success=([0-9]+)\s+failed=([0-9]+)\s+"
    r"rows=([0-9]+)\s+skipped_sheets=([0-9]+)\s+elapsed_sec=([0-9]+\.?[0-9]*)\s+"
    r"throughput_rps=([0-9]+\.?[0-9]*)$"
)

def test_summary_pattern_example_line():
    line = (
        "SUMMARY files=1/1 success=1 failed=0 rows=4 skipped_sheets=0 "
        "elapsed_sec=0.84 throughput_rps=4761.9"
    )
    m = SUMMARY_PATTERN.match(line)
    assert m, "SUMMARY line should match contract regex"
