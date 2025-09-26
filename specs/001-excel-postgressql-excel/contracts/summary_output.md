# SUMMARY Output Contract

SUMMARY 行は処理完了後に 1 行 (およびログファイル) に出力される。QR-003 に基づきラベルは `SUMMARY` 固定。

## フォーマット (正規表現)
```
^SUMMARY\s+files=([0-9]+)\/(\1)\s+success=([0-9]+)\s+failed=([0-9]+)\s+rows=([0-9]+)\s+skipped_sheets=([0-9]+)\s+elapsed_sec=([0-9]+\.?[0-9]*)\s+throughput_rps=([0-9]+\.?[0-9]*)$
```

## フィールド定義
| フィールド | 説明 | 対応元 | 関連FR/QR |
|-----------|------|--------|-----------|
| files | 処理対象ファイル総数 | 検出時カウント | FR-001 |
| success | 成功ファイル数 | ProcessingResult.success_files | FR-011 |
| failed | 失敗ファイル数 | ProcessingResult.failed_files | FR-011 |
| rows | 総挿入行数 | ProcessingResult.total_inserted_rows | FR-011 |
| skipped_sheets | スキップシート総数 | ProcessingResult.skipped_sheets | FR-010, FR-011 |
| elapsed_sec | 全体経過秒 | ProcessingResult.elapsed_seconds | QR-004 |
| throughput_rps | 行/秒 | ProcessingResult.throughput_rows_per_sec | QR-005 |

## 行頭ラベル
- INFO/WARN/ERROR/SUMMARY の4種のみ (QR-003)

## Test Cases
1. 全成功: success + failed=0 + 正の throughput
2. 一部失敗: failed>0 → exit code 2 と整合
3. rows=0 (Excel 0件) → throughput_rps=0
4. スキップあり: skipped_sheets>0
5. 性能境界: elapsed_sec<=60 (代表データ) を性能テストで検証 (別テストファイル)
