# Testing Guidelines

## Directory structure

Tests live in the root `tests/` directory. Mirror the `src/docproc/` module structure with subdirectories:

```
src/docproc/
    pipeline/
        ocr.py
        vision.py
    config.py

tests/
    pipeline/
        test_pipeline_ocr.py
        test_pipeline_vision.py
    test_config.py
```

## File naming

Each source module gets its own test file named `test_{module_directory}_{module_name}.py`. For top-level modules (no subdirectory), use `test_{module_name}.py`.

## Test style

Use plain pytest functions — no test classes.

```python
# Good
def test_load_config_returns_defaults_when_file_missing():
    ...

# Bad
class TestLoadConfig:
    def test_returns_defaults_when_file_missing(self):
        ...
```

## Test naming

Name tests `test_{method_name}_{reason_for_test}()`:

```python
def test_parse_date_raises_on_empty_string():
    ...

def test_classify_returns_common_when_no_tags_match():
    ...
```

## Mocking

Use `mock.patch` as a decorator. Name mock arguments `mock_{mocked_method}`:

```python
from unittest import mock

@mock.patch("docproc.pipeline.ocr.httpx.post")
def test_extract_text_returns_raw_content(mock_post):
    mock_post.return_value = mock.Mock(json=lambda: {"text": "hello"})
    result = extract_text("file.pdf")
    assert result == "hello"
```

## Assertions

Use `assert` directly instead of mock magic assert methods:

```python
# Good
assert mock_post.call_count == 1
assert mock_post.call_args[0][0] == "https://api.example.com/ocr"

# Bad
mock_post.assert_called_once()
mock_post.assert_called_with("https://api.example.com/ocr")
```

This makes assertion failures more readable — pytest shows the actual vs. expected values directly in the diff output.

## Parametrize

Use `pytest.mark.parametrize` to cover multiple inputs:

```python
import pytest

@pytest.mark.parametrize("input_ext,expected", [
    (".pdf", "application/pdf"),
    (".png", "image/png"),
    (".jpg", "image/jpeg"),
])
def test_detect_mime_type_from_extension(input_ext, expected):
    assert detect_mime_type(f"file{input_ext}") == expected
```
