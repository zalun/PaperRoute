# Task 06: LLM Reconciler

## Status: Done (per PLAN.md)

## Summary

Implement the reconciler that takes both OCR and Vision outputs and uses an LLM to merge them into a single, clean, authoritative markdown document. Also extracts the document date.

## Files to Create

- `src/docproc/reconciler.py`

## Details

### Purpose

OCR and Vision each have strengths and weaknesses:

| Aspect | OCR | Vision |
|--------|-----|--------|
| Raw text accuracy | High | Medium (may hallucinate) |
| Table understanding | Low | High |
| Structure/layout | Low | High |
| Determinism | Yes | No |
| Handwriting | Poor | Better |

The reconciler uses an LLM to intelligently merge both, producing a document that has:
- Accurate text from OCR
- Proper structure/tables from Vision
- A coherent, clean markdown output

### Key Implementation Points

1. **LLM call via OpenAI-compatible API**:
   - Model: `config.deepfellow.llm_model` (e.g., "deepseek")
   - NOT the vision model — this is a text-to-text task.
   - Use `openai.AsyncOpenAI` pointed at DeepFellow.

2. **Reconciliation prompt**:
   - Provide both OCR text and Vision markdown.
   - Instruct the LLM to:
     - Trust OCR for exact text (names, numbers, addresses).
     - Trust Vision for structure (tables, headers, sections).
     - Resolve any conflicts by preferring OCR for specific data.
     - Produce clean, well-formatted markdown.
   - Example prompt structure:
     ```
     You are reconciling two extractions of the same document.

     ## OCR Extraction (accurate text, poor structure):
     {ocr_text}

     ## Vision Extraction (good structure, may have text errors):
     {vision_markdown}

     Produce a final clean markdown document that:
     1. Uses exact text from OCR (especially names, numbers, dates, addresses)
     2. Uses structural formatting from Vision (tables, headers, lists)
     3. Resolves any conflicts by preferring OCR for specific data
     4. Is well-formatted, clean markdown

     Also extract the document date if present.
     ```

3. **Date extraction**:
   - The reconciler should identify and extract the document's date.
   - This could be a letter date, invoice date, statement date, etc.
   - Return as a `date` object in `ReconciledDocument`.
   - If no date found, set to `None`.

4. **Structured output**:
   - Consider using OpenAI's function calling / structured output to get:
     - `markdown`: The final document
     - `document_date`: Extracted date
     - `title`: Document title
     - `language`: Detected language

5. **Fallback behavior**:
   - If OCR failed but Vision succeeded: use Vision output directly.
   - If Vision failed but OCR succeeded: use OCR output with minimal formatting.
   - If both failed: raise error.

### Function Signature

```python
async def reconcile(
    ocr_result: OCRResult | None,
    vision_result: VisionResult | None,
    config: Config,
) -> ReconciledDocument:
    """
    Merge OCR and Vision extractions into a clean markdown document.

    Uses an LLM to intelligently combine the strengths of both
    extraction methods. Also extracts document date and title.

    Args:
        ocr_result: Text from OCR (may be None if OCR failed)
        vision_result: Content from Vision (may be None if Vision failed)
        config: Application configuration

    Returns:
        ReconciledDocument with clean markdown and extracted metadata

    Raises:
        ReconciliationError: If both inputs are None or LLM call fails
    """
```

### Edge Cases

- **Single source**: If only one extraction succeeded, pass it through with light formatting.
- **Empty document**: OCR returns empty text, Vision returns empty content → flag as unreadable.
- **Very long documents**: May need to chunk and reconcile page-by-page for token limit reasons.
- **Non-text documents**: Pure images (photos, diagrams) — Vision handles, OCR returns nothing.

## Acceptance Criteria

- [ ] Merges OCR and Vision outputs into clean markdown
- [ ] Extracts document date when present
- [ ] Extracts document title when identifiable
- [ ] Handles single-source fallback (only OCR or only Vision)
- [ ] Returns structured `ReconciledDocument`
- [ ] LLM call uses the configured `llm_model` (deepseek)
- [ ] Works async
- [ ] Handles token limits for large documents

## Dependencies

- Task 01 (Project Setup) — needs `openai` library
- Task 02 (Configuration) — needs DeepFellow LLM settings
- Task 03 (Data Models) — needs `OCRResult`, `VisionResult`, `ReconciledDocument`
- Task 04 (OCR) — produces input `OCRResult`
- Task 05 (Vision) — produces input `VisionResult`
