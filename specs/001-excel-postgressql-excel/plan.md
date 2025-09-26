
# Implementation Plan: Excel -> PostgreSQL バルク登録 CLI ツール

**Branch**: `001-excel-postgressql-excel` | **Date**: 2025-09-26 | **Spec**: `specs/001-excel-postgressql-excel/spec.md`
**Input**: Feature specification from `specs/001-excel-postgressql-excel/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
複数のExcelファイル(.xlsx)を指定フォルダから走査し、設定ファイル (`config/import.yml`) に定義されたシート→テーブル対応に従って PostgreSQL へバルク登録する単一 CLI ツールを提供する。ファイル単位でトランザクション整合性を確保し (FR-002)、途中エラー時はそのファイルのみロールバックし他ファイル処理を継続 (FR-009)。PK/親FK列はExcel値を無視しDB側自動採番/親値伝播 (FR-006, FR-007, FR-021)。処理終了後に成功/失敗/挿入行数/スキップ数/所要時間サマリーを表示 (FR-011) し JSON Lines 形式のエラーログを出力 (FR-008, FR-030)。初版はシリアル処理で安定性優先 (QR-010)。性能目標: 50,000 行/ファイル規模で p95 60 秒以内 (QR-004), スループット ≥800 行/秒 (QR-005), メモリ <512MB (QR-006)。

## Technical Context
**Language/Version**: Python 3.11 (仮定: プロジェクト標準。変更が必要なら後で調整)  
**Primary Dependencies**:
- pandas (Excelシート一括読込 / DataFrame 前処理)  
- openpyxl (pandas の .xlsx エンジン)  
- psycopg2 (PostgreSQL接続, FR-027)  
- PyYAML (設定ファイル読込, FR-014/FR-026)  
- tqdm (進行表示差分更新サポート; QR-008)  
 - 標準 logging (構造化/レベルラベル; QR-003, QR-007)  
**Storage**: PostgreSQL 14+ (シーケンス / IDENTITY / FK 制約)  
**Testing**: pytest + pytest-cov + (性能計測: time/perf フィクスチャ)  
**Target Platform**: Linux server (CI & 運用)  
**Project Type**: single (単一 CLI / ライブラリ構成)  
**Performance Goals**: p95 ファイル処理 ≤ 60s, スループット ≥ 800 行/秒, メモリピーク < 512MB  
**Constraints**:
- 初版はシリアル処理 (QR-010)
- 1ファイル=1トランザクション (FR-002)
- PK/親FK列はExcel値を無視 (FR-006, FR-007, FR-021)
- RETURNING は必要最小限 (FR-029)
- エラーログ JSON Lines 固定スキーマ (FR-030)
- 環境変数優先 DB 接続 (FR-027)
**Scale/Scope**:
- 最大: 100 ファイル / 各ファイル 10 シート / 1 シート最大 50,000 行 × 40 列
- 想定総挿入行数 (バッチ実行あたり): 最大 50,000 行/ファイル × 100 = 5,000,000 行 (シリアル)
**Phase 0 Research 決定事項 (R-001..R-007)**:
| ID | Topic | Decision (要約) |
|----|-------|-----------------|
| R-001 | INSERT Strategy | execute_values 採用 (性能十分 / 実装容易) |
| R-002 | Logging | 標準 logging 採用 (依存削減) |
| R-003 | 進行表示 | tqdm 単一 + 非TTY抑制 |
| R-004 | dtype 最適化 | convert_dtypes + numeric downcast |
| R-005 | Error log flush | ファイル単位 finally flush |
| R-006 | Batch size | 暫定 1000 行 (計測で調整) |
| R-007 | RETURNING | 親FK伝播必要時のみ |
詳細は `research.md` 参照。

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Code Quality Baseline**: ruff / black / mypy (Phase 0 で設定), 依存追加は `DECISIONS.md` に根拠記録、不要/重複ライブラリ禁止。
- [x] **Test-First Delivery**: Phase 1 で契約/統合/ユニットの失敗テストを先行生成し、その後実装。カバレッジ閾値 90% (QR-002) を `pytest --cov --cov-fail-under=90` で強制。
- [x] **Consistent User Experience**: CLI 出力ラベル (INFO|WARN|ERROR|SUMMARY) 一元化。`--help` と README のサマリ書式を同期。進行表示は差分更新 (QR-008)。
- [x] **Performance & Capacity Discipline**: p95 60s / 800 rows/sec / <512MB を `tests/perf/test_performance.py` で測定。行バッチサイズ調整 (Phase 0 実験)。
- [x] **Quality Gates & Metrics**: CI で lint, type, unit, integration, contract, perf smoke (軽量サンプル) 実行。計測値は SUMMARY 出力とログに構造化 (QR-007)。

### Post-Design Re-evaluation (Phase 1 完了)
現状スキャフォールド: config loader / error log buffer / excel reader / batch insert / CLI 基本。Exit code 0,1 シナリオ テスト緑。部分失敗 (exit 2) は未実装 (skip)。カバレッジ >97%。設計過剰なし。Perf は smoke のみ。
→ Post-Design Constitution Check: PASS。

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (generated by /tasks command) ✔
```

ios/ or android/
### Source Code (repository root)
```
src/
├── cli/                 # エントリポイント, 引数処理, 進行表示
├── config/              # 設定読込 (YAML) ローダ & バリデーション
├── excel/               # Excel (pandas) 読込/前処理, 無視列適用
├── db/                  # DB接続, トランザクション境界, INSERT戦略
├── models/              # 内部データモデル (ExcelFile, Sheet, RowData, ErrorRecord など)
├── services/            # 高水準 orchestration (ファイル処理, サマリー集計)
├── logging/             # 構造化/JSON lines エラーログ, メトリクス出力
└── util/                # 汎用ヘルパ (時間計測, バッチ化 等)

tests/
├── contract/            # (Phase 1) CLI 契約 & 出力フォーマット
├── integration/         # E2E: 実際のサンプルExcel + テストDB (docker?)
├── unit/                # 細粒度: config, excel, db, services 各層
└── perf/                # 性能スモーク & バジェット検証 (短時間データ)

config/                  # import.yml (実行時) サンプルとテンプレート
logs/                    # 実行時生成 (Git 管理外)
scripts/                 # ローカル開発補助 (性能計測, サンプル生成)
```

**Structure Decision**: 単一 (single) プロジェクト構成。層は「CLI境界 → orchestration(service) → ドメイン(models) → インフラ(excel/db/logging)」。循環依存を避け、下位層は上位層を参照しない。テストはテスト種別毎に独立ディレクトリでカバレッジ・責務を明確化。

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

追加予定リサーチ項目:
- バッチ INSERT 方法比較: execute_values vs COPY (性能/実装コスト)
- 進行表示ライブラリ (tqdm) の差分更新実装簡素化パターン
- エラーログ JSON Lines のフラッシュ戦略 (バッファサイズ閾値)
- pandas 読込時 dtype 最適化 (メモリ 512MB 以内達成)
- 最適バッチサイズ (行数 vs トランザクション時間, 目標800 rows/sec)

research.md では各項目に Decision / Rationale / Alternatives を記述。

**Output**: research.md with all NEEDS CLARIFICATION resolved (現時点で追加的明示的未解決なし)

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh copilot`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P] 
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Tests before implementation 
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

### Phase 2 へ引き継ぐ主要未実装項目
1. service orchestration (ファイル走査→normalize→DB挿入→集計→部分失敗判定)
2. 部分失敗 exit code=2 実装 & テスト有効化
3. SUMMARY 行メトリクス (rows, skipped_sheets, elapsed_sec, throughput_rps) 実計算
4. FK 伝播 / RETURNING 条件分岐ロジック
5. バッチ計測フック (バッチ時間/行/秒)
6. logging 初期化と統一ラベル出力
7. integration テスト (実 Excel → モックDB or テストDB)
8. perf テスト強化 (代表50k行データ生成ユーティリティ)
9. config schema の jsonschema バリデーションテスト追加
10. エラー行 (行特定不可ケース row=-1) ハンドリング仕様 / ErrorRecord 拡張

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Tasks generated (tasks.md present)
- [ ] Phase 3: Implementation in progress
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v1.0.0 - See `.specify/memory/constitution.md`*
