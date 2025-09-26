# Contracts Overview

このディレクトリは CLI ツールの外部可観測な契約 (Contracts) を仕様化し、Phase 1 で failing テスト生成の根拠となる。

## 契約カテゴリ
| カテゴリ | 説明 | 対応ファイル |
|----------|------|--------------|
| CLI Exit Codes | 終了コードの意味と条件 | `cli_exit_codes.md` |
| Summary Output | SUMMARY行フォーマット/必須フィールド | `summary_output.md` |
| Error Log JSON | エラーログ1行 JSON スキーマ | `error_log_schema.json` |
| Config Schema | `config/import.yml` 必須/任意項目 | `config_schema.yaml` |

## テスト指針
- 契約ファイル変更時は対応する contract test を更新し snapshot/スキーマ差分を検出。
- 破壊的変更はメジャーバージョン (将来 versioning 導入時) のみ許容。

## カバレッジ対象 FR/QR
- FR-011, FR-018, FR-020, FR-026, FR-030
- QR-003, QR-007, QR-009

---
