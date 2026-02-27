# Document Processing & RAG System Plan

## Overview

A document processing daemon that watches a directory, extracts content via OCR + Vision, categorizes by recipient/subject, and indexes into a RAG system for chat-based retrieval.

## Technology Stack

- **Python 3.14** with **uv** package manager
- **OpenAI API** (local model via DeepFellow)
- **DeepFellow** for RAG and LLM API
- **watchdog** for filesystem monitoring
- **DeepFellow easyOCR** for deterministic OCR (no local installation needed)
- **Gradio** for chat frontend (with recipient selection)

## Project Structure

```
PaperRoute/
├── pyproject.toml
├── config.yaml                         # Recipients, tags, directories
├── src/
│   └── docproc/
│       ├── __init__.py
│       ├── watcher.py                  # Directory watcher daemon
│       ├── ocr.py                      # DeepFellow easyOCR processing
│       ├── vision.py                   # Vision model extraction
│       ├── reconciler.py               # LLM reconciliation of OCR + Vision
│       ├── classifier.py               # Recipient/subject classification
│       ├── rag.py                      # RAG indexing client
│       ├── config.py                   # Configuration loader
│       └── models.py                   # Pydantic models
├── chat/
│   └── app.py                          # Chat frontend
├── inbox/                              # Input: watched directory
└── output/                             # Output: organized documents
    └── {recipient}/{category}/{date}-{subject}.md
```

## Configuration Schema (config.yaml)

```yaml
directories:
  watch: "./inbox"
  output: "./output"

deepfellow:
  base_url: "http://localhost:8000/v1"  # OpenAI-compatible endpoint
  responses_endpoint: "/v1/responses"   # RAG-enabled responses
  api_key: "${DEEPFELLOW_API_KEY}"
  vision_model: "gpt-4-vision"          # For image/PDF extraction
  llm_model: "deepseek"                 # For reconciliation & classification
  rag_collection: "documents"

recipients:
  - name: "Piotr Zalewa"
    tags: ["aquarium", "fish", "reef"]
  # No "Common" - it's the automatic fallback when no recipient matches
  # Categories are determined dynamically by LLM from document context
```

## Component Details

### 1. Watcher Daemon (`watcher.py`)

- Uses `watchdog` library to monitor `inbox/` directory
- Triggers processing pipeline on new PDF/image files
- Handles file locking to prevent duplicate processing
- Runs as a daemon (can be managed via systemd or supervisor)

### 2. OCR Pipeline (`ocr.py`)

- Uses DeepFellow's easyOCR API for deterministic text extraction
- No local OCR installation required
- Returns structured text with page numbers

### 3. Vision Extraction (`vision.py`)

- Sends images to Vision model via OpenAI-compatible API
- Extracts text, tables, and structural information
- Returns markdown-formatted content

### 4. Reconciler (`reconciler.py`)

- Receives both OCR and Vision outputs
- Uses LLM to merge/reconcile discrepancies
- Produces final clean Markdown document
- Extracts date from document content

### 5. Classifier (`classifier.py`)

- Analyzes document content via LLM (deepseek)
- Matches content against recipient tags from config
- Falls back to "Common" if no recipient tags match
- Determines category dynamically from document context (not predefined)
- Generates descriptive filename/subject

### 6. RAG Indexer (`rag.py`)

- Indexes final Markdown into DeepFellow RAG
- Includes metadata (recipient, category, date, original filename)
- Supports document updates/deletions

### 7. Chat Frontend (`chat/app.py`)

- Gradio interface with recipient selector dropdown
- User selects their recipient (e.g., "Piotr Zalewa")
- Queries RAG filtered by selected recipient's documents
- Displays responses with source citations
- Uses `/v1/responses` endpoint for RAG-enabled queries

## Processing Flow

```
┌─────────────────┐
│  inbox/         │  ← New file detected
│  (input)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  1. File Type   │
│     Detection   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌───────┐
│  OCR  │  │Vision │  ← Run in parallel
└───┬───┘  └───┬───┘
    │          │
    └────┬─────┘
         │
         ▼
┌─────────────────┐
│ 2. Reconciler   │  ← LLM merges both outputs
│    (LLM)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Classifier   │  ← Determines recipient + category
│    (LLM)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. File Mover   │  ← Saves .md + original to output/
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. RAG Indexer  │  ← Indexes into DeepFellow
└─────────────────┘
```

## Dependencies (pyproject.toml)

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
# Note: OCR via DeepFellow API - no local pytesseract/pdf2image needed
```

## Files to Create

1. `pyproject.toml` - Project configuration
2. `config.yaml` - Runtime configuration
3. `src/docproc/__init__.py` - Package init
4. `src/docproc/models.py` - Pydantic data models
5. `src/docproc/config.py` - Configuration loader
6. `src/docproc/ocr.py` - OCR processing
7. `src/docproc/vision.py` - Vision model client
8. `src/docproc/reconciler.py` - LLM reconciliation
9. `src/docproc/classifier.py` - Recipient/category classification
10. `src/docproc/rag.py` - RAG indexing
11. `src/docproc/watcher.py` - Directory watcher daemon
12. `chat/app.py` - Chat frontend

## Verification

1. **Unit tests**: Drop test PDF into `inbox/`, verify output structure
2. **Integration test**: Process document end-to-end, query via chat
3. **Manual verification**:
   - `uv run python -m docproc.watcher` - Start daemon
   - Copy a PDF to `inbox/`
   - Check `output/` for organized files
   - `uv run python chat/app.py` - Start chat, query about document

## Decisions Made

- **Chat Framework**: Gradio
- **Chat Scope**: Filter by recipient (user selects their recipient)
- **RAG API**: OpenAI-compatible `/v1/responses` endpoint

## Implementation Progress

- [x] `pyproject.toml`
- [x] `config.yaml`
- [x] `src/docproc/__init__.py`
- [x] `src/docproc/models.py`
- [x] `src/docproc/config.py`
- [x] `src/docproc/ocr.py`
- [x] `src/docproc/vision.py`
- [x] `src/docproc/reconciler.py`
- [x] `src/docproc/classifier.py`
- [x] `src/docproc/rag.py`
- [x] `src/docproc/watcher.py`
- [x] `chat/app.py`
