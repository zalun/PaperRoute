# Task 09: Directory Watcher Daemon

## Status: Done (per PLAN.md)

## Summary

Implement the filesystem watcher daemon that monitors the `inbox/` directory for new files and orchestrates the full processing pipeline. This is the main entry point of the system.

## Files to Create

- `src/docproc/watcher.py`

## Details

### Architecture

The watcher is the **orchestrator** — it ties all components together:

```
File detected → OCR + Vision (parallel) → Reconciler → Classifier → File Mover → RAG Indexer
```

It uses the `watchdog` library to monitor the filesystem and triggers the pipeline for each new file.

### Key Implementation Points

1. **Watchdog setup**:
   ```python
   from watchdog.observers import Observer
   from watchdog.events import FileSystemEventHandler

   class DocumentHandler(FileSystemEventHandler):
       def on_created(self, event):
           if not event.is_directory:
               asyncio.run(process_file(Path(event.src_path)))
   ```

2. **File type detection**:
   - Accept: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif`
   - Ignore: `.tmp`, `.part`, partial downloads, hidden files (`.DS_Store`)
   - Validate file type before entering pipeline.

3. **File locking / deduplication**:
   - Files may trigger multiple events (created, modified as write completes).
   - Implement debouncing: wait for file to stabilize (no size change for N seconds).
   - Track processed files to avoid re-processing.
   - Options: in-memory set, or a `.processed` marker file.

4. **Pipeline orchestration**:
   ```python
   async def process_file(file_path: Path, config: Config):
       # 1. Create processing job
       job = ProcessingJob(file_path=file_path, ...)

       # 2. Run OCR and Vision in parallel
       ocr_result, vision_result = await asyncio.gather(
           extract_text(file_path, config),
           extract_with_vision(file_path, config),
           return_exceptions=True,
       )

       # 3. Reconcile
       document = await reconcile(ocr_result, vision_result, config)

       # 4. Classify
       classification = await classify(document, config)

       # 5. Save output file
       output_path = save_document(document, classification, config)

       # 6. Index into RAG
       indexed = await index_document(processed_doc, config)
   ```

5. **Output file saving**:
   - Create directory structure: `output/{recipient}/{category}/`
   - Save as: `{date}-{subject}.md`
   - Also copy/move the original file alongside the markdown.
   - Handle filename collisions (append counter).

6. **Daemon mode**:
   - Run as a long-running process.
   - Entry point: `uv run python -m docproc.watcher`
   - Handle SIGINT/SIGTERM gracefully.
   - Log pipeline progress for each file.

7. **Error handling per file**:
   - One file's failure should NOT crash the daemon.
   - Catch exceptions per-file, log errors, continue watching.
   - Consider moving failed files to an `errors/` directory.

### Main Entry Point

```python
def main():
    config = load_config()

    handler = DocumentHandler(config)
    observer = Observer()
    observer.schedule(handler, str(config.directories.watch), recursive=False)
    observer.start()

    logger.info(f"Watching {config.directories.watch} for new documents...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

if __name__ == "__main__":
    main()
```

### File Debouncing Strategy

```python
import time

DEBOUNCE_SECONDS = 2

def is_file_stable(file_path: Path) -> bool:
    """Wait until file size stops changing."""
    size1 = file_path.stat().st_size
    time.sleep(DEBOUNCE_SECONDS)
    size2 = file_path.stat().st_size
    return size1 == size2 and size2 > 0
```

### Output Directory Structure

```
output/
├── Piotr Zalewa/
│   ├── invoices/
│   │   ├── 2025-01-15-reef-tank-supplies.md
│   │   └── 2025-01-15-reef-tank-supplies.pdf  (original)
│   └── insurance/
│       └── 2025-02-01-home-policy-renewal.md
└── Common/
    ├── tax/
    │   └── 2025-01-31-annual-tax-return.md
    └── utilities/
        └── 2025-01-20-electricity-bill.md
```

## Acceptance Criteria

- [ ] Detects new files in `inbox/` directory in real-time
- [ ] Filters by supported file types (PDF, PNG, JPG, TIFF)
- [ ] Ignores temp files, hidden files, and partial downloads
- [ ] Debounces file events to avoid processing incomplete files
- [ ] Runs OCR and Vision in parallel
- [ ] Orchestrates full pipeline: OCR → Vision → Reconcile → Classify → Save → Index
- [ ] Saves output markdown to correct directory structure
- [ ] Copies original file alongside output
- [ ] Handles filename collisions
- [ ] One file's failure doesn't crash the daemon
- [ ] Graceful shutdown on SIGINT/SIGTERM
- [ ] Prevents duplicate processing of same file
- [ ] Runs as: `uv run python -m docproc.watcher`

## Dependencies

- Task 01 (Project Setup) — needs `watchdog` library
- Task 02 (Configuration) — needs directory paths
- Task 03 (Data Models) — needs all models
- Task 04 (OCR) — pipeline step
- Task 05 (Vision) — pipeline step
- Task 06 (Reconciler) — pipeline step
- Task 07 (Classifier) — pipeline step
- Task 08 (RAG Indexer) — pipeline step
