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

Run performance tests (developer opt-in):
```
# Run batch size experiment (T013)
RUN_BATCH_EXPERIMENT=1 pytest tests/perf/test_batch_size_experiment.py -v -s

# Run all performance tests
pytest tests/perf/ -v
```

## Output & Metrics

### SUMMARY Output
After processing completes, the tool outputs a single SUMMARY line with key metrics:

```
SUMMARY files=2/2 success=2 failed=0 rows=1250 skipped_sheets=1 elapsed_sec=1.84 throughput_rps=679.3
```

**Field explanations:**
- **files**: `processed/total` - Number of `.xlsx` files processed vs detected
- **success**: Files successfully imported (all sheets processed without fatal errors)
- **failed**: Files that failed completely (database connection errors, file corruption, etc.)
- **rows**: Total number of data rows inserted across all files and sheets
- **skipped_sheets**: Sheets skipped due to missing required columns or configuration
- **elapsed_sec**: Total processing time in seconds (excluding startup overhead)
- **throughput_rps**: Processing rate in rows per second (rows/elapsed_sec)

**Exit codes:**
- `0`: All files processed successfully
- `1`: Fatal error (config issues, directory not found, database connection failed)
- `2`: Partial failure (some files succeeded, others failed)

For detailed performance targets and analysis, see [`docs/performance.md`](docs/performance.md).

## Contracts
- Exit codes: `contracts/cli_exit_codes.md`
- SUMMARY regex: `contracts/summary_output.md`
- Error log schema: `contracts/error_log_schema.json`
- Config schema: `contracts/config_schema.yaml`

## Next Steps
- 実際の Excel 読込 (pandas) 実装
- INSERT execute_values 実装 + バッチサイズ調整
- ログ/メトリクス基盤
- エラーログバッファ flush 実装
- CLI エントリポイント & 統合テスト

## License
MIT
