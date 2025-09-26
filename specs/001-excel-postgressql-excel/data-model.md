# Data Model: Excel -> PostgreSQL バルク登録 CLI ツール

**Feature Branch**: 001-excel-postgressql-excel  
**Date**: 2025-09-26  
**Phase**: 1 (Design)  
**Spec Reference**: `specs/001-excel-postgressql-excel/spec.md`

## 目的
本ドキュメントは仕様 (FR/QR) を実装に落とし込むための論理データモデルを定義する。主対象はアプリ内部のドメインモデル / 設定モデル / 処理結果集計モデル / エラーログシリアライザ。永続化は PostgreSQL だが、アプリは中間テーブルを追加しない (既存ターゲットテーブルへ直接挿入)。よって本モデルはメモリ上構造 + 挿入用変換責務を定義する。

## モデリング方針
| 項目 | 方針 |
|------|------|
| **責務分離** | 読込 (Excel) / 変換 (無視列・型) / 挿入(DB) / ロギング を分離し循環依存を避ける |
| **不変性** | 行データ (`RowData`) は生成後は値マップを変更しない (除外列フィルタ後) |
| **型境界** | Excel -> pandas(DataFrame) -> 正規化(dict[str, Any]) -> DBパラメータ(list[tuple]) |
| **可観測性** | メトリクス (行数/処理時間) は専用集計 (`ProcessingResult`) で一元管理 (QR-007) |
| **エラーロギング** | `ErrorRecord` は JSON Lines シリアライズ専用 DTO (FR-030) |
| **設定整合性** | `ImportConfig` ロード時に構造検証し、実行時は immutable とする (FR-014, FR-026) |

## Excel -> DB 型マッピング (論理)
| Excel (推定) | pandas dtype 初期 | 正規化型 (Python) | DB プレースホルダ型例 | 備考 |
|--------------|------------------|-------------------|------------------------|------|
| 数値 (整数) | int64 | int | INTEGER/BIGINT | downcast で int32 になる場合あり |
| 数値 (少数) | float64 | float | DOUBLE PRECISION | 必要に応じ decimal 変換 (将来) |
| 文字列 | object | str | TEXT/VARCHAR | 前後空白 trim (任意改善) |
| 日付/日時 | datetime64[ns] | datetime | TIMESTAMP WITH TZ | timezone を UTC に正規化 (FR-023) |
| ブール | bool | bool | BOOLEAN | 空セル→NULL |
| 空白/NaN | NaN | None | NULL | 挿入前に None に統一 |

## エンティティ定義

### 1. ImportConfig
設定ファイル全体を表すルートオブジェクト (FR-014, FR-026, FR-027)。

| フィールド | 型 | 必須 | 説明 | 関連FR |
|-----------|----|------|------|--------|
| source_directory | str | Yes | Excel ファイル探索ディレクトリ | FR-001, FR-014, FR-026 |
| sheet_mappings | dict[str, SheetMappingConfig] | Yes | シート名→マッピング | FR-003, FR-026 |
| sequences | dict[str, str] | Yes (空可) | 列名→シーケンス名 (参照用/記録用) | FR-012, FR-026 |
| fk_propagations | dict[str, str] | Yes (空可) | 親列→子列 (列名) | FR-007, FR-013, FR-026 |
| timezone | str | No | 指定無なら "UTC" | FR-023, FR-026 |
| database | DatabaseConfig | Yes | DB 接続フォールバック | FR-027 |

### 2. SheetMappingConfig
1 シートに対するターゲットテーブルと列扱いの設定。

| フィールド | 型 | 必須 | 説明 | 関連FR |
|-----------|----|------|------|--------|
| sheet_name | str | Yes | Excelシート名 (キー重複禁止) | FR-003 |
| table_name | str | Yes | 挿入先テーブル名 | FR-003 |
| sequence_columns | set[str] | No | 自動採番で Excel 値無視する列 | FR-006, FR-012 |
| fk_propagation_columns | set[str] | No | 親から値伝播する列 | FR-007, FR-013 |
| expected_columns | set[str] | No (派生) | Excel ヘッダ存在必須列 (列欠落エラー判定) | FR-016 |

### 3. DatabaseConfig
環境変数で不足時のみ使用するフォールバック設定 (FR-027)。

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| host | str | No | PGHOST 未設定時 |
| port | int | No | PGPORT 未設定時 |
| user | str | No | PGUSER |
| password | str | No | PGPASSWORD |
| database | str | No | PGDATABASE |
| dsn | str | No | まとめ指定 (env が優先) |

### 4. ExcelFile
実行対象ファイルの処理コンテキスト。

| フィールド | 型 | 必須 | 説明 | 関連FR |
|-----------|----|------|------|--------|
| path | Path | Yes | フルパス | FR-001 |
| name | str | Yes | ファイル名 | FR-001 |
| sheets | list[SheetProcess] | Yes | 対象シート処理単位 | FR-003 |
| start_time | datetime | No | 処理開始 (UTC) | QR-007 |
| end_time | datetime | No | 処理終了 (UTC) | QR-007 |
| status | FileStatus | Yes | pending/processing/success/failed | FR-002, FR-009 |
| total_rows | int | No | 成功時総挿入行数 (親採番列除外後) | FR-011 |
| skipped_sheets | int | No | マッピング無シート数 | FR-010 |
| error | str | No | 失敗理由サマリ | FR-008 |

**FileStatus (Enum)**: pending → processing → (success | failed)

### 5. SheetProcess
1 シート処理単位。

| フィールド | 型 | 必須 | 説明 | 関連FR |
|-----------|----|------|------|--------|
| sheet_name | str | Yes | Excel シート名 | FR-003 |
| table_name | str | Yes | 対応テーブル | FR-003 |
| mapping | SheetMappingConfig | Yes | 設定参照 | FR-003 |
| rows | list[RowData] | No | 正常化済み行データ | FR-004, FR-005 |
| ignored_columns | set[str] | No | 自動採番/FK伝播で除外した列 | FR-006, FR-007, FR-021 |
| inserted_rows | int | No | コミット成功行数 | FR-022 |
| error | str | No | シートレベルエラー | FR-008 |

### 6. RowData
1 行の論理表現 (Excel -> 正規化後)。

| フィールド | 型 | 必須 | 説明 | 関連FR |
|-----------|----|------|------|--------|
| row_number | int | Yes | Excel 上の元行番号 (3行目=1データ開始) | FR-004, FR-018 |
| values | dict[str, Any] | Yes | 列名→値 (除外列含まない) | FR-005, FR-006 |
| raw_values | dict[str, Any] | No | 元値 (デバッグ/警告用) | FR-021 |
| invalid | bool | No | 行レベル不正(将来拡張) | 予備 |

### 7. ErrorRecord (ログ出力 DTO)
FR-018, FR-030 の固定スキーマ。

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| timestamp | str | Yes | ISO8601 UTC | 
| file | str | Yes | ファイル名 |
| sheet | str | Yes | シート名 |
| row | int | Yes | 行番号 (RowData.row_number) |
| error_type | str | Yes | 例: CONSTRAINT_VIOLATION / MISSING_COLUMN |
| db_message | str | Yes | DB 例外 / バリデーションメッセージ |

シリアライズ後の追加キー禁止 (FR-030)。

### 8. ProcessingResult
集計およびサマリー出力用 (FR-011, FR-022, QR-007)。

| フィールド | 型 | 必須 | 説明 | 関連FR/QR |
|-----------|----|------|------|-----------|
| success_files | int | Yes | 成功ファイル数 | FR-011 |
| failed_files | int | Yes | 失敗ファイル数 | FR-011 |
| total_inserted_rows | int | Yes | 総挿入行数 | FR-011 |
| skipped_sheets | int | Yes | スキップシート合計 | FR-010, FR-011 |
| start_time | datetime | Yes | 全体開始 | QR-007 |
| end_time | datetime | Yes | 全体終了 | QR-007 |
| elapsed_seconds | float | Yes | end - start | QR-004 |
| throughput_rows_per_sec | float | Yes | total_inserted / elapsed | QR-005 |
| file_stats | list[FileStat] | No | ファイル詳細 | QR-007 |

**FileStat** (内部補助)
| フィールド | 型 | 説明 |
|-----------|----|------|
| file_name | str | ファイル名 |
| status | str | success/failed |
| inserted_rows | int | 成功時行数 |
| elapsed_seconds | float | ファイル処理時間 |

### 9. MetricsSnapshot (オプション)
リアルタイム進行表示用構造 (QR-007, QR-008)。初版はオンメモリのみ。

| フィールド | 型 | 説明 |
|-----------|----|------|
| current_file_index | int | 現在ファイル番号 |
| total_files | int | 総ファイル数 |
| current_sheet | str | 現在処理シート |
| processed_rows_in_file | int | 現ファイルで処理済行数 |
| last_update | datetime | 最終表示更新時刻 |

## リレーション概要
```
ImportConfig ──1..*──> SheetMappingConfig
ExcelFile ──1..*──> SheetProcess ──1..*──> RowData
ProcessingResult ──aggregates──> FileStat
SheetMappingConfig references: sequence_columns, fk_propagation_columns
ErrorRecord ──(independent DTO, references ExcelFile.name / SheetProcess.sheet_name / RowData.row_number)──>
```

## バリデーション & ルール対応一覧
| ルール | 実現ポイント | 関連FR/QR |
|--------|--------------|-----------|
| ファイル拡張子 .xlsx のみ | ファイル列挙フェーズ (ExcelFile 作成前) | FR-001 |
| シートマッピング未定義はスキップ | ExcelFile -> SheetProcess 構築時 | FR-003, FR-010 |
| 2行目ヘッダ必須 | Sheet 読込時 -> DataFrame columns 検証 | FR-004 |
| ヘッダ列 = DB列 | RowData 正規化 (列集合一致) | FR-005 |
| PK/親列 Excel 値無視 | RowData 正規化 (除外列追跡) | FR-006, FR-007, FR-021 |
| 列欠落はファイルロールバック | SheetProcess 構築時 (expected_columns 差分) | FR-016 |
| シーケンス/親列 Excel 値存在は警告 | 無視列検出時 Logging Hook | FR-021 |
| エラー行 JSON Lines | ErrorRecord シリアライズ | FR-018, FR-030 |
| サマリー計測 | ProcessingResult 集計 | FR-011, QR-007 |
| 進行表示差分更新 | MetricsSnapshot | QR-008 |
| スループット計算 | ProcessingResult.throughput_rows_per_sec | QR-005 |
| メモリ最適化 | pandas 読込後 downcast | QR-006 |

## シーケンス & FK 伝播処理戦略
1. INSERT 対象列集合 = (DataFrame 列) - (sequence_columns ∪ fk_propagation_columns)
2. 親テーブルで RETURNING が必要な場合: 親 INSERT (RETURNING pk) → Map に格納 → 子 RowData 生成時に該当 fk_propagation_columns を補完。
3. 複数親が存在する複雑ケースは初版範囲外 (将来拡張: 複数段階依存ソート)。

## エラーハンドリングモデル
| 階層 | 例 | 影響 | ロールバック | ログ |
|------|----|------|--------------|------|
| ファイル致命的 | 列欠落, DB接続失敗 | そのファイル失敗 | ファイル単位 | ErrorRecord(該当行不明→row=-1 等) |
| シート致命的 | 制約違反 (バッチ) | ファイル失敗 | ファイル単位 | 全失敗扱い, 行特定不要 (batch) |
| 行単位 (将来) | 個別検証エラー | (未対応) | (将来部分継続) | 行単位 ErrorRecord |

初版はバッチ単位エラーで行特定しない (R-001 決定)。

## パフォーマンス計測フィールド
- 処理時間: `ExcelFile.start_time/end_time`, `FileStat.elapsed_seconds`
- 行/秒: `ProcessingResult.throughput_rows_per_sec`
- p95 判定: テスト側で複数 FileStat 収集後統計算出 (モデルは単純配列保持)

## 拡張余地 (Phase 1 以降候補)
| 項目 | 目的 | 影響 |
|------|------|------|
| 行単位部分失敗許容 | 大規模ファイルで成功率向上 | エラーモデル複雑化 |
| dtype 設定拡張 | 精度/性能チューニング | 設定スキーマ変更 |
| 並列処理 | スループット向上 | トランザクション/メモリ調整 |
| COPY 最適化オプション | 高速化 | 実装複雑化 |

## 実装インタフェース案 (抜粋)
```python
# models/excel_file.py
@dataclass(frozen=True)
class ExcelFile:
    path: Path
    name: str
    sheets: list["SheetProcess"]
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: FileStatus = FileStatus.PENDING
    total_rows: int = 0
    skipped_sheets: int = 0
    error: str | None = None
```

```python
# models/row_data.py
@dataclass(frozen=True)
class RowData:
    row_number: int
    values: dict[str, Any]
    raw_values: dict[str, Any] | None = None
```

## 要求対応サマリー (トレーサビリティ)
| エンティティ/構造 | 主要関連 FR/QR |
|--------------------|----------------|
| ImportConfig | FR-014, FR-026, FR-027 |
| SheetMappingConfig | FR-003, FR-006, FR-007, FR-012, FR-013, FR-016 |
| ExcelFile | FR-001, FR-002, FR-009, FR-011, FR-022 |
| SheetProcess | FR-003, FR-004, FR-005, FR-006, FR-007, FR-021, FR-022 |
| RowData | FR-004, FR-005, FR-006, FR-007, FR-021 |
| ErrorRecord | FR-008, FR-018, FR-030, QR-009 |
| ProcessingResult | FR-011, FR-022, QR-004, QR-005, QR-007 |
| MetricsSnapshot | QR-007, QR-008 |

---
*End of Phase 1: data-model draft*
