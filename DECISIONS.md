# Architectural & Technical Decisions (Phase 0 / Phase 1)

This document records the finalized decisions referenced by the Constitution (dependency / approach justification). Acts as a concise, versioned changelog of design intent. For detailed analysis see `specs/001-excel-postgressql-excel/research.md`.

| ID | Topic | Decision | Key Rationale | FR/QR Impact | Revisit Trigger |
|----|-------|----------|---------------|--------------|-----------------|
| R-001 | INSERT Strategy | Use `psycopg2.extras.execute_values` | Achieves ≥800 rows/sec target with low complexity; granular error diagnostics acceptable at batch level | FR-022, QR-004/005 | Throughput < target in perf tests |
| R-002 | Logging | Standard `logging` (no loguru) | Avoid extra dependency; custom formatter sufficient for JSON lines + label control | QR-003, QR-007, FR-030 | Structured logging needs >1 sink/rotation complexity |
| R-003 | Progress Display | Single `tqdm` instance (disable in non-TTY) | Rapid implementation, minimal noise, meets QR-008 diff update requirement | QR-008 | CI noise / formatting issues |
| R-004 | dtype Optimization | `convert_dtypes()` + numeric downcast; defer category unless >70% repetition | Memory reduction without premature schema config complexity | QR-006 | Peak memory >512MB |
| R-005 | Error Log Flush | In‑memory list → flush once per file (finally) | Simplicity; worst-case memory ~8MB at 50k errors manageable | FR-030, QR-009 | Error volume >> estimates / memory pressure |
| R-006 | Batch Size | Default 1000 rows | Balance network round trips vs memory; practical literature baseline | QR-004/005 | Perf profiling suggests alternative superior |
| R-007 | RETURNING Usage | Only when FK propagation requires parent PK | Minimizes round-trip & result materialization | FR-029 | Multi-parent dependency or child needs additional generated columns |

## Traceability
- Source: `research.md` (detailed alternatives & rationale)
- Referenced by: `plan.md` Technical Context & Constitution Code Quality Baseline (dependency justification)

## Change Management
Any change to a decision requires:
1. Update this table (append new row with incremented revision if altering an existing topic)
2. Link to performance / correctness evidence (benchmark snippet, failing test rationale, etc.)
3. Update affected contract tests / documentation.

## Open (Future) Decisions Candidates
| Candidate | Why Deferred |
|-----------|--------------|
| COPY protocol fast path | Need baseline perf & error handling abstraction first |
| Parallel file processing | Memory & transactional isolation trade-offs unvalidated |
| Config-driven explicit dtypes | Avoid premature complexity before profiling real datasets |

---
_Last updated: 2025-09-26_
