# Feature Specification: Excel -> PostgreSQL バルク登録CLIツール

**Feature Branch**: `001-excel-postgressql-excel`  
**Created**: 2025-09-26  
**Status**: Draft  
**Input**: User description: "ExcelからPostgresSQLにデータ登録する簡単なツールを開発する。 複数Excelをフォルダ内から読み込み、シート単位でテーブルへ1ファイル1トランザクションで挿入。 設定ファイルでシート名->テーブル名、シーケンス、FKマッピング。 PK/親伝播列はExcel値を無視。 エラーは記録して継続。 最後に集計を表示。"

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Capture Quality & Performance commitments (coverage targets, UX guarantees, performance budgets)
7. Identify Key Entities (if data involved)
8. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ✅ State non-functional expectations (code quality, testing, UX, performance) explicitly
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies  
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
運用担当者は設定ファイルを用意し、対象フォルダにExcelファイルを置いてCLIツールを実行することで、各Excel内の複数シートを対応するPostgreSQLテーブルへ自動登録したい。ファイルごとにトランザクション整合性を確保し、エラーがあっても他ファイルの処理を継続したい。完了後に成功件数・失敗件数を集計したサマリーレポートを受け取りたい。

### Acceptance Scenarios
1. **Given** 設定ファイルと対象フォルダ内に有効なExcelファイルが複数存在する, **When** CLIを実行する, **Then** 各ファイルが1トランザクションで処理され全シートの行が対応テーブルに挿入され成功サマリーが表示される。
2. **Given** あるExcelファイル内の1テーブル挿入中にDB制約違反が発生する, **When** そのトランザクションがロールバックされる, **Then** エラー内容がエラーログファイルに出力され他のExcelファイルの処理は続行される。
3. **Given** PK自動採番列や親FK伝播列にExcel上値が存在する, **When** 読み込み処理が行われる, **Then** それら列のExcel値は無視されDB側のシーケンスまたは親関係設定で値が補完される。
4. **Given** 設定ファイルに存在しないシート名のシートがExcelにある, **When** CLIが実行される, **Then** そのシートはスキップされ警告ログが記録される。

### Edge Cases
- 空ファイル (データ行が存在しない) は0件として成功扱い。
- 同一ファイルを再投入した際の重複 (一意制約違反) はファイル単位ロールバックしエラーログ出力。
- 設定ファイルでマッピングされた列がExcelヘッダ(2行目)に存在しない場合はファイルエラーとしてロールバック。
- シーケンス設定された列にNULL行が多数ある場合も処理継続し自動採番。
- ピーク時: 100ファイル / ファイル最大シート数10 / 各シート最大5万行を目安とし、1ファイル処理開始からコミットまでの目標時間は60秒以内。

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: システムMUST 指定フォルダ内(非再帰)の拡張子.xlsxファイル一覧を取得する。
- **FR-002**: システムMUST 各Excelファイルを1トランザクションで処理し、途中エラー時にはそのファイル分の挿入を全てロールバックする。
- **FR-003**: システムMUST 設定ファイルに定義された シート名→テーブル名 マッピングに従い対応するシートのみを対象とする。
- **FR-004**: システムMUST 各対象シートの2行目を列ヘッダ行として読み取り、3行目以降をデータ行として扱う。
- **FR-005**: システムMUST 列ヘッダとDBテーブル列名が一致する前提でINSERT列集合を決定する。
- **FR-006**: システムMUST 設定ファイルに定義されたPK自動採番列についてExcel入力値を無視し、シーケンスから値を取得する。
- **FR-007**: システムMUST 設定ファイルに定義されたFK伝播列 (親列→子列マッピング) のExcel入力値を無視し、親値を適用する。
- **FR-008**: システムMUST 挿入時に発生したDB例外(制約違反等)をキャプチャし、当該ファイル処理を中止・ロールバックし、エラーログファイルへJSON Lines形式で詳細を書き出す。
- **FR-009**: システムMUST 1ファイル処理失敗時も残りファイルの処理を継続する。
- **FR-010**: システムMUST スキップしたシート(マッピング未定義)を警告ログに記録する。
- **FR-011**: システムMUST 処理完了後に成功ファイル数/失敗ファイル数/挿入行数合計/スキップシート数/処理時間合計を標準出力に要約表示する。
- **FR-012**: システムMUST 設定ファイルでシーケンス名と自動採番列名を複数定義可能にする。
- **FR-013**: システムMUST 設定ファイルで親テーブルからのFK伝播列マッピングを複数定義可能にする。
- **FR-014**: システムMUST CLI単一コマンド(引数なし)で起動し、設定ファイルパスや対象フォルダパスは既定ロケーションを参照する。
- **FR-015**: システムMUST 設定ファイルが存在しない/不正形式の場合は処理を中断しエラー終了コードを返す。
- **FR-016**: システムMUST 設定に存在するシートでExcel側に欠落する列がある場合ファイル全体をエラーとしロールバックする。
- **FR-017**: システムMUST ログ出力先ディレクトリが存在しない場合は起動時に作成する。
- **FR-018**: システムMUST エラーログ1行に ファイル名/シート名/行番号/エラー種別/DBエラーメッセージ/タイムスタンプ を含める。
- **FR-019**: システムMUST サマリー出力を標準出力と同内容でログファイルにも保存する。
- **FR-020**: システムMUST ツールの終了コードを (0=全ファイル成功, 2=一部失敗, 1=起動時致命的エラー) の3種に分類する。
- **FR-021**: システムMUST シーケンス/親FK列にExcelで値が提供された場合は無条件に無視し警告ログを出力する。
- **FR-022**: システムMUST シート毎の挿入成功行数と失敗行数(ロールバック発生で全部失敗の場合は0/総件数)をトラッキングする。
- **FR-023**: システムMUST タイムゾーンは設定ファイルで指定されない限りUTCを使用する。
- **FR-024**: システムMUST 実行中の進行状況 (現在ファイル番号/総ファイル数, シート進行) を標準出力に表示する。
- **FR-025**: システムMUST 対象フォルダにExcelが0件の場合は0件処理のサマリーを正常終了で表示する。

### Quality & Performance Requirements
- **QR-001**: コード品質ゲート (lint/format/static analysis) をCIで必須化し失敗時はマージ不可。
- **QR-002**: クリティカルパス (ファイル走査, シート読込, INSERTバッチ処理) を含む自動テストカバレッジ90%以上を維持しPRで1%以上低下させない。
- **QR-003**: CLI出力の成功/警告/エラーの行頭ラベル (INFO|WARN|ERROR|SUMMARY) は統一し、HelpテキストとREADMEにも記載する。
- **QR-004**: 性能目標: 平均ファイルサイズ(シート合計行数≤50,000, 列数≤40)で1ファイル60秒以内 (p95) にコミット完了する。
- **QR-005**: スループット目標: 50,000行/ファイル構成で最低 800 行/秒 (平均) を達成する。
- **QR-006**: メモリ利用上限: 単一巨大シート(5万行×40列)処理時に常駐メモリ < 512MB を維持する。
- **QR-007**: 計測用に 処理行数/秒 (rolling), ファイル処理時間, 失敗率 をログへ構造化出力する。
- **QR-008**: 進行表示更新は1秒間隔以内、標準出力スパム回避のため最小限の再描画 (差分更新) にする。
- **QR-009**: エラーログ書き込みはI/Oボトルネックを避けるためバッファリングしファイル終了時にフラッシュする。
- **QR-010**: 初回リリースでは同時並行処理を行わずシリアル処理で安定性を優先する。

### Key Entities *(include if feature involves data)*
- **ExcelFile**: 物理ファイル。属性: ファイル名, パス, シート集合, 処理結果ステータス, 処理時間。
- **SheetMapping**: 設定上のシート→テーブル対応。属性: シート名, テーブル名, 列マッピング(暗黙: ヘッダ=列), シーケンス列集合, 親FK伝播列集合。
- **RowData**: 1シートの1行の論理データ。属性: 行番号, 列名→値マップ, 無視列集合。
- **ProcessingResult**: 集計用。属性: 成功ファイル数, 失敗ファイル数, 総挿入行数, スキップシート数, 開始時刻/終了時刻。
- **ErrorRecord**: エラー行情報。属性: ファイル名, シート名, 行番号, 種別, メッセージ, タイムスタンプ。

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous  
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [ ] User description parsed
- [ ] Key concepts extracted
- [ ] Ambiguities marked
- [ ] User scenarios defined
- [ ] Requirements generated
- [ ] Entities identified
- [ ] Review checklist passed

---
