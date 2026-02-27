# Task 07: Recipient & Category Classifier

## Status: Done (per PLAN.md)

## Summary

Implement the classifier that analyzes reconciled document content via LLM to determine the recipient, category, and generate a descriptive subject/filename.

## Files to Create

- `src/docproc/classifier.py`

## Details

### Architecture

The classifier is a critical routing component. It determines:
1. **Who** the document belongs to (recipient)
2. **What** the document is about (category)
3. **How** to name the output file (subject)

All classification is done by the LLM — no hard-coded rules beyond recipient tag matching.

### Recipient Matching Logic

1. Load recipients and their tags from config:
   ```yaml
   recipients:
     - name: "Piotr Zalewa"
       tags: ["aquarium", "fish", "reef"]
   ```

2. Send document content + recipient/tag list to LLM.

3. LLM determines which recipient's tags best match the document content.

4. **Fallback to "Common"**: If no recipient's tags match, classify as "Common". "Common" is NOT a configured recipient — it's the implicit default.

### Category Determination

- Categories are **NOT predefined** in config.
- The LLM determines the category dynamically from document content.
- Examples of categories the LLM might generate:
  - "invoices", "insurance", "medical", "tax", "correspondence", "receipts", "contracts", "bank-statements"
- Category should be a short, lowercase, kebab-case string suitable for directory names.

### Subject Generation

- The LLM generates a short descriptive subject for the filename.
- Should be human-readable and capture the document's essence.
- Format: lowercase, kebab-case, no special characters.
- Examples: "water-bill-january", "annual-checkup-results", "reef-tank-supplies-order"

### LLM Prompt Design

```
Analyze this document and classify it.

## Document Content:
{reconciled_markdown}

## Available Recipients:
{for each recipient: name + tags}

## Instructions:
1. Determine which recipient this document belongs to based on their tags.
   If no recipient's tags match, use "Common".
2. Determine a short category for this document (e.g., "invoices", "medical", "insurance").
   Use lowercase kebab-case.
3. Generate a short descriptive subject suitable for a filename.
   Use lowercase kebab-case. No dates in the subject.

Respond in JSON format:
{
  "recipient": "Piotr Zalewa" or "Common",
  "category": "category-name",
  "subject": "descriptive-subject",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why this classification"
}
```

### Structured Output

Use OpenAI function calling or structured output to ensure the response matches `Classification` model:

```python
class Classification(BaseModel):
    recipient: str       # "Piotr Zalewa" or "Common"
    category: str        # LLM-determined, kebab-case
    subject: str         # Descriptive filename, kebab-case
    confidence: float | None
    reasoning: str | None
```

### Function Signature

```python
async def classify(
    document: ReconciledDocument,
    config: Config,
) -> Classification:
    """
    Classify a document by recipient, category, and subject.

    Uses LLM to match document content against recipient tags,
    determine a category, and generate a descriptive subject.

    Args:
        document: The reconciled document content
        config: Application configuration (includes recipients)

    Returns:
        Classification with recipient, category, subject
    """
```

### Output Path Construction

After classification, the output path is constructed as:
```
output/{recipient}/{category}/{date}-{subject}.md
```

Example:
```
output/Piotr Zalewa/invoices/2025-01-15-reef-tank-supplies.md
output/Common/insurance/2025-03-01-home-insurance-renewal.md
```

### Edge Cases

- **Ambiguous recipient**: Document matches multiple recipients' tags → LLM picks best match, logs reasoning.
- **No date in document**: Use file modification date or current date.
- **Very short documents**: May have low classification confidence — still classify, but log warning.
- **Non-English documents**: LLM should still be able to classify. Language detected in reconciler step.

## Acceptance Criteria

- [ ] Correctly matches documents to recipients based on tags
- [ ] Falls back to "Common" when no tags match
- [ ] Generates appropriate dynamic categories (not predefined)
- [ ] Produces kebab-case subjects suitable for filenames
- [ ] Returns structured `Classification` model
- [ ] Includes confidence score and reasoning
- [ ] Handles edge cases (ambiguous, short docs, no date)

## Dependencies

- Task 01 (Project Setup) — needs `openai` library
- Task 02 (Configuration) — needs recipients + tags, DeepFellow settings
- Task 03 (Data Models) — needs `ReconciledDocument`, `Classification`
- Task 06 (Reconciler) — produces input `ReconciledDocument`
