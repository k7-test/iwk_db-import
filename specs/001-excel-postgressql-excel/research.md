# Research: Excel -> PostgreSQL バルク登録 CLI ツール

**Feature Branch**: 001-excel-postgressql-excel  
**Date**: 2025-09-26  
**Status**: In Progress (Phase 0)

## Purpose
Phase 0 で特定した未確定または最適化余地のある技術要素について調査し、採用方針 (Decision) と理由 (Rationale)、検討したが採用しない代替案 (Alternatives) を明示する。最終的に `plan.md` の Technical Context 未確定項目を確定し、以降の設計 (Phase 1) を安定化させる。

## Scope of Research Items
| ID | Topic | Goal | Status |
|----|-------|------|--------|
| R-001 | INSERT バッチ方式 (execute_values vs COPY) | 性能目標 (≥800 rows/sec) を安定達成 | Pending |
| R-002 | ログ基盤 (標準 logging vs loguru) | 構造化/レベル表記/JSON lines 実装コスト最小化 | Pending |
| R-003 | 進行表示実装 (tqdm 差分更新) | QR-008 のスパム抑止と1秒以内更新実現 | Pending |
| R-004 | pandas dtype 最適化 | メモリ上限 <512MB 達成 | Pending |
| R-005 | エラーログバッファリング戦略 | I/O ボトルネック回避 + 安全フラッシュ | Pending |
| R-006 | バッチサイズチューニング | p95 60s 達成/行レイテンシ最適化 | Pending |
| R-007 | RETURNING 最小化条件 | FR-029 遵守 (必要時のみ取得) 明確化 | Pending |

---

## R-001: INSERT バッチ方式 (execute_values vs COPY)
**Question**: 初版で性能目標 (≥800 rows/sec, p95 60s) を満たすための最小実装コスト戦略は何か。

### Options
1. psycopg2.extras.execute_values (バッチ INSERT)
2. psycopg2.copy_from / copy_expert (COPY プロトコル) ※pandas DataFrame → CSV ライク変換必要
3. 単純 executemany (低速リスク)

### Evaluation
| Criterion | execute_values | COPY | executemany |
|-----------|----------------|------|-------------|
| 実装コスト | 低 | 中 (前処理変換) | 低 |
| スループット | 高 (中～大バッチ) | 非常に高 | 低～中 |
| メモリ追加 | 低 | 中 (一時バッファ) | 低 |
| 柔軟な列除外 | 容易 | 容易 | 容易 |
| エラー行特定 | バッチ失敗時特定難 | より困難 | 行単位容易 |

### Preliminary Benchmark (参考値/文献):
- execute_values: 5k～20k rows/sec (環境依存, 中規模列数) 報告例多数。
- COPY: 20k rows/sec 以上到達例あり (最適化必要)。
- executemany: 数百～1k rows/sec 程度で頭打ち報告例。

### Decision
採用: execute_values (初版)。

### Rationale
- 目標 800 rows/sec は execute_values で十分射程内。
- COPY はエラー扱いと列マッピング調整に追加実装コストがかかる。
- executemany では性能リスクが高い。
- 後続改良として COPY 最適化ブランチをパフォーマンス向上タスク化可能。

### Alternatives (Rejected)
- COPY: 初期コスト > 目標必要性。行エラー分離戦略別途必要。
- executemany: 性能閾値リスク。

### Follow-up Metrics
- バッチサイズ毎 (500, 1000, 2000, 5000) の行/秒計測。
- p95 ファイル処理時間 (代表 50k行, 40列 DataFrame) 測定ログ保存。

---

## R-002: ログ基盤 (標準 logging vs loguru)
### Requirements Mapping
- QR-003 (ラベル統一), QR-007 (構造計測), FR-030 (固定エラーログスキーマ)。

### Options
1. 標準 logging + Formatter (JSONLines 用ハンドラ)
2. loguru (シンプル API + シリアライズ拡張)

### Comparison
| Criterion | logging | loguru |
|-----------|---------|--------|
| 標準性 | 高 | 中 |
| 依存追加 | 不要 | 必要 |
| JSON Lines 実装 | 手動 (custom handler) | sink 指定で容易 |
| 型安全/静的解析 | 良 | 良 |
| 初期化簡素性 | 中 | 高 |

### Decision
採用: 標準 logging。

### Rationale
- 追加依存を避け Code Quality Baseline に適合。
- 要求される機能は custom Formatter/Handler で完結。

### Alternatives
- loguru: 実装速度有利だが依存増加を理由に保留。

### Follow-up
- `logging.handlers` + size/行数ベースローテ不要 (起動毎新規ファイル)。
- エラーログ: バッファリングは内部バッファ(List) + flushタイミングでファイル追記。

---

## R-003: 進行表示 (tqdm 差分更新)
### Goal
QR-008: 1秒以内更新 / スパム抑止。

### Strategy
- ファイル進捗: current / total (INFO行再描画)
- シート処理: シート開始時に1行 INFO、完了時に SUMMARY 増分。
- tqdm 導入は大規模出力時も抑制可能。`tqdm(disable=not is_tty)` で制御。

### Decision
採用: tqdm (単一インスタンス) + 手動ログ併用。

### Rationale
- 実装労力 < 自前制御カーソル制御。
- 非TTY環境(CI)でも冗長 ANSI を避ける制御簡易。

### Alternatives
- 完全手書き差分: 柔軟だがメンテ性低。

---

## R-004: pandas dtype 最適化
### Goal
メモリピーク <512MB (QR-006)。

### Baseline Estimation
- 50,000 行 × 40 列 = 2,000,000 セル。
- object 文字列平均 30 bytes 仮定 → 60MB + DataFrame オーバーヘッド。
- 数値列は int32/float32 へ downcast で削減。

### Techniques
- 初回読込後: `df.convert_dtypes()` + selective `astype`。
- 数値列: `pd.to_numeric(errors="ignore", downcast="integer")` / `downcast="float"`。
- カテゴリ候補 (高重複) 列: `astype('category')` (ただし INSERT 変換コスト観察)。

### Decision
基本: convert_dtypes + numeric downcast。カテゴリ化は高重複>70% 列のみ適用 (Phase 1 ユーティリティ化)。

### Alternatives
- 事前 dtype 指定 (設定ファイル拡張): 現段階で過剰、第二フェーズで検討。

### Validation Plan
- サンプル最大規模 DataFrame で memory_usage(deep=True) を測定し research.md に結果追記。

---

## R-005: エラーログ バッファリング戦略
### Requirements
FR-030, QR-009: バッファリングしてファイル終了時 flush。

### Strategy
- in-memory list (ErrorRecord JSON strings)
- ファイル単位 flush (成功/失敗問わず finally)
- 想定最大エラーレコード: 制約違反大量でも 50,000 行 (最悪ケース) → 1行 ~160 bytes 想定 ≈ 8MB: 許容。

### Decision
採用: シート毎即時追加, ファイル終了時 flush。致命的例外時も finally flush。

### Alternatives
- 行毎即 write: I/O 多発。
- サイズ閾値 flush: 実装複雑化メリット小。

### Failure Handling
- flush 失敗時: 標準エラーへ最終ダンプ (JSON array) + EXIT CODE=2 に影響 (集計エラー追加)。

---

## R-006: バッチサイズ チューニング
### Goal
p95 60s & ≥800 rows/sec 安定。

### Initial Hypothesis
- 1000~2000 行/バッチ が DB 往復コストとメモリバランス良。

### Experiment Plan
| Batch | 指標 | 期待 |
|-------|------|------|
| 500 | latency | 安定/往復多 | 
| 1000 | throughput | baseline |
| 2000 | throughput | 改善 | 
| 5000 | メモリ/エラー影響 | 限界確認 |

### Decision (Provisional)
暫定既定値: 1000 行。計測後 research.md に最終決定追記。

### Metrics Capture
- 行/秒 (総行 / 経過秒)
- 単バッチ平均時間, p95 バッチ時間

---

## R-007: RETURNING 最小化条件
### Requirement
FR-029: 必要な場合のみ RETURNING を利用。

### Use Cases
- PK 値を後続 FK 伝播に使用する必要があるケース。
- サマリー集計は PK 値不要。(行数は len(DataFrame))

### Decision
デフォルト: RETURNING なし。親テーブル → 子テーブルで親生成PK が必要な場合のみ 1回目 INSERT で RETURNING 取得→メモリ上 map 保持。

### Alternatives
- 常に RETURNING: 不要オーバーヘッド。
- 逐次単行 INSERT: 性能劣化。

### Implementation Note (to Phase 1)
- service 層で「親シーケンス列が FK 伝播設定に含まれるか」を判定し戦略分岐。

---

## Open Questions (現在なし)
(新規不確定が発生した場合ここに [OQ-###] で追記)

---
## Summary of Decisions
| Topic | Decision | Revisit Trigger |
|-------|----------|-----------------|
| INSERT 戦略 | execute_values | スループット < 800 rows/sec |
| Logging | 標準 logging | JSON構造が肥大/複雑化 |
| 進行表示 | tqdm | CI出力ノイズ過多 |
| dtype 最適化 | convert_dtypes + selective downcast | メモリ>512MB |
| Error Log flush | ファイル終了時まとめ書き | エラー>50% ケースで遅延懸念 |
| バッチサイズ | 1000 (暫定) | p95>60s / rows/sec<800 |
| RETURNING 条件 | 親FK伝播必要時のみ | 新たな依存列追加 |

---
## Next Steps (to Phase 1)
1. data-model.md で各 Entity (ExcelFile, SheetMapping, RowData, ProcessingResult, ErrorRecord) 詳細化 (型/制約)。
2. contracts/: CLI 入出力契約 (終了コード, SUMMARY 行書式, エラーログ1行JSON検証用 schema)。
3. failing テスト生成: config ロード, 単一ファイル成功, 失敗ロールバック, エラーログ出力, 性能スモーク scaffold。
4. バッチ挿入用ユーティリティ (execute_values wrapper) のインタフェース設計。
5. logging 初期化モジュール (ラベル付与 + JSON lines writer + メトリクス計測) ドラフト。

---
*End of Research (Phase 0 deliverable draft)*
