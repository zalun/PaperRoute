"""Tests for the OCR extraction module."""

from unittest import mock

import httpx
import pytest

from docproc.config import Config
from docproc.ocr import (
    OCRError,
    _build_url,
    _parse_response,
    _validate_file,
    extract_text,
)


def _make_config(**overrides: str) -> Config:
    """Build a minimal frozen Config for testing."""
    deepfellow = {
        "base_url": "http://localhost:8000",
        "responses_endpoint": "/v1/responses",
        "ocr_endpoint": "/v1/ocr",
        "api_key": "test-key",
        "vision_model": "gpt-4-vision",
        "llm_model": "deepseek",
        "rag_collection": "documents",
        **overrides,
    }
    return Config(
        directories={"watch": "/tmp/inbox", "output": "/tmp/output"},
        deepfellow=deepfellow,
        recipients=[{"name": "Test", "tags": ["t1"]}],
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
    with pytest.raises(OCRError, match="Unsupported file type"):
        _validate_file(f)


def test_validate_file_rejects_missing_file(tmp_path):
    f = tmp_path / "missing.pdf"
    with pytest.raises(OCRError, match="File not found"):
        _validate_file(f)


@pytest.mark.parametrize("ext", [".PDF", ".Png", ".JPG"])
def test_validate_file_is_case_insensitive(tmp_path, ext):
    f = tmp_path / f"doc{ext}"
    f.touch()
    _validate_file(f)  # should not raise


# --- _build_url ---


def test_build_url_joins_base_and_endpoint():
    config = _make_config()
    assert _build_url(config) == "http://localhost:8000/v1/ocr"


def test_build_url_strips_trailing_slash():
    config = _make_config(base_url="http://localhost:8000/")
    assert _build_url(config) == "http://localhost:8000/v1/ocr"


def test_build_url_adds_leading_slash():
    config = _make_config(ocr_endpoint="v1/ocr")
    assert _build_url(config) == "http://localhost:8000/v1/ocr"


# --- _parse_response ---


def test_parse_response_multi_page_with_confidence():
    data = {
        "pages": [
            {"page_number": 1, "text": "Page one"},
            {"page_number": 2, "text": "Page two"},
        ],
        "confidence": 0.95,
    }
    result = _parse_response(data)
    assert result.text == "Page one\n\nPage two"
    assert len(result.pages) == 2
    assert result.pages[0].page_number == 1
    assert result.pages[1].text == "Page two"
    assert result.confidence == 0.95


def test_parse_response_single_page_no_confidence():
    data = {"pages": [{"page_number": 1, "text": "Only page"}]}
    result = _parse_response(data)
    assert result.text == "Only page"
    assert len(result.pages) == 1
    assert result.confidence is None


def test_parse_response_empty_pages():
    data = {"pages": [], "confidence": 0.0}
    result = _parse_response(data)
    assert result.text == ""
    assert result.pages == []
    assert result.confidence == 0.0


# --- extract_text (integration, mocked HTTP) ---


def _success_response():
    """Build a mock httpx.Response for a successful OCR call."""
    resp = mock.Mock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {
        "pages": [{"page_number": 1, "text": "Hello world"}],
        "confidence": 0.99,
    }
    return resp


async def test_extract_text_returns_ocr_result(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    config = _make_config()

    with mock.patch("docproc.ocr.httpx.AsyncClient") as mock_client_cls:
        mock_client = mock.AsyncMock()
        mock_client_cls.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_client
        )
        mock_client_cls.return_value.__aexit__ = mock.AsyncMock(return_value=False)
        mock_client.post.return_value = _success_response()

        result = await extract_text(pdf, config)

    assert result.text == "Hello world"
    assert result.confidence == 0.99
    assert len(result.pages) == 1


async def test_extract_text_raises_on_unsupported_file(tmp_path):
    docx = tmp_path / "doc.docx"
    docx.touch()
    config = _make_config()

    with pytest.raises(OCRError, match="Unsupported file type"):
        await extract_text(docx, config)


async def test_extract_text_raises_on_missing_file(tmp_path):
    missing = tmp_path / "missing.pdf"
    config = _make_config()

    with pytest.raises(OCRError, match="File not found"):
        await extract_text(missing, config)


async def test_extract_text_retries_on_5xx_then_succeeds(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    config = _make_config()

    error_resp = mock.Mock(spec=httpx.Response)
    error_resp.status_code = 503
    error_resp.text = "Service Unavailable"

    with mock.patch("docproc.ocr.httpx.AsyncClient") as mock_client_cls:
        mock_client = mock.AsyncMock()
        mock_client_cls.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_client
        )
        mock_client_cls.return_value.__aexit__ = mock.AsyncMock(return_value=False)
        mock_client.post.side_effect = [error_resp, _success_response()]

        with mock.patch("docproc.ocr.asyncio.sleep", new_callable=mock.AsyncMock):
            result = await extract_text(pdf, config)

    assert result.text == "Hello world"
    assert mock_client.post.call_count == 2


async def test_extract_text_retries_on_timeout_then_succeeds(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    config = _make_config()

    with mock.patch("docproc.ocr.httpx.AsyncClient") as mock_client_cls:
        mock_client = mock.AsyncMock()
        mock_client_cls.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_client
        )
        mock_client_cls.return_value.__aexit__ = mock.AsyncMock(return_value=False)
        mock_client.post.side_effect = [
            httpx.TimeoutException("timed out"),
            _success_response(),
        ]

        with mock.patch("docproc.ocr.asyncio.sleep", new_callable=mock.AsyncMock):
            result = await extract_text(pdf, config)

    assert result.text == "Hello world"
    assert mock_client.post.call_count == 2


async def test_extract_text_raises_after_max_retries(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    config = _make_config()

    error_resp = mock.Mock(spec=httpx.Response)
    error_resp.status_code = 500
    error_resp.text = "Internal Server Error"

    with mock.patch("docproc.ocr.httpx.AsyncClient") as mock_client_cls:
        mock_client = mock.AsyncMock()
        mock_client_cls.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_client
        )
        mock_client_cls.return_value.__aexit__ = mock.AsyncMock(return_value=False)
        mock_client.post.return_value = error_resp

        with (
            mock.patch("docproc.ocr.asyncio.sleep", new_callable=mock.AsyncMock),
            pytest.raises(OCRError, match="OCR failed after 3 attempts"),
        ):
            await extract_text(pdf, config)

    assert mock_client.post.call_count == 3


async def test_extract_text_fails_immediately_on_4xx(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    config = _make_config()

    error_resp = mock.Mock(spec=httpx.Response)
    error_resp.status_code = 422
    error_resp.text = "Unprocessable Entity"

    with mock.patch("docproc.ocr.httpx.AsyncClient") as mock_client_cls:
        mock_client = mock.AsyncMock()
        mock_client_cls.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_client
        )
        mock_client_cls.return_value.__aexit__ = mock.AsyncMock(return_value=False)
        mock_client.post.return_value = error_resp

        with pytest.raises(OCRError, match="Client error 422"):
            await extract_text(pdf, config)

    assert mock_client.post.call_count == 1


async def test_extract_text_sends_correct_auth_and_file(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    config = _make_config(api_key="secret-key-123")

    with mock.patch("docproc.ocr.httpx.AsyncClient") as mock_client_cls:
        mock_client = mock.AsyncMock()
        mock_client_cls.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_client
        )
        mock_client_cls.return_value.__aexit__ = mock.AsyncMock(return_value=False)
        mock_client.post.return_value = _success_response()

        await extract_text(pdf, config)

    call_kwargs = mock_client.post.call_args
    assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer secret-key-123"}
    filename = call_kwargs.kwargs["files"]["file"][0]
    assert filename == "doc.pdf"


@pytest.mark.parametrize("ext", [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"])
async def test_extract_text_accepts_all_image_types(tmp_path, ext):
    f = tmp_path / f"doc{ext}"
    f.write_bytes(b"fake-content")
    config = _make_config()

    with mock.patch("docproc.ocr.httpx.AsyncClient") as mock_client_cls:
        mock_client = mock.AsyncMock()
        mock_client_cls.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_client
        )
        mock_client_cls.return_value.__aexit__ = mock.AsyncMock(return_value=False)
        mock_client.post.return_value = _success_response()

        result = await extract_text(f, config)

    assert result.text == "Hello world"


async def test_extract_text_exponential_backoff_delays(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    config = _make_config()

    error_resp = mock.Mock(spec=httpx.Response)
    error_resp.status_code = 500
    error_resp.text = "Internal Server Error"

    with mock.patch("docproc.ocr.httpx.AsyncClient") as mock_client_cls:
        mock_client = mock.AsyncMock()
        mock_client_cls.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_client
        )
        mock_client_cls.return_value.__aexit__ = mock.AsyncMock(return_value=False)
        mock_client.post.return_value = error_resp

        mock_sleep = mock.AsyncMock()
        with (
            mock.patch("docproc.ocr.asyncio.sleep", mock_sleep),
            pytest.raises(OCRError),
        ):
            await extract_text(pdf, config)

    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list[0].args[0] == 1.0
    assert mock_sleep.call_args_list[1].args[0] == 2.0
