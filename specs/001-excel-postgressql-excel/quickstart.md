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
## 5. 実行
プロジェクトディレクトリから以下のコマンドを実行:

```bash
python -m src.cli
```

### 5.1 成功時の出力例:
```
INFO  Processing files from: ./data
INFO  processing file=customers.xlsx (1/1)
INFO  sheet=Customers rows=2 inserting...
INFO  sheet=Orders rows=2 inserting...
SUMMARY files=1/1 success=1 failed=0 rows=4 skipped_sheets=0 elapsed_sec=0.84 throughput_rps=4761.9
```

### 5.2 部分失敗 (一部ファイル制約違反) の出力例:
```
INFO  Processing files from: ./data
INFO  processing file=customers.xlsx (1/2)
INFO  sheet=Customers rows=2 inserting...
WARN  processing file=invalid_data.xlsx (2/2) - constraint violation, rolling back
ERROR file=invalid_data.xlsx constraint violation: duplicate key value violates unique constraint 'customers_pkey'
SUMMARY files=2/2 success=1 failed=1 rows=2 skipped_sheets=0 elapsed_sec=1.23 throughput_rps=1626.0
```
**終了コード**: 2 (部分失敗)

### 5.3 FK 伝播の出力例:
```
INFO  Processing files from: ./data
INFO  processing file=customers_with_orders.xlsx (1/1)
INFO  sheet=Customers rows=3 inserting with RETURNING...
INFO  FK propagation: captured 3 parent keys for customer_id
INFO  sheet=Orders rows=4 inserting with propagated FKs...
SUMMARY files=1/1 success=1 failed=0 rows=7 skipped_sheets=0 elapsed_sec=1.05 throughput_rps=6666.7
```
**特徴**: 
- Customers シートでは `id` 列が sequence で自動生成され、`RETURNING` で取得
- Orders シートでは `customer_id` 列に親の `id` 値が自動挿入される

`logs/errors-YYYYMMDD-HHMMSS.log` が生成 (エラーなしなら空/未作成の場合あり) (FR-030)。

---
## 6. FK 伝播の詳細例

FK 伝播機能により、親シートで生成された PK を子シートの FK 列に自動設定できます。

### 6.1 設定例 (FK 伝播あり)
```yaml
sheet_mappings:
  Customers:
    table: customers
    sequence_columns: [id]
    fk_propagation_columns: []  # 親なので空
  Orders:
    table: orders  
    sequence_columns: [id]
    fk_propagation_columns: [customer_id]  # 親から伝播する列
sequences:
  id: customers_id_seq
fk_propagations:
  customer_id: id  # Orders.customer_id ← Customers.id
```

### 6.2 Excel ファイル例 (FK 伝播用)
**Customers シート:**
| (タイトル行) | Customer Master |
|-------------|-----------------|
| id | name | email |
| (空白) | Alice | alice@example.com |
| (空白) | Bob | bob@example.com |

**Orders シート:**
| (タイトル行) | Order Details |
|-------------|---------------|
| id | customer_id | amount |
| (空白) | Alice | 1500.00 |
| (空白) | Bob | 2500.00 |
| (空白) | Alice | 800.00 |

**処理結果:**
1. Customers → `id` が sequence で生成 (例: Alice=101, Bob=102)
2. Orders → `customer_id` 列の "Alice", "Bob" が自動的に 101, 102 に置換

---
## 7. エラーログ例
挿入失敗時の JSON Lines 内容例:
```json
{"timestamp":"2025-09-26T10:12:33Z","file":"customers.xlsx","sheet":"Orders","row":2,"error_type":"CONSTRAINT_VIOLATION","db_message":"duplicate key value violates unique constraint 'orders_pkey'"}
```

---
## 8. 部分失敗の詳細例

複数ファイル処理時に一部が失敗した場合の動作例:

### 8.1 シナリオ
- `customers.xlsx` (成功予定)
- `duplicate_customers.xlsx` (制約違反で失敗予定)

### 8.2 実行結果
```bash
$ python -m src.cli
INFO  Processing files from: ./data
INFO  processing file=customers.xlsx (1/2)
INFO  sheet=Customers rows=2 committed successfully
INFO  processing file=duplicate_customers.xlsx (2/2)
ERROR file=duplicate_customers.xlsx transaction rolled back: constraint violation
SUMMARY files=2/2 success=1 failed=1 rows=2 skipped_sheets=0 elapsed_sec=1.45 throughput_rps=1379.3
```

### 8.3 エラーログ (`logs/errors-YYYYMMDD-HHMMSS.log`)
```json
{"timestamp":"2025-09-26T15:23:45Z","file":"duplicate_customers.xlsx","sheet":"Customers","row":3,"error_type":"CONSTRAINT_VIOLATION","db_message":"duplicate key value violates unique constraint 'customers_pkey'"}
```

**結果**: 
- `customers.xlsx` → DB にコミット済み
- `duplicate_customers.xlsx` → 完全にロールバック (影響なし)
- 終了コード: 2

---
## 9. 終了コード
| Code | 説明 |
|------|------|
| 0 | 全ファイル成功 |
| 2 | 一部失敗 (少なくとも1ファイルロールバック) |
| 1 | 起動時致命的エラー (設定不正, DB接続不可 など) |

---
## 10. 性能確認 (スモーク)
小規模データで throughput_rps が >800 を大幅に超えることを目安に初期性能を確認。大量データ検証は別途性能テストで実施。

---
## 11. トラブルシュート
| 症状 | 原因候補 | 対処 |
|------|----------|------|
| exit code 1 | config/import.yml 不備 | スキーマ確認 (contracts/config_schema.yaml) |
| exit code 2 | データ制約違反 | エラーログ JSON Lines 確認 |
| rows=0 | シートヘッダ不一致/マッピング不足 | sheet_mappings と Excel 2 行目見直し |
| skipped_sheets>0 | 設定未定義シート | 必要なら sheet_mappings に追加 |
| throughput 低い | バッチサイズ小 / ネット遅延 | 後続チューニング (R-006) |
| FK 伝播エラー | 親子シート順序不正 | 親シートを子より先にマッピング設定 |
| 部分失敗継続しない | orchestrator 未実装 | 実装状況確認、モック使用時は正常動作 |

---
## 12. 次に読む
- `contracts/summary_output.md` (出力フォーマット)
- `contracts/error_log_schema.json` (エラーログスキーマ)
- `data-model.md` (内部ドメインモデル)
- `research.md` (性能/設計判断根拠)

---
*Quickstart 完了*
