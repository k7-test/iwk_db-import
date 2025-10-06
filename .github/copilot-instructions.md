# Copilot Instructions (Agent Context)

Feature: Excel -> PostgreSQL bulk import CLI (Branch `001-excel-postgressql-excel`)

## Scope Snapshot
- Read multiple `.xlsx` files from configured `source_directory`.
- Per-file transaction (commit on success, rollback on failure).
- 2nd row = header, 1st row optional title/ignored.
- Batch insert via `psycopg2.extras.execute_values` (R-001).
- Sequence / parent FK columns ignored in Excel (values supplied by DB / propagation) (FR-006/007/021).
- Error log: JSON Lines, strict schema, flushed per file (R-005, FR-018/030).
- SUMMARY line contract (see `contracts/summary_output.md`).
- Performance targets (QR-004/005/006): p95 ≤60s/file (50k rows), ≥800 rows/sec, peak mem <512MB.

## Key Decisions (See `DECISIONS.md` / `research.md` for rationale)
| ID | Decision |
|----|----------|
| R-001 | Use `execute_values` for inserts |
| R-002 | Standard `logging` only |
| R-003 | `tqdm` for progress (TTY only) |
| R-004 | `convert_dtypes` + numeric downcast, defer categories |
| R-005 | Flush error log once per file |
| R-006 | Default batch size 1000 |
| R-007 | RETURNING only when FK propagation required |

## Current Implementation Status (Phase 4 Complete)
Core implementation:
- Config loader (`src/config/loader.py`) with jsonschema runtime validation + default timezone.
- Error log buffer & `ErrorRecord` (JSON serialization) (`src/logging/error_log.py`).
- Logging initialization (`src/logging/init.py`) with labeled prefixes (INFO/WARN/ERROR/SUMMARY).
- Excel reader & normalization (`src/excel/reader.py`) with header & expected column checks.
- Batch insert abstraction (`src/db/batch_insert.py`) with optional RETURNING & metrics callbacks.
- CLI (`src/cli/__main__.py`) integrated with orchestrator, supports exit codes 0/1/2, real SUMMARY output.
- Contract tests: exit codes, summary regex, error log schema (all passing).
- Performance tests: throughput budget validated, batch size experiments available.

Domain models (complete):
- Config models (`src/models/config_models.py`) domain dataclasses for ImportConfig, DatabaseConfig, SheetMappingConfig.
- Processing result models (`src/models/processing_result.py`) for ProcessingResult, FileStat, MetricsSnapshot with batch timing stats.
- Excel file models (`src/models/excel_file.py`, `src/models/sheet_process.py`, `src/models/row_data.py`) for file processing workflow.
- Error record model (`src/models/error_record.py`) for structured error logging with row=-1 support.

Services (complete):
- Orchestration service (`src/services/orchestrator.py`) coordinating file processing, transactions, partial failure handling.
- Summary service (`src/services/summary.py`) for SUMMARY line rendering from ProcessingResult.
- Progress tracking (`src/services/progress.py`) with tqdm (TTY only).
- FK propagation service (`src/services/fk_propagation.py`) for parent-child relationship handling with conditional RETURNING.

Validation:
- Test coverage: 94.81% (exceeds 90% target).
- All contract tests passing (161 passed, 13 skipped).
- Performance targets validated: >10,000 rps (12.5× above target), <60s p95, <512MB memory.
- Quality gate scripts (`scripts/quality_gate.sh`, `scripts/gen_perf_dataset.py`) in place.

Remaining work:
1. Integration tests with real DB fixtures (currently skipped in mock mode).
2. Optional batch size tuning in production (R-006 recommends batch_size=2000).
3. Enhanced skipped_sheets detailed handling (minor feature, test currently skipped).

## Coding Conventions
- Python 3.11, type hints strict (`mypy --strict`).
- Lint: ruff (line length 100). Keep new dependencies justified in `DECISIONS.md` first.
- Tests first: add / update failing tests before implementation changes.
- Keep layers acyclic: CLI -> services -> (models/domain) -> infra (excel/db/logging/util). Lower layers must not import higher.
- Domain models in `src/models/` provide type-safe dataclasses for configuration, processing results, and workflow entities.
- Services in `src/services/` coordinate cross-cutting concerns (orchestration, progress, metrics, FK relationships).

## Error Log Schema
Keys: `timestamp`, `file`, `sheet`, `row`, `error_type`, `db_message` (no extras). `timestamp` UTC ISO8601 `...Z`.

## SUMMARY Regex (for reference)
```
^SUMMARY\s+files=([0-9]+)/(\1)\s+success=([0-9]+)\s+failed=([0-9]+)\s+rows=([0-9]+)\s+skipped_sheets=([0-9]+)\s+elapsed_sec=([0-9]+\.?[0-9]*)\s+throughput_rps=([0-9]+\.?[0-9]*)$
```

## Guardrails
- Do not prematurely implement COPY path or parallelization.
- Avoid leaking DB credentials; rely on env precedence (FR-027).
- Preserve high (>90%) coverage; expand tests with each new feature.

_Last updated: 2025-10-06 (Phase 4 implementation complete)_
