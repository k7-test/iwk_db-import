# Excel -> PostgreSQL Bulk Import CLI

Prototype feature branch: `001-excel-postgressql-excel`

## Overview
複数Excelファイルを設定ファイルに基づき PostgreSQL へ 1ファイル=1トランザクションでバルク登録する CLI ツール。

## Key Requirements (抜粋)
- ファイル単位トランザクション / 途中エラーでそのファイルのみロールバック
- PK/FK 伝播列は Excel 値無視 (DB側自動採番/親値補完)
- JSON Lines エラーログ / SUMMARY 行出力
- p95 60s / ≥800 rows/sec / <512MB メモリ (代表負荷)
- 初版はシリアル処理

## Repository Structure (Feature Scope)
```
specs/001-excel-postgressql-excel/
  spec.md
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/
src/
  config/loader.py (scaffold)
/tests
  unit/
  contract/
  integration/
  perf/
```

## Development
Install dev deps (will refine once lock file added):
```
pip install -e .[dev]
```
Run tests:
```
pytest
```

## Contracts
- Exit codes: `contracts/cli_exit_codes.md`
- SUMMARY regex: `contracts/summary_output.md`
- Error log schema: `contracts/error_log_schema.json`
- Config schema: `contracts/config_schema.yaml`

## Task Management

This project has 40 implementation tasks organized in phases. To convert tasks to GitHub issues for tracking:

```bash
# Create all GitHub issues from tasks.md
./scripts/batch_create_issues.sh
```

See [`docs/task-to-issue-conversion.md`](docs/task-to-issue-conversion.md) for detailed instructions.

## Next Steps
- 実際の Excel 読込 (pandas) 実装
- INSERT execute_values 実装 + バッチサイズ調整
- ログ/メトリクス基盤
- エラーログバッファ flush 実装
- CLI エントリポイント & 統合テスト

## License
MIT
