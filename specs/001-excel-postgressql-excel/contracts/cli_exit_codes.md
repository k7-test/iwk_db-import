# CLI Exit Codes Contract

| Code | Meaning | Conditions (All must hold) | Related FR |
|------|---------|----------------------------|------------|
| 0 | 全ファイル成功 | (a) 全ての対象Excelファイルがトランザクション成功 (b) 失敗/ロールバックなし (c) 致命的初期化エラーなし | FR-002, FR-009, FR-011, FR-020 |
| 2 | 一部失敗 | (a) 少なくとも1ファイルがロールバック (b) 初期化フェーズは成功 (c) その他ファイルは継続実行 | FR-002, FR-009, FR-020 |
| 1 | 起動時致命的エラー | (a) 設定ファイル欠如/不正 (b) ログディレクトリ作成不可 (c) DB接続確立不能 (d) Config schema violation | FR-014, FR-015, FR-017, FR-020, FR-026, FR-027 |

## Notes
- 処理途中の OS シグナル (SIGINT) は将来拡張: 現段階では即時終了 → exit code 2 (部分失敗扱い) を推奨。
- 致命的エラー検出タイミング: main() 初期化ブロック内で例外捕捉後 exit(1)。

## Test Cases (Failing First)
1. 正常系: モックDB + 2ファイル成功 → exit 0
2. 一部失敗: 1ファイルで制約違反 → exit 2
3. 設定欠如: config/import.yml 無 → exit 1
4. DB接続失敗: 環境変数不備/無効ホスト → exit 1
