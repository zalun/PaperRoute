# Task 12: Testing & Verification

## Status: Pending

## Summary

Verify the entire system works end-to-end: drop a document into `inbox/`, confirm it gets processed, classified, saved, and indexed, then query it through the chat frontend.

## Details

### Unit Test Strategy

Test each component in isolation:

1. **Config loading** (`config.py`):
   - Load a sample config.yaml
   - Verify environment variable substitution
   - Verify path resolution
   - Verify recipients parsing

2. **Models** (`models.py`):
   - Validate model creation with valid data
   - Verify validation errors on invalid data
   - Test serialization/deserialization

3. **OCR** (`ocr.py`):
   - Mock the DeepFellow API response
   - Verify `OCRResult` construction
   - Test error handling (API down, timeout)

4. **Vision** (`vision.py`):
   - Mock the OpenAI-compatible API
   - Verify image encoding
   - Verify `VisionResult` construction
   - Test multi-page handling

5. **Reconciler** (`reconciler.py`):
   - Mock the LLM API
   - Test both-sources, OCR-only, Vision-only scenarios
   - Verify date extraction

6. **Classifier** (`classifier.py`):
   - Mock the LLM API
   - Test recipient matching with tags
   - Test "Common" fallback
   - Verify classification output format

7. **RAG Indexer** (`rag.py`):
   - Mock the RAG API
   - Test index, update, delete
   - Test metadata correctness

8. **Watcher** (`watcher.py`):
   - Test file type filtering
   - Test debouncing logic
   - Test pipeline orchestration (mocked components)

### Integration Test

End-to-end test with a real document:

```bash
# 1. Start the daemon
uv run python -m docproc.watcher &

# 2. Drop a test PDF
cp test-documents/sample-invoice.pdf inbox/

# 3. Wait for processing (watch logs)
sleep 10

# 4. Verify output
ls output/*/                    # Check directory structure
cat output/*/*/*.md             # Check markdown content

# 5. Start chat and query
uv run python chat/app.py &
# Open browser to http://localhost:7860
# Select recipient, ask about the invoice
```

### Manual Verification Checklist

- [ ] `uv sync` — all dependencies install cleanly
- [ ] `uv run python -m docproc.watcher` — daemon starts, logs "Watching..."
- [ ] Copy PDF to `inbox/` — daemon detects it within seconds
- [ ] Logs show: OCR running, Vision running, Reconciling, Classifying, Saving, Indexing
- [ ] `output/` has correct directory structure: `{recipient}/{category}/{date}-{subject}.md`
- [ ] Markdown file has YAML frontmatter with correct metadata
- [ ] Markdown content is clean and well-formatted
- [ ] Original file is copied alongside markdown
- [ ] RAG indexing succeeds (check logs)
- [ ] `uv run python chat/app.py` — Gradio launches at port 7860
- [ ] Recipient dropdown shows configured recipients
- [ ] Querying about the document returns relevant answer
- [ ] Source citations shown in response
- [ ] Processing a second document works (daemon stays up)
- [ ] Processing an image (PNG/JPG) works
- [ ] Daemon handles graceful shutdown (Ctrl+C)

### Test Documents

Prepare test documents covering different scenarios:

1. **Simple invoice PDF** — clear text, one page, should match a recipient
2. **Multi-page letter** — tests multi-page OCR and Vision
3. **Scanned image** — PNG/JPG with printed text
4. **Table-heavy document** — tests Vision table extraction
5. **Unrelated document** — should classify as "Common"
6. **Non-English document** — tests language handling

### Error Scenarios to Test

- [ ] DeepFellow API is down — graceful degradation
- [ ] Invalid file type dropped — ignored with log message
- [ ] Empty file dropped — handled without crash
- [ ] Very large PDF (50+ pages) — processes without timeout
- [ ] Duplicate file dropped — not reprocessed
- [ ] Config missing required fields — clear error on startup

## Acceptance Criteria

- [ ] All unit tests pass
- [ ] End-to-end pipeline works for at least one document
- [ ] Chat frontend returns relevant answers
- [ ] Daemon runs stably without memory leaks
- [ ] Error scenarios don't crash the system

## Dependencies

- ALL previous tasks (01–11)
