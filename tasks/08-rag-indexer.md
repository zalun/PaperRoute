# Task 08: RAG Indexer

## Status: Done (per PLAN.md)

## Summary

Implement the RAG indexing client that stores processed documents into DeepFellow's RAG system, with metadata for filtering, and supports updates and deletions.

## Files to Create

- `/Users/piotrzalewa/Projects/PDF/src/docproc/rag.py`

## Details

### Architecture

After a document is processed, reconciled, and classified, the final markdown is indexed into DeepFellow's RAG system. This enables the chat frontend to query documents with semantic search.

### DeepFellow RAG Integration

- DeepFellow provides RAG capabilities through its API.
- Collection name: `config.deepfellow.rag_collection` (e.g., "documents").
- Documents are stored with metadata for filtering.

### Metadata Schema

Each indexed document includes metadata for filtering and display:

```python
metadata = {
    "recipient": "Piotr Zalewa",        # For filtering in chat
    "category": "invoices",              # Document category
    "document_date": "2025-01-15",       # Document date (ISO format)
    "original_filename": "scan_001.pdf", # Original uploaded filename
    "subject": "reef-tank-supplies",     # Generated subject
    "output_path": "output/Piotr Zalewa/invoices/2025-01-15-reef-tank-supplies.md",
    "indexed_at": "2025-01-15T10:30:00Z", # When indexing happened
}
```

### Key Implementation Points

1. **Index document**:
   - Send markdown content + metadata to DeepFellow RAG API.
   - Use the output file path or a hash as the document ID for deduplication.
   - Handle chunking if DeepFellow requires it (or let the API handle it).

2. **Update document**:
   - If a document is reprocessed, update the existing index entry.
   - Use document ID to match existing entries.

3. **Delete document**:
   - If a source file is removed, remove from RAG index.
   - The watcher daemon may trigger deletions.

4. **Recipient filtering**:
   - Metadata must include `recipient` so chat queries can filter by recipient.
   - This is critical for the chat frontend's recipient selector.

5. **Error handling**:
   - RAG indexing failure should NOT block the processing pipeline.
   - Log errors but still save the output file.
   - Mark `indexed: False` in `ProcessedDocument` if indexing fails.
   - Consider a retry queue for failed indexing.

### Function Signatures

```python
async def index_document(
    document: ProcessedDocument,
    config: Config,
) -> bool:
    """
    Index a processed document into DeepFellow RAG.

    Returns True if indexing succeeded, False otherwise.
    """

async def delete_document(
    document_id: str,
    config: Config,
) -> bool:
    """
    Remove a document from the RAG index.
    """

async def update_document(
    document: ProcessedDocument,
    config: Config,
) -> bool:
    """
    Update an existing document in the RAG index.
    Deletes old entry and re-indexes.
    """
```

### RAG Query (used by chat)

The chat frontend uses the `/v1/responses` endpoint for RAG-enabled queries. This endpoint:
- Accepts a query + optional filters (recipient).
- Searches the RAG collection.
- Returns an LLM response grounded in retrieved documents.
- Includes source citations.

```python
async def query_rag(
    query: str,
    recipient: str | None,
    config: Config,
) -> RAGResponse:
    """
    Query the RAG system with optional recipient filter.
    Used by the chat frontend.
    """
```

## Acceptance Criteria

- [ ] Can index a processed document with full metadata
- [ ] Supports document updates (reprocessing)
- [ ] Supports document deletion
- [ ] Metadata includes recipient for chat filtering
- [ ] Indexing failures don't block the processing pipeline
- [ ] Returns success/failure status
- [ ] Works async
- [ ] Query function supports recipient filtering

## Dependencies

- Task 01 (Project Setup) — needs `openai` library
- Task 02 (Configuration) — needs DeepFellow RAG settings
- Task 03 (Data Models) — needs `ProcessedDocument`
- Task 07 (Classifier) — classification metadata for indexing
