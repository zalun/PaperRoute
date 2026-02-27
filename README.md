# PaperRoute

A document processing daemon that watches a directory for new PDFs and images, extracts content via parallel OCR + Vision LLM, classifies documents by recipient and category, and indexes everything into a RAG system for chat-based retrieval.

## How it works

Drop a PDF or image into `inbox/` and PaperRoute will:

1. **Extract text** using both OCR (deterministic) and a Vision LLM (structural) in parallel
2. **Reconcile** the two extractions into a clean markdown document via LLM
3. **Classify** the document — matching it to a recipient based on configured tags, determining a category, and generating a descriptive subject
4. **Save** the markdown (with YAML frontmatter) and a copy of the original to `output/{recipient}/{category}/{date}-{subject}.md`
5. **Index** into a RAG system for semantic search

Then ask questions about your documents through a chat interface.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- [DeepFellow](https://deepfellow.com) instance (provides OCR, Vision, LLM, and RAG APIs)

## Quick start

```bash
# Install dependencies
uv sync

# Configure
cp config.yaml.example config.yaml  # Edit with your DeepFellow settings
export DEEPFELLOW_API_KEY=your-key

# Start the watcher daemon
uv run python -m docproc.watcher

# In another terminal, start the chat frontend
uv run python chat/app.py
```

Drop files into `inbox/` and query them at http://localhost:7860.

## Configuration

Edit `config.yaml`:

```yaml
directories:
  watch: "./inbox"
  output: "./output"

deepfellow:
  base_url: "http://localhost:8000/v1"
  api_key: "${DEEPFELLOW_API_KEY}"
  vision_model: "gpt-4-vision"
  llm_model: "deepseek"

recipients:
  - name: "Piotr Zalewa"
    tags: ["aquarium", "fish", "reef"]
```

Documents that don't match any recipient's tags are filed under "Common". Categories are not predefined — the LLM determines them from document content.

## Processing pipeline

```
inbox/ (new file)
  │
  ├─→ OCR (DeepFellow easyOCR) ──┐
  │                               ├─→ Reconciler (LLM) → Classifier (LLM) → Save + Index
  └─→ Vision (LLM) ──────────────┘
```

## Supported file types

- PDF (`.pdf`)
- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- TIFF (`.tiff`, `.tif`)

## License

[MIT](LICENSE)
