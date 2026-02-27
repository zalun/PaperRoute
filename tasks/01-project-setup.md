# Task 01: Project Setup

## Status: Done (per PLAN.md)

## Summary

Bootstrap the Python project with `uv`, create `pyproject.toml`, and establish the directory/package structure.

## Files to Create

- `/Users/piotrzalewa/Projects/PDF/pyproject.toml`
- `/Users/piotrzalewa/Projects/PDF/src/docproc/__init__.py`

## Details

### pyproject.toml

```toml
[project]
name = "docproc"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "watchdog>=4.0.0",
    "openai>=1.0.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "gradio>=4.0.0",
    "python-dotenv>=1.0.0",
]
```

Key decisions:
- **Python 3.14** minimum — uses latest language features.
- **uv** as package manager — fast, reliable, replaces pip/venv.
- **No local OCR dependencies** (no pytesseract, pdf2image, poppler) — OCR is handled by DeepFellow API remotely.

### Directory Structure

```
/Users/piotrzalewa/Projects/PDF/
├── pyproject.toml
├── config.yaml
├── src/
│   └── docproc/
│       ├── __init__.py
│       ├── watcher.py
│       ├── ocr.py
│       ├── vision.py
│       ├── reconciler.py
│       ├── classifier.py
│       ├── rag.py
│       ├── config.py
│       └── models.py
├── chat/
│   └── app.py
├── doc-holder/          # Input: watched directory (already exists)
└── output/              # Output: organized documents
    └── {recipient}/{category}/{date}-{subject}.md
```

### __init__.py

Should expose the main pipeline entry point and version string. Keep minimal — avoid circular imports.

## Acceptance Criteria

- [ ] `uv sync` succeeds without errors
- [ ] `uv run python -c "import docproc"` works
- [ ] All dependencies listed in pyproject.toml are resolvable
- [ ] `doc-holder/` and `output/` directories exist

## Dependencies

None — this is the foundation task.
