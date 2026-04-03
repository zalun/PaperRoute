"""Tests for the Vision LLM extraction module."""

from unittest import mock

import pytest
from openai import APIConnectionError, APIStatusError

from docproc.config import Config
from docproc.vision import (
    VisionError,
    _call_vision_api,
    _encode_image,
    _pdf_to_images,
    _validate_file,
    extract_with_vision,
)


def _make_config(**overrides: str) -> Config:
    """Build a minimal frozen Config for testing."""
    deepfellow = {
        "base_url": "http://localhost:8000",
        "responses_endpoint": "/v1/responses",
        "ocr_endpoint": "/v1/ocr",
        "api_key": "test-key",
        "vision_model": "llama3.2-vision:11b",
        "llm_model": "deepseek",
        "rag_collection": "documents",
        **overrides,
    }
    return Config(
        directories={"watch": "/tmp/inbox", "output": "/tmp/output"},
        deepfellow=deepfellow,
        recipients=[{"name": "Test", "tags": ["t1"]}],
    )


def _mock_completion(content: str | None = "Extracted text"):
    """Build a mock ChatCompletion response."""
    message = mock.Mock()
    message.content = content
    choice = mock.Mock()
    choice.message = message
    response = mock.Mock()
    response.choices = [choice]
    return response


def _make_api_status_error(status_code: int, message: str = "error"):
    """Build a mock APIStatusError."""
    response = mock.Mock()
    response.status_code = status_code
    response.headers = {}
    return APIStatusError(
        message=message,
        response=response,
        body=None,
    )


# --- _validate_file ---


@pytest.mark.parametrize("ext", [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"])
def test_validate_file_accepts_supported_extensions(tmp_path, ext):
    f = tmp_path / f"doc{ext}"
    f.touch()
    _validate_file(f)  # should not raise


def test_validate_file_rejects_unsupported_extension(tmp_path):
    f = tmp_path / "doc.docx"
    f.touch()
    with pytest.raises(VisionError, match="Unsupported file type"):
        _validate_file(f)


def test_validate_file_rejects_missing_file(tmp_path):
    f = tmp_path / "missing.pdf"
    with pytest.raises(VisionError, match="File not found"):
        _validate_file(f)


@pytest.mark.parametrize("ext", [".PDF", ".Png", ".JPG"])
def test_validate_file_is_case_insensitive(tmp_path, ext):
    f = tmp_path / f"doc{ext}"
    f.touch()
    _validate_file(f)  # should not raise


# --- _pdf_to_images ---


@mock.patch("docproc.vision.pymupdf")
def test_pdf_to_images_renders_pages(mock_pymupdf, tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")

    mock_pix = mock.Mock()
    mock_pix.tobytes.return_value = b"png-bytes"
    mock_page = mock.Mock()
    mock_page.get_pixmap.return_value = mock_pix

    mock_doc = mock.MagicMock()
    mock_doc.__iter__ = mock.Mock(return_value=iter([mock_page, mock_page]))
    mock_pymupdf.open.return_value = mock_doc

    images = _pdf_to_images(pdf)

    assert len(images) == 2
    assert images[0] == b"png-bytes"
    assert mock_page.get_pixmap.call_args.kwargs["dpi"] == 150
    assert mock_doc.close.call_count == 1


@mock.patch("docproc.vision.pymupdf")
def test_pdf_to_images_raises_on_corrupt_file(mock_pymupdf, tmp_path):
    pdf = tmp_path / "corrupt.pdf"
    pdf.write_bytes(b"not-a-pdf")
    mock_pymupdf.open.side_effect = RuntimeError("corrupt")

    with pytest.raises(VisionError, match="Failed to open PDF"):
        _pdf_to_images(pdf)


# --- _encode_image ---


def test_encode_image_returns_base64():
    result = _encode_image(b"hello")
    assert result == "aGVsbG8="


# --- _call_vision_api ---


async def test_call_vision_api_returns_content():
    client = mock.AsyncMock()
    client.chat.completions.create.return_value = _mock_completion("# Title\nContent")

    result = await _call_vision_api(client, "vision-model", "base64data")

    assert result == "# Title\nContent"
    assert client.chat.completions.create.call_count == 1


async def test_call_vision_api_raises_on_empty_choices():
    client = mock.AsyncMock()
    response = mock.Mock()
    response.choices = []
    client.chat.completions.create.return_value = response

    with pytest.raises(VisionError, match="empty choices"):
        await _call_vision_api(client, "model", "img")


async def test_call_vision_api_returns_empty_string_on_none_content():
    client = mock.AsyncMock()
    client.chat.completions.create.return_value = _mock_completion(None)

    result = await _call_vision_api(client, "model", "img")

    assert result == ""


async def test_call_vision_api_retries_on_5xx():
    client = mock.AsyncMock()
    client.chat.completions.create.side_effect = [
        _make_api_status_error(503, "Service Unavailable"),
        _mock_completion("Recovered"),
    ]

    with mock.patch("docproc.vision.asyncio.sleep", new_callable=mock.AsyncMock):
        result = await _call_vision_api(client, "model", "img")

    assert result == "Recovered"
    assert client.chat.completions.create.call_count == 2


async def test_call_vision_api_fails_immediately_on_4xx():
    client = mock.AsyncMock()
    client.chat.completions.create.side_effect = _make_api_status_error(
        422, "Unprocessable"
    )

    with pytest.raises(VisionError, match="Client error 422"):
        await _call_vision_api(client, "model", "img")

    assert client.chat.completions.create.call_count == 1


async def test_call_vision_api_raises_after_max_retries():
    client = mock.AsyncMock()
    client.chat.completions.create.side_effect = _make_api_status_error(
        500, "Internal Server Error"
    )

    with (
        mock.patch("docproc.vision.asyncio.sleep", new_callable=mock.AsyncMock),
        pytest.raises(VisionError, match="failed after 3 attempts"),
    ):
        await _call_vision_api(client, "model", "img")

    assert client.chat.completions.create.call_count == 3


async def test_call_vision_api_retries_on_connection_error():
    client = mock.AsyncMock()
    client.chat.completions.create.side_effect = [
        APIConnectionError(request=mock.Mock()),
        _mock_completion("OK"),
    ]

    with mock.patch("docproc.vision.asyncio.sleep", new_callable=mock.AsyncMock):
        result = await _call_vision_api(client, "model", "img")

    assert result == "OK"
    assert client.chat.completions.create.call_count == 2


async def test_call_vision_api_raises_after_max_connection_errors():
    client = mock.AsyncMock()
    client.chat.completions.create.side_effect = APIConnectionError(request=mock.Mock())

    with (
        mock.patch("docproc.vision.asyncio.sleep", new_callable=mock.AsyncMock),
        pytest.raises(VisionError, match="failed after 3 attempts"),
    ):
        await _call_vision_api(client, "model", "img")

    assert client.chat.completions.create.call_count == 3


async def test_call_vision_api_exponential_backoff():
    client = mock.AsyncMock()
    client.chat.completions.create.side_effect = _make_api_status_error(500, "error")

    mock_sleep = mock.AsyncMock()
    with (
        mock.patch("docproc.vision.asyncio.sleep", mock_sleep),
        pytest.raises(VisionError),
    ):
        await _call_vision_api(client, "model", "img")

    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list[0].args[0] == 1.0
    assert mock_sleep.call_args_list[1].args[0] == 2.0


# --- extract_with_vision (integration, mocked) ---


@mock.patch("docproc.vision.AsyncOpenAI")
@mock.patch("docproc.vision._pdf_to_images")
async def test_extract_with_vision_single_page_pdf(mock_pdf, mock_openai_cls, tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    mock_pdf.return_value = [b"png-page-1"]

    mock_client = mock.AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_completion("# Page 1")
    mock_openai_cls.return_value = mock_client

    result = await extract_with_vision(pdf, _make_config())

    assert result.content == "# Page 1"
    assert result.tables is None
    assert result.structural_notes is None


@mock.patch("docproc.vision.AsyncOpenAI")
@mock.patch("docproc.vision._pdf_to_images")
async def test_extract_with_vision_multi_page_pdf(mock_pdf, mock_openai_cls, tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    mock_pdf.return_value = [b"png-1", b"png-2", b"png-3"]

    mock_client = mock.AsyncMock()
    mock_client.chat.completions.create.side_effect = [
        _mock_completion("Page 1 text"),
        _mock_completion("Page 2 text"),
        _mock_completion("Page 3 text"),
    ]
    mock_openai_cls.return_value = mock_client

    result = await extract_with_vision(pdf, _make_config())

    assert result.content == "Page 1 text\n\nPage 2 text\n\nPage 3 text"
    assert mock_client.chat.completions.create.call_count == 3


@mock.patch("docproc.vision.AsyncOpenAI")
async def test_extract_with_vision_direct_image(mock_openai_cls, tmp_path):
    img = tmp_path / "photo.png"
    img.write_bytes(b"fake-png-data")

    mock_client = mock.AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_completion("Image content")
    mock_openai_cls.return_value = mock_client

    result = await extract_with_vision(img, _make_config())

    assert result.content == "Image content"


async def test_extract_with_vision_rejects_unsupported_file(tmp_path):
    docx = tmp_path / "doc.docx"
    docx.touch()

    with pytest.raises(VisionError, match="Unsupported file type"):
        await extract_with_vision(docx, _make_config())


async def test_extract_with_vision_rejects_missing_file(tmp_path):
    missing = tmp_path / "missing.pdf"

    with pytest.raises(VisionError, match="File not found"):
        await extract_with_vision(missing, _make_config())


@mock.patch("docproc.vision.AsyncOpenAI")
async def test_extract_with_vision_uses_config_model(mock_openai_cls, tmp_path):
    img = tmp_path / "doc.jpg"
    img.write_bytes(b"fake-jpg")

    mock_client = mock.AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_completion("text")
    mock_openai_cls.return_value = mock_client

    await extract_with_vision(img, _make_config(vision_model="my-vision-model"))

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "my-vision-model"


@mock.patch("docproc.vision.AsyncOpenAI")
async def test_extract_with_vision_uses_config_base_url(mock_openai_cls, tmp_path):
    img = tmp_path / "doc.jpg"
    img.write_bytes(b"fake-jpg")

    mock_client = mock.AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_completion("text")
    mock_openai_cls.return_value = mock_client

    await extract_with_vision(img, _make_config(base_url="http://custom:9000"))

    assert mock_openai_cls.call_args.kwargs["base_url"] == "http://custom:9000"


async def test_extract_with_vision_raises_on_image_read_failure(tmp_path):
    img = tmp_path / "unreadable.png"
    img.write_bytes(b"data")
    img.chmod(0o000)

    with pytest.raises(VisionError, match="Failed to read file"):
        await extract_with_vision(img, _make_config())

    img.chmod(0o644)


@mock.patch("docproc.vision.pymupdf")
def test_pdf_to_images_raises_on_render_failure(mock_pymupdf, tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")

    mock_page = mock.Mock()
    mock_page.get_pixmap.side_effect = RuntimeError("render failed")

    mock_doc = mock.MagicMock()
    mock_doc.__iter__ = mock.Mock(return_value=iter([mock_page]))
    mock_pymupdf.open.return_value = mock_doc

    with pytest.raises(VisionError, match="Failed to render PDF pages"):
        _pdf_to_images(pdf)

    assert mock_doc.close.call_count == 1
