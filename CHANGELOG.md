# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.3] - 2026-02-27

### Added
- `src/docproc/models.py` — Pydantic data models for the processing pipeline
- Models: ProcessingJob, PageText, OCRResult, VisionResult, ReconciledDocument, Classification, ProcessedDocument
- Date parsing helper supporting ISO, European, and dot-separated formats
- Full test suite for all models (~25 tests)

## [0.1.2] - 2026-02-27

### Added
- `config-example.yaml` with example project configuration (`config.yaml` is gitignored)
- `src/docproc/config.py` — typed configuration loader with Pydantic models
- Environment variable substitution (`${VAR}`) with dotenv support
- Path resolution against project root
- Singleton caching for configuration
- Configuration validation (watch dir exists, recipients non-empty, API key set)

## [0.1.1] - 2026-02-27

### Added
- Project bootstrapped with `pyproject.toml` and hatchling build system
- `src/docproc` package with version string
- `inbox/` and `output/` directories
- Dev tooling: pytest, ruff, ty, pytest-cov
- CHANGELOG.md

### Changed
- CLAUDE.md workflow references from GitLab to GitHub

## [0.1.0] - 2026-02-27

### Added
- Initial project plan and task breakdown (PLAN.md, tasks/)
- CLAUDE.md with project guidance
- README.md
