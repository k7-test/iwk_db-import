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

## Current Implementation Status (Post Phase 1)
Implemented scaffolds:
- Config loader (`src/config/loader.py`) basic required key validation + default timezone.
- Error log buffer & `ErrorRecord` (JSON serialization) (`src/logging/error_log.py`).
- Excel reader & normalization (`src/excel/reader.py`) with header & expected column checks.
- Batch insert abstraction (`src/db/batch_insert.py`) + tests (execute_values monkeypatched).
- Minimal CLI (`src/cli/__main__.py`) success + start-up failure exit codes (0/1) and SUMMARY zero-file template.
- Contract tests: exit codes (partial), summary regex, error log schema.
- Perf smoke placeholder.

Pending (Phase 2 tasks):
1. Orchestration service layer (file scan → sheet normalization → DB insert → metrics → error flush).
2. Partial failure handling (exit code 2) + enabling skipped contract test.
3. Metrics & SUMMARY field population (rows, elapsed_sec, throughput_rps, skipped_sheets real values).
4. FK propagation + conditional RETURNING.
5. Logging initialization with labeled lines (INFO/WARN/ERROR/SUMMARY) and progress output.
6. Config schema contract test (root keys & structure) — to be added.
7. Integration & performance tests with real DB / fixtures.
8. Batch size tuning instrumentation.
9. Enhanced error scenarios (sheet-level fatal, row=-1 sentinel) & ErrorRecord extension if needed.

## Coding Conventions
- Python 3.11, type hints strict (`mypy --strict`).
- Lint: ruff (line length 100). Keep new dependencies justified in `DECISIONS.md` first.
- Tests first: add / update failing tests before implementation changes.
- Keep layers acyclic: CLI -> services -> (models/domain) -> infra (excel/db/logging/util). Lower layers must not import higher.

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

_Last updated: 2025-09-26_
