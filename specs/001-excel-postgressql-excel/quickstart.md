# Quickstart: Excel -> PostgreSQL バルク登録 CLI ツール

**Branch**: 001-excel-postgressql-excel  
**Spec**: `specs/001-excel-postgressql-excel/spec.md`

このドキュメントは初回利用者が 5 分でツールを試せることを目的とした最小実行ガイドです (FR-014, FR-011, FR-020, FR-030 / QR-003 対応)。

---
## 1. 前提
- Python 3.11+
- PostgreSQL 接続先 (ローカル or コンテナ) が起動済み
- 環境変数で DB 接続情報設定 (例):
  - `PGHOST=localhost`
  - `PGPORT=5432`
  - `PGUSER=appuser`
  - `PGPASSWORD=secret`
  - `PGDATABASE=appdb`

(環境変数未設定の場合 `config/import.yml` の `database:` セクション値をフォールバック使用; FR-027)

---
## 2. ディレクトリ構成 (サンプル)
```
project/
  config/
    import.yml
  data/
    customers.xlsx
  logs/                # 実行時に自動生成 (FR-017)
```

---
## 3. 設定ファイル例 `config/import.yml`
```yaml
source_directory: ./data
sheet_mappings:
  Customers:
    table: customers
    sequence_columns: [id]
    fk_propagation_columns: []
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
```

---
## 4. Excelファイル例 `data/customers.xlsx`
シート: `Customers` / `Orders`

`Customers` シート:
| (1行目タイトル例) | Import Tool | Demo |
|------------------|------------|------|
| id | name | email |
| 1  | Alice | alice@example.com |
| 2  | Bob   | bob@example.com   |

`Orders` シート:
| (1行目タイトル例) | Order Sheet | Sample |
|------------------|-------------|--------|
| id | customer_id | amount |
| 1  | 1 | 1200 |
| 2  | 1 | 800  |

ツールは2行目をヘッダ (FR-004)。上記例では 2 行目がヘッダ行として扱われ、3行目以降がデータ。実利用時は 1 行目をタイトル行 (自由) として残し、2 行目に実 DB 列名を配置する形式を推奨。

---
## 5. 実行 (暫定例)
(実際のエントリポイント名は実装後に更新) 例: `python -m src.cli.import_excel`

出力イメージ:
```
INFO  scanning directory ./data (found=1)
INFO  processing file=customers.xlsx (1/1)
INFO  sheet=Customers rows=2 inserting...
INFO  sheet=Orders rows=2 inserting...
SUMMARY files=1/1 success=1 failed=0 rows=4 skipped_sheets=0 elapsed_sec=0.84 throughput_rps=4761.9
```

`logs/errors-YYYYMMDD-HHMMSS.log` が生成 (エラーなしなら空/未作成の場合あり) (FR-030)。

---
## 6. エラーログ例
挿入失敗時の JSON Lines 内容例:
```json
{"timestamp":"2025-09-26T10:12:33Z","file":"customers.xlsx","sheet":"Orders","row":2,"error_type":"CONSTRAINT_VIOLATION","db_message":"duplicate key value violates unique constraint 'orders_pkey'"}
```

---
## 7. 終了コード
| Code | 説明 |
|------|------|
| 0 | 全ファイル成功 |
| 2 | 一部失敗 (少なくとも1ファイルロールバック) |
| 1 | 起動時致命的エラー (設定不正, DB接続不可 など) |

---
## 8. 性能確認 (スモーク)
小規模データで throughput_rps が >800 を大幅に超えることを目安に初期性能を確認。大量データ検証は別途性能テストで実施。

---
## 9. トラブルシュート
| 症状 | 原因候補 | 対処 |
|------|----------|------|
| exit code 1 | config/import.yml 不備 | スキーマ確認 (contracts/config_schema.yaml) |
| exit code 2 | データ制約違反 | エラーログ JSON Lines 確認 |
| rows=0 | シートヘッダ不一致/マッピング不足 | sheet_mappings と Excel 2 行目見直し |
| skipped_sheets>0 | 設定未定義シート | 必要なら sheet_mappings に追加 |
| throughput 低い | バッチサイズ小 / ネット遅延 | 後続チューニング (R-006) |

---
## 10. 次に読む
- `contracts/summary_output.md` (出力フォーマット)
- `contracts/error_log_schema.json` (エラーログスキーマ)
- `data-model.md` (内部ドメインモデル)
- `research.md` (性能/設計判断根拠)

---
*Quickstart 完了*
