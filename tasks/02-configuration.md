# Task 02: Configuration System

## Status: Done (per PLAN.md)

## Summary

Create `config.yaml` and the `config.py` loader that reads it, supports environment variable substitution, and provides typed access to all settings.

## Files to Create

- `/Users/piotrzalewa/Projects/PDF/config.yaml`
- `/Users/piotrzalewa/Projects/PDF/src/docproc/config.py`

## Details

### config.yaml Schema

```yaml
directories:
  watch: "./doc-holder"
  output: "./output"

deepfellow:
  base_url: "http://localhost:8000/v1"    # OpenAI-compatible endpoint
  responses_endpoint: "/v1/responses"     # RAG-enabled responses
  api_key: "${DEEPFELLOW_API_KEY}"        # Environment variable substitution
  vision_model: "gpt-4-vision"            # For image/PDF extraction
  llm_model: "deepseek"                   # For reconciliation & classification
  rag_collection: "documents"

recipients:
  - name: "Piotr Zalewa"
    tags: ["aquarium", "fish", "reef"]
  # No "Common" entry — it's the automatic fallback when no recipient matches
  # Categories are NOT predefined — LLM determines them dynamically
```

### config.py Implementation Details

1. **Environment variable substitution**: Parse `${VAR_NAME}` patterns in string values and replace with `os.environ` lookups. Use `python-dotenv` to load `.env` file if present.

2. **Path resolution**: Resolve relative paths (`./doc-holder`) against the project root, not CWD.

3. **Typed config object**: Use Pydantic models or a dataclass to provide typed access:
   ```python
   config.directories.watch  # Path object
   config.deepfellow.base_url  # str
   config.recipients  # list[Recipient]
   ```

4. **Validation**: Fail early if:
   - Watch directory doesn't exist
   - Required API keys are missing
   - Recipients list is empty

5. **Singleton pattern**: Load config once, reuse across modules.

### Recipients Design

- Each recipient has a `name` and `tags` list.
- Tags are keywords the classifier uses to match document content to a recipient.
- "Common" is NOT a configured recipient — it's the implicit fallback when no tags match.
- Categories (e.g., "invoices", "insurance") are NOT predefined — the LLM determines them dynamically from document content.

## Acceptance Criteria

- [ ] `config.yaml` is valid YAML and parseable
- [ ] Environment variables like `${DEEPFELLOW_API_KEY}` are substituted at load time
- [ ] Missing env vars raise a clear error message
- [ ] Relative paths resolve correctly regardless of CWD
- [ ] Config is accessible as typed Python objects
- [ ] Recipients are loaded with names and tags

## Dependencies

- Task 01 (Project Setup) — needs pyproject.toml for pydantic/pyyaml
