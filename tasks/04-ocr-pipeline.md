# Task 04: OCR Pipeline (DeepFellow easyOCR)

## Status: Done (per PLAN.md)

## Summary

Implement the OCR extraction module that sends documents to DeepFellow's easyOCR API for deterministic text extraction. No local OCR installation required.

## Files to Create

- `/Users/piotrzalewa/Projects/PDF/src/docproc/ocr.py`

## Details

### Architecture

This module wraps DeepFellow's easyOCR API endpoint. It handles:

1. **File preparation**: Read the PDF/image file from disk.
2. **API call**: Send to DeepFellow easyOCR endpoint.
3. **Response parsing**: Convert raw API response into `OCRResult` model.
4. **Error handling**: Retries, timeouts, API errors.

### DeepFellow easyOCR Integration

- DeepFellow provides an easyOCR endpoint — no local Tesseract/poppler needed.
- The API accepts file uploads (PDF, PNG, JPG, etc.).
- Returns structured text with page-level breakdown.
- This is **deterministic** OCR — same input always produces same output (unlike LLM-based extraction).

### Key Implementation Points

1. **File type handling**:
   - PDFs: Send directly — the API handles multi-page extraction.
   - Images (PNG, JPG, TIFF): Send as-is.
   - Validate file type before sending.

2. **Page-level extraction**:
   - Parse response to create `PageText` objects per page.
   - Maintain page ordering.
   - Combine into full text as well.

3. **Async support**:
   - Use `httpx` or `aiohttp` for async HTTP calls.
   - OCR runs in parallel with Vision (see Task 05), so async is important.

4. **Error handling**:
   - Retry on transient failures (5xx, timeouts).
   - Log but don't crash on OCR failures — Vision can be the fallback.
   - Set reasonable timeout (OCR on large PDFs can be slow).

5. **Configuration**:
   - Read DeepFellow base URL and API key from config.
   - Endpoint path for easyOCR (may differ from LLM endpoint).

### Function Signature

```python
async def extract_text(file_path: Path, config: Config) -> OCRResult:
    """
    Extract text from a document using DeepFellow easyOCR.

    Args:
        file_path: Path to PDF or image file
        config: Application configuration

    Returns:
        OCRResult with extracted text and page breakdown

    Raises:
        OCRError: If extraction fails after retries
    """
```

### Supported File Types

- PDF (`.pdf`) — most common input
- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- TIFF (`.tiff`, `.tif`)

## Acceptance Criteria

- [ ] Can extract text from a PDF via DeepFellow easyOCR API
- [ ] Can extract text from image files (PNG, JPG)
- [ ] Returns structured `OCRResult` with page-level breakdown
- [ ] Handles API errors gracefully with retries
- [ ] Works async for parallel execution with Vision
- [ ] Logs extraction progress and any issues
- [ ] Unsupported file types raise a clear error

## Dependencies

- Task 01 (Project Setup)
- Task 02 (Configuration) — needs DeepFellow API settings
- Task 03 (Data Models) — needs `OCRResult`, `PageText`
