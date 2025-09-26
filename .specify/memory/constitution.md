<!--
Sync Impact Report
Version change: 0.0.0 → 1.0.0
Modified principles: Initial adoption
Added sections: Quality Gates & Metrics; Delivery Workflow
Removed sections: Placeholder principle slots beyond IV
Templates requiring updates:
- ✅ .specify/templates/plan-template.md
- ✅ .specify/templates/spec-template.md
- ✅ .specify/templates/tasks-template.md
Follow-up TODOs: None
-->
# IWK DB Import Constitution

## Core Principles

### I. Code Quality Baseline
- All contributions MUST pass automated formatting, linting, and static analysis gates configured for the repository before review.
- Code reviews MUST confirm readability, testability, and adherence to domain style guides; reviewers SHALL block merges when quality signals regress.
- New dependencies MAY be introduced only with documented justification covering maintenance burden and security posture.
Rationale: A disciplined codebase reduces regression risk and keeps the importer maintainable for long-lived data pipelines.

### II. Test-First Delivery
- Every change MUST begin with failing automated tests that capture intended behaviour before implementation proceeds.
- The default branch MUST maintain ≥90% statement coverage across critical paths (ingest pipelines, schema transforms, CLI entry points) and never drop more than 1% per pull request.
- CI pipelines MUST execute unit, integration, and contract suites on every merge request; red pipelines block release until resolved.
Rationale: Test-first execution secures correctness of ETL flows and keeps data migrations auditable.

### III. Consistent User Experience
- User-facing surfaces (CLI, API, docs) MUST share consistent command verbs, option names, output formatting, and error semantics across features.
- User workflows MUST document expected latency, progress indicators, fallback behaviour, and recovery guidance when imports fail.
- All user-visible changes MUST include updated quickstart examples and help text before release.
Rationale: A predictable experience enables operators to run imports confidently under time pressure.

### IV. Performance & Capacity Discipline
- Features MUST define explicit throughput, latency, and resource ceilings and capture them in specs before implementation begins.
- Performance tests measuring representative workloads MUST run at least on pre-merge branches and demonstrate adherence to published budgets.
- Instrumentation (metrics, structured logs) MUST exist for every critical path to detect drift from performance commitments.
Rationale: Import jobs often run on shared infrastructure; tight budgets prevent backlog spikes and service degradation.

## Quality Gates & Metrics
- Maintain a green CI baseline with static analysis, unit, integration, contract, and performance suites; any regression blocks merge.
- Enforce code ownership for critical importer modules; changes without appropriate reviewers are invalid.
- Capture and publish key health metrics (test coverage, defect escape rate, performance headroom) in release notes.
- Documentation updates MUST accompany any user workflow or performance commitment change to keep runbooks accurate.

## Delivery Workflow
1. Draft specs capturing functional scope, UX narratives, test strategy, and performance budgets before planning.
2. Run constitution alignment review during planning to confirm design satisfies all four Core Principles and Quality Gates.
3. Execute development with TDD, maintaining failing tests until implementation passes; commit instrumentation alongside feature code.
4. Perform regression, performance, and UX verification prior to release, updating documentation and support playbooks.
5. Post-release, monitor metrics for two full import cycles and log compliance outcomes.

## Governance
- Amendments require consensus from technical leads, QA leads, and operations maintainers, plus documented impact analysis.
- Versioning follows semantic rules: MAJOR for principle overhaul, MINOR for new guidance, PATCH for clarifications.
- Compliance reviews occur at the end of each release train; violations trigger action items tracked to closure.
- Store ratified constitutions under version control; superseded versions remain accessible for audit.

**Version**: 1.0.0 | **Ratified**: 2025-09-26 | **Last Amended**: 2025-09-26