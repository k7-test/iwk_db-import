# Tasks: Excel -> PostgreSQL バルク登録 CLI ツール

**Feature Dir**: `specs/001-excel-postgressql-excel/`  
**Source Root**: `src/` (single-project)  
**Input Docs**: plan.md, research.md, data-model.md, contracts/, quickstart.md  
**Generation Date**: 2025-09-26

## Execution Flow (auto-generated)
```
1. Load plan & design docs (DONE)
2. Derive tasks from: contracts (exit codes, summary, error log, config schema), entities (data-model), research decisions (R-001..R-007), outstanding Phase 2 backlog
3. Order: Setup → Tests (failing first) → Models → Services → Integration/Logging/Metrics → Polish
4. Mark [P] for parallel-safe tasks (distinct files, no dependency)
5. Provide dependency notes & parallel launch examples
```

Legend:  
`[P]` = Can be executed in parallel (independent files, no ordering edge).  
All test tasks must be created & fail before corresponding implementation tasks (TDD gate).

---
## Phase 3.1: Setup / Baseline Adjustments
These tasks ensure any missing dependencies & decision logs needed for Phase 2 are in place.

- [ ] T001 Verify current structure matches `plan.md` (no action if OK) and create `src/models/` & `src/services/` directories if absent.
- [ ] T002 Add runtime config validation dependency (`jsonschema`) to `pyproject.toml` (tool.poetry.dependencies or project deps) & lock file update.
- [ ] T003 [P] Update `DECISIONS.md` adding R-008: "Adopt jsonschema for runtime config validation" (rationale: align with contracts/config_schema.yaml; low complexity). Reference revisit trigger: schema version bump.

## Phase 3.2: Tests First (Contract / Integration / Performance)
Create failing tests BEFORE any implementation below T012+. Some tests may partially exist; extend or un-skip as needed.

### Contract Tests (derived from contracts/)
- [ ] T004 Contract test: config schema validation (invalid/missing keys) in `tests/contract/test_config_schema_validation.py` referencing `contracts/config_schema.yaml`.
- [ ] T005 [P] Contract test: partial failure exit code=2 (one file fails, others succeed) in `tests/contract/test_exit_code_partial_failure.py` (un-skip if existing; ensure fails now).
- [ ] T006 [P] Contract test: summary metrics populated (rows>0, elapsed_sec>0, throughput_rps>=0) in `tests/contract/test_summary_metrics.py` using regex from `contracts/summary_output.md`.
- [ ] T007 [P] Contract test: error log row=-1 sentinel for file-level fatal error in `tests/contract/test_error_log_unknown_row.py` validating `contracts/error_log_schema.json`.
- [ ] T008 [P] Contract test: exit codes mapping (0 success, 1 startup error) ensure existing test extended to assert no exit code 2 on pure success in `tests/contract/test_cli_exit_codes.py`.

### Integration Tests (from spec & quickstart scenarios)
- [ ] T009 Integration test: successful multi-file run (2 files, multiple sheets) verifies inserted row count & SUMMARY alignment in `tests/integration/test_run_success.py`.
- [ ] T010 [P] Integration test: partial failure rollback (one file violates constraint → other commits) in `tests/integration/test_run_partial_failure.py`.
- [ ] T011 [P] Integration test: FK propagation (parent then child sheet referencing parent PK) in `tests/integration/test_fk_propagation.py`.

### Performance / Quality Tests
- [ ] T012 Performance test: throughput & p95 budget (generate synthetic 50k rows DataFrame) in `tests/perf/test_throughput_budget.py` (assert elapsed_sec <= 60 for representative data; gated as smoke if data generation large). Use batch size 1000.
- [ ] T013 [P] Performance test: batch size experiment harness (500 vs 1000 vs 2000) to log (not assert) metrics in `tests/perf/test_batch_size_experiment.py` (skipped by default; developer opt-in).

## Phase 3.3: Domain Models (entities from data-model.md)
Implement or formalize dataclasses & enums (some may currently be implicit or absent). Each in its own file for parallelism.

- [ ] T014 Implement ImportConfig / SheetMappingConfig / DatabaseConfig dataclasses + loader mapping in `src/models/config_models.py` (separate from existing minimal loader; no logic yet).
- [ ] T015 [P] Implement ExcelFile & FileStatus enum in `src/models/excel_file.py`.
- [ ] T016 [P] Implement SheetProcess in `src/models/sheet_process.py`.
- [ ] T017 [P] Implement RowData in `src/models/row_data.py`.
- [ ] T018 [P] Implement ErrorRecord (row=-1 support) in `src/models/error_record.py` (adjust existing `src/logging/error_log.py` later).
- [ ] T019 [P] Implement ProcessingResult, FileStat, MetricsSnapshot in `src/models/processing_result.py`.

## Phase 3.4: Core / Services / Infrastructure Enhancements
Blocked by failing tests from Phase 3.2 & entity definitions.

- [ ] T020 Service orchestration: implement `process_all()` in `src/services/orchestrator.py` (scan directory, per-file transaction, aggregate metrics, return ProcessingResult).
- [ ] T021 Implement partial failure handling logic (catch file-level exceptions → rollback & record; still continue) in `src/services/orchestrator.py` (depends T020).
- [ ] T022 Implement FK propagation + conditional RETURNING logic in `src/services/fk_propagation.py` using R-007 (parent map capture). Depends: T015-T017.
- [ ] T023 Enhance batch insert wrapper to support optional RETURNING & metrics callbacks in `src/db/batch_insert.py` (depends T022).
- [ ] T024 Implement runtime config schema validation (jsonschema) in `src/config/loader.py` (depends T002, T014, T004).
- [ ] T025 Implement logging initialization with labeled prefixes (INFO|WARN|ERROR|SUMMARY) and integrate error log buffer in `src/logging/init.py` (adjust CLI) (depends T018).
- [ ] T026 Implement metrics accumulation & SUMMARY line rendering in `src/services/summary.py` used by CLI main (depends T020, T019).
- [ ] T027 Update CLI main (`src/cli/__main__.py`) to wire orchestrator, handle exit code 2, and print SUMMARY (depends T021, T026).

## Phase 3.5: Integration / Cross-Cutting
- [ ] T028 Implement dataset generation script for perf (`scripts/gen_perf_dataset.py`) producing synthetic Excel with parameterized rows/cols.
- [ ] T029 [P] Add batch timing instrumentation (per batch elapsed, accumulate stats) in `src/db/batch_insert.py` (extends T023) & expose to ProcessingResult.
- [ ] T030 [P] Implement progress display with `tqdm` (TTY only) in `src/services/progress.py` and integrate into orchestrator (depends T020).

## Phase 3.6: Polish / Quality Gates / Docs
- [ ] T031 Remove skips from earlier tests & ensure all green (particularly partial failure & metrics) – adjust tests if assumptions changed.
- [ ] T032 [P] Add unit tests for new FK propagation path in `tests/unit/test_fk_propagation.py`.
- [ ] T033 [P] Add unit tests for summary rendering in `tests/unit/test_summary_render.py`.
- [ ] T034 [P] Add unit tests for config validation error cases in `tests/unit/test_config_validation.py`.
- [ ] T035 Performance report doc `docs/performance.md` summarizing measured throughput & memory vs targets.
- [ ] T036 Update `quickstart.md` with real CLI command & new behaviors (partial failure example, FK propagation).
- [ ] T037 [P] Update `.github/copilot-instructions.md` with newly added modules (services, models, metrics) & last changes section.
- [ ] T038 [P] Update `plan.md` Progress Tracking (mark Phase 3 tasks start / completion) & decisions table if new (R-008 recorded earlier).
- [ ] T039 Final quality gate script: ensure ruff, mypy, pytest (all), coverage ≥90%, perf smoke runs under threshold – add helper script `scripts/quality_gate.sh`.
- [ ] T040 [P] Add README section or `docs/metrics.md` referencing SUMMARY fields & interpretation (if not covered by performance.md).

---
## Dependencies
| Task | Depends On |
|------|------------|
| T002 | T001 |
| T003 | T002 |
| T004 | T001 |
| T005 | T001 |
| T006 | T001 |
| T007 | T001 |
| T008 | T001 |
| T009 | T004-T008 (tests foundation) |
| T010 | T004-T008 |
| T011 | T004-T008 |
| T012 | T004-T008 |
| T014 | T004-T008 |
| T015 | T014 |
| T016 | T014 |
| T017 | T014 |
| T018 | T014 |
| T019 | T014 |
| T020 | T015-T019 |
| T021 | T020 |
| T022 | T015-T017 |
| T023 | T022 |
| T024 | T002,T004,T014 |
| T025 | T018 |
| T026 | T019,T020 |
| T027 | T021,T026 |
| T028 | T020 |
| T029 | T023 |
| T030 | T020 |
| T031 | T020-T027 (implementations) |
| T032 | T022-T023 |
| T033 | T026 |
| T034 | T024 |
| T035 | T028,T029 (metrics) |
| T036 | T027 |
| T037 | T026,T027 |
| T038 | T031 |
| T039 | T031-T038 |
| T040 | T026,T035 |

## Parallel Execution Examples
```
# Example 1: Run initial contract tests in parallel (after T001-T003):
Task: T005 (partial failure exit code test)
Task: T006 (summary metrics test)
Task: T007 (error log row=-1 test)
Task: T008 (exit codes mapping extension)

# Example 2: After entities (T014) are defined:
Task: T015 (ExcelFile)
Task: T016 (SheetProcess)
Task: T017 (RowData)
Task: T018 (ErrorRecord)
Task: T019 (ProcessingResult etc.)

# Example 3: Cross-cutting instrumentation after core services:
Task: T029 (batch timing instrumentation)
Task: T030 (progress display)
Task: T032 (FK unit tests)
Task: T033 (summary unit tests)
Task: T034 (config validation unit tests)
```

## Validation Checklist
- [ ] All contract files mapped to a contract test (cli_exit_codes, summary_output, error_log_schema, config_schema)
- [ ] Each entity in data-model has a model implementation task (ImportConfig, SheetMappingConfig, DatabaseConfig, ExcelFile, SheetProcess, RowData, ErrorRecord, ProcessingResult, MetricsSnapshot, FileStat)
- [ ] Tests precede related implementation tasks
- [ ] [P] tasks don't share file targets
- [ ] Metrics & performance tasks (T012, T013, T029, T035) present
- [ ] UX/doc updates tasks (T036, T037, T040) present
- [ ] Quality gate task (T039) present
- [ ] Decision log update (T003, T038) present

## Notes
- Keep failing tests committed BEFORE implementing corresponding features (enforced by review).
- Large synthetic datasets should be generated on-demand (flag/skip) to keep CI fast.
- FK propagation currently limited to single-level parent→child per R-007; extend only with new research decision.
- Avoid premature COPY optimization; revisit only if throughput < target after instrumentation.

---
*End of tasks.md*
