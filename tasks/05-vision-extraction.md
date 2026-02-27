# Task 05: Vision Model Extraction

## Status: Done (per PLAN.md)

## Summary

Implement the Vision model client that sends document images to a vision-capable LLM (via OpenAI-compatible API) for rich content extraction including text, tables, and structural information.

## Files to Create

- `src/docproc/vision.py`

## Details

### Architecture

Uses the OpenAI-compatible API provided by DeepFellow to send images to a vision model (e.g., `gpt-4-vision`). Unlike OCR which is deterministic, Vision extraction is LLM-based and can understand layout, context, tables, and relationships.

### Why Both OCR and Vision?

- **OCR** (Task 04): Deterministic, accurate character-level extraction. Good at raw text but misses structure.
- **Vision** (this task): Understands document layout, tables, headers, relationships. May hallucinate text but captures semantics.
- **Reconciler** (Task 06): Merges both for best-of-both-worlds output.

### Key Implementation Points

1. **PDF to image conversion**:
   - Vision models need images, not PDFs.
   - Convert PDF pages to images before sending.
   - Options: Use DeepFellow API for conversion, or use `pdf2image`/`pymupdf` locally.
   - Consider: PLAN says "no local installation needed" — prefer API-based conversion if available.

2. **OpenAI-compatible API call**:
   - Use the `openai` Python library pointed at DeepFellow's `base_url`.
   - Send image as base64-encoded content in the message.
   - Model: `config.deepfellow.vision_model` (e.g., "gpt-4-vision").

3. **Prompt engineering**:
   - Instruct the model to extract ALL text faithfully.
   - Ask for tables in markdown format.
   - Request structural observations (headers, sections, layout).
   - Ask for output in markdown format.
   - Example prompt:
     ```
     Extract all text content from this document image.
     Preserve the structure including headers, paragraphs, and lists.
     Format tables as markdown tables.
     Note any structural elements (letterhead, signatures, stamps).
     Output everything in clean markdown format.
     ```

4. **Multi-page handling**:
   - Process each page as a separate API call.
   - Combine results maintaining page order.
   - Consider sending multiple pages in one call if the model supports it.

5. **Async execution**:
   - Runs in parallel with OCR (both triggered by watcher).
   - Use `openai.AsyncOpenAI` client.

### Function Signature

```python
async def extract_with_vision(file_path: Path, config: Config) -> VisionResult:
    """
    Extract content from a document using a Vision LLM model.

    Converts PDF pages to images, sends each to the vision model,
    and returns structured markdown content.

    Args:
        file_path: Path to PDF or image file
        config: Application configuration

    Returns:
        VisionResult with markdown content, tables, and structural notes
    """
```

### Image Encoding

```python
import base64

def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
```

### API Call Pattern

```python
client = AsyncOpenAI(
    base_url=config.deepfellow.base_url,
    api_key=config.deepfellow.api_key,
)

response = await client.chat.completions.create(
    model=config.deepfellow.vision_model,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": EXTRACTION_PROMPT},
            {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{encoded_image}"
            }}
        ]
    }],
    max_tokens=4096,
)
```

## Acceptance Criteria

- [ ] Can send a PDF/image to the vision model and get markdown content back
- [ ] Multi-page PDFs are handled (each page processed)
- [ ] Tables are extracted as markdown tables
- [ ] Returns structured `VisionResult` model
- [ ] Works async for parallel execution with OCR
- [ ] Handles API errors, rate limits, and timeouts
- [ ] Prompt produces consistent, high-quality extraction

## Dependencies

- Task 01 (Project Setup) — needs `openai` library
- Task 02 (Configuration) — needs DeepFellow API settings, vision model name
- Task 03 (Data Models) — needs `VisionResult`
