# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PaperRoute** — a document processing daemon that watches an inbox directory, extracts content via parallel OCR + Vision LLM, reconciles and classifies documents by recipient/category, saves organized markdown output, and indexes into a RAG system for chat-based retrieval.

## Commands

```bash
uv sync                              # Install dependencies
uv run pytest                        # Run tests (coverage must stay ≥80%)
uv run ruff check src/ tests/        # Lint
uv run ruff format --check src/ tests/ # Check formatting
uv run ruff format src/ tests/        # Auto-fix formatting
uv run ty check src/                 # Type check
uv run python -m docproc.watcher     # Start the watcher daemon
uv run python chat/app.py            # Start the Gradio chat frontend (port 7860)
```

## Architecture

The system is a pipeline triggered by filesystem events:

```
inbox/ (new file) → OCR + Vision (parallel) → Reconciler → Classifier → File Mover → RAG Indexer
```

All LLM/OCR calls go through DeepFellow's OpenAI-compatible API (`base_url` in config.yaml). There are two distinct models: a vision model for image extraction and an LLM (deepseek) for text tasks (reconciliation, classification). The chat frontend uses a separate `/v1/responses` endpoint for RAG-enabled queries.

### Key design decisions

- **OCR is remote** — via DeepFellow easyOCR API. No local Tesseract/poppler/pdf2image needed.
- **Dual extraction** — OCR (deterministic, accurate text) and Vision (structural understanding, tables) run in parallel, then an LLM reconciles them.
- **Recipients vs "Common"** — Recipients are configured with tag lists for matching. "Common" is the implicit fallback — it is NOT a configured recipient.
- **Dynamic categories** — Categories (e.g., "invoices", "medical") are NOT predefined. The LLM determines them from document content.
- **RAG indexing is non-blocking** — Failures don't stop the processing pipeline.

### Output structure

```
output/{recipient}/{category}/{date}-{subject}.md      # Reconciled markdown with YAML frontmatter
output/{recipient}/{category}/{date}-{subject}.pdf      # Original file copy
```

### Data flow through Pydantic models

```
ProcessingJob → OCRResult + VisionResult → ReconciledDocument → Classification → ProcessedDocument
```

## Configuration

`config.yaml` at project root. Supports `${ENV_VAR}` substitution. Relative paths resolve against project root, not CWD.

## Workflow

When working on a task, always create a GitHub issue and a pull request (PR) before starting implementation. Use `gh` CLI for this.

### Versioning
- Version follows `0.1.x` during initial development. Bump the patch version in both `pyproject.toml` and `src/docproc/__init__.py` after each task.
- Update `CHANGELOG.md` (Keep a Changelog format) with every task.

### Testing
See [`docs/TESTING.md`](docs/TESTING.md) for full conventions. Key rules: pytest functions (no classes), `mock.patch` decorator, `assert` directly (never magic assert methods), `pytest.mark.parametrize` for multiple inputs.

### Quality gates
- Test coverage must stay at or above **80%** (`--cov-fail-under=80`).
- `ruff check` and `ruff format --check` must pass with no errors.
- `ty check` must pass with no errors.

## Task breakdown

Detailed implementation specs for each component live in `tasks/01-*.md` through `tasks/12-*.md`. Read the relevant task file before implementing a component.
