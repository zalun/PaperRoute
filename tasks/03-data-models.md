# Task 03: Pydantic Data Models

## Status: Done (per PLAN.md)

## Summary

Define all Pydantic models that flow through the processing pipeline. These models are the contract between every component.

## Files to Create

- `/Users/piotrzalewa/Projects/PDF/src/docproc/models.py`

## Details

### Models Required

#### 1. `ProcessingJob`
Represents a single document being processed through the pipeline.

```python
class ProcessingJob(BaseModel):
    file_path: Path                # Original file in doc-holder/
    file_type: str                 # "pdf", "png", "jpg", etc.
    created_at: datetime           # When processing started
    status: Literal["pending", "processing", "done", "failed"]
```

#### 2. `OCRResult`
Output from the easyOCR step.

```python
class OCRResult(BaseModel):
    text: str                      # Full extracted text
    pages: list[PageText]          # Text per page with page numbers
    confidence: float | None       # Overall OCR confidence if available
```

#### 3. `PageText`
Text content for a single page.

```python
class PageText(BaseModel):
    page_number: int
    text: str
```

#### 4. `VisionResult`
Output from the Vision model step.

```python
class VisionResult(BaseModel):
    content: str                   # Markdown-formatted extraction
    tables: list[str] | None      # Extracted tables as markdown
    structural_notes: str | None   # Layout/structure observations
```

#### 5. `ReconciledDocument`
Output from the reconciler — the merged, clean document.

```python
class ReconciledDocument(BaseModel):
    markdown: str                  # Final clean markdown content
    document_date: date | None     # Date extracted from content
    title: str | None              # Document title if identifiable
    language: str | None           # Detected language
```

#### 6. `Classification`
Output from the classifier.

```python
class Classification(BaseModel):
    recipient: str                 # Matched recipient name or "Common"
    category: str                  # LLM-determined category (e.g., "invoices")
    subject: str                   # Descriptive subject for filename
    confidence: float | None       # Classification confidence
    reasoning: str | None          # Why this classification was chosen
```

#### 7. `ProcessedDocument`
The final output combining everything.

```python
class ProcessedDocument(BaseModel):
    original_path: Path
    output_path: Path              # Where the .md was saved
    markdown: str
    classification: Classification
    document_date: date | None
    indexed: bool                  # Whether RAG indexing succeeded
    metadata: dict                 # Additional metadata for RAG
```

### Design Principles

- All models use Pydantic v2 (`BaseModel` from `pydantic`).
- Use `Path` from `pathlib` for file paths — not raw strings.
- Dates as `date` objects, not strings.
- Optional fields use `| None` syntax (Python 3.10+ union).
- Each pipeline stage takes the previous stage's model as input and produces its own.

### Data Flow

```
file detected → ProcessingJob
     ↓
OCR  → OCRResult
Vision → VisionResult
     ↓
Reconciler(OCRResult, VisionResult) → ReconciledDocument
     ↓
Classifier(ReconciledDocument) → Classification
     ↓
FileMover + RAGIndexer → ProcessedDocument
```

## Acceptance Criteria

- [ ] All models are importable: `from docproc.models import ProcessingJob, ...`
- [ ] Models validate correctly — invalid data raises `ValidationError`
- [ ] Models serialize to/from JSON cleanly
- [ ] Path fields accept both strings and Path objects
- [ ] Date fields parse common date formats

## Dependencies

- Task 01 (Project Setup) — needs pydantic installed
