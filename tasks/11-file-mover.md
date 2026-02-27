# Task 11: File Mover / Output Manager

## Status: Implicit in watcher (Task 09)

## Summary

Implement the logic that saves the processed markdown document and the original file to the correct output directory structure based on classification results.

## Files

This logic lives within the watcher pipeline (Task 09) but is significant enough to document separately.

## Details

### Output Path Construction

```
output/{recipient}/{category}/{date}-{subject}.md
output/{recipient}/{category}/{date}-{subject}.{original_extension}
```

Examples:
```
output/Piotr Zalewa/invoices/2025-01-15-reef-tank-supplies.md
output/Piotr Zalewa/invoices/2025-01-15-reef-tank-supplies.pdf
output/Common/insurance/2025-03-01-home-insurance-renewal.md
output/Common/insurance/2025-03-01-home-insurance-renewal.pdf
```

### Key Implementation Points

1. **Directory creation**:
   - Create `output/{recipient}/{category}/` if it doesn't exist.
   - Use `Path.mkdir(parents=True, exist_ok=True)`.

2. **Filename construction**:
   - Format: `{date}-{subject}.md`
   - Date: from `ReconciledDocument.document_date` or fallback to today.
   - Subject: from `Classification.subject` (already kebab-case).
   - Sanitize: remove any characters unsafe for filenames.

3. **Collision handling**:
   - If file already exists, append a counter: `{date}-{subject}-2.md`
   - Don't silently overwrite.

4. **Save markdown**:
   - Write the reconciled markdown content to the `.md` file.
   - Include a YAML frontmatter header with metadata:
     ```markdown
     ---
     recipient: Piotr Zalewa
     category: invoices
     date: 2025-01-15
     subject: reef-tank-supplies
     original_file: scan_001.pdf
     processed_at: 2025-01-15T10:30:00Z
     ---

     # Reef Tank Supplies Invoice
     ...document content...
     ```

5. **Copy original file**:
   - Copy (not move) the original from `inbox/` to output alongside the `.md`.
   - Use same base name with original extension.
   - Consider: should originals be moved or copied? Copying is safer.

6. **Filename sanitization**:
   ```python
   import re

   def sanitize_filename(name: str) -> str:
       """Remove unsafe characters from filename."""
       name = re.sub(r'[^\w\s-]', '', name)
       name = re.sub(r'[-\s]+', '-', name).strip('-')
       return name.lower()
   ```

### Function Signature

```python
def save_document(
    reconciled: ReconciledDocument,
    classification: Classification,
    original_path: Path,
    config: Config,
) -> Path:
    """
    Save processed document to output directory.

    Creates directory structure, writes markdown with frontmatter,
    and copies the original file.

    Returns:
        Path to the saved markdown file
    """
```

## Acceptance Criteria

- [ ] Creates correct directory structure
- [ ] Saves markdown with YAML frontmatter metadata
- [ ] Copies original file alongside markdown
- [ ] Handles filename collisions with counter
- [ ] Sanitizes filenames
- [ ] Falls back to current date if document date is None

## Dependencies

- Task 03 (Data Models) — needs `ReconciledDocument`, `Classification`
- Task 06 (Reconciler) — produces markdown content
- Task 07 (Classifier) — produces classification for path
