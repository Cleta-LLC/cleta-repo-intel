# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

### Added
- Schema `0.2` evidence records for commits, reconstructed change items, and changed files.
- Evidence-linked semantic release themes.
- Release-character classification such as feature delivery, stabilization, and cross-layer hardening.
- Risk, assurance, scope, process, and evidence findings with explicit confidence and supporting evidence IDs.
- Conservative repeated-change-item detection as a rework/iteration signal.
- Executive release narrative derived from deterministic repository evidence.
- Self-contained HTML release-intelligence report.
- CLI `--format html` and `--format all`; `all` is now the default while `both` remains JSON + Markdown.

### Changed
- Roadmap prioritizes semantic release intelligence before remote/fleet ingestion.
- Markdown reports now lead with release intelligence before raw engineering metrics.

## [0.1.0] - Unreleased

### Added
- Local Git repository snapshots between arbitrary refs.
- Markdown and JSON report output.
- Conventional change-item reconstruction for squash-compressed histories.
- Engineering-footprint sizing based on reconstructed change volume, files, and churn.
- Separate delivery-complexity scoring with explicit reasons for database/schema, configuration, and cross-layer changes.
- File-surface, major-area, test, documentation, database, and CI/config signals.
- Python 3.12+ CI coverage.
