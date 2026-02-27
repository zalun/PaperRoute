"""OCR extraction via DeepFellow easyOCR API.

Sends PDF/image files to the remote easyOCR endpoint and returns
structured text with page-level breakdown. Runs async for parallel
execution with Vision extraction.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from docproc.config import Config
from docproc.models import OCRResult, PageText

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"})

_MAX_RETRIES = 3
_INITIAL_DELAY = 1.0
_BACKOFF_FACTOR = 2.0
_TIMEOUT_SECONDS = 120.0


class OCRError(Exception):
    """Raised when OCR extraction fails."""


def _validate_file(file_path: Path) -> None:
    """Check that the file exists and has a supported extension."""
    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise OCRError(msg)
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        msg = f"Unsupported file type: {ext}"
        raise OCRError(msg)


def _build_url(config: Config) -> str:
    """Join base_url and ocr_endpoint into a full URL."""
    base = config.deepfellow.base_url.rstrip("/")
    endpoint = config.deepfellow.ocr_endpoint
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    return base + endpoint


def _parse_response(data: dict[str, Any]) -> OCRResult:
    """Convert API JSON response to an OCRResult."""
    pages = [
        PageText(page_number=p["page_number"], text=p["text"])
        for p in data.get("pages", [])
    ]
    full_text = "\n\n".join(p.text for p in pages)
    confidence = data.get("confidence")
    return OCRResult(text=full_text, pages=pages, confidence=confidence)


async def _send_with_retry(
    client: httpx.AsyncClient,
    url: str,
    file_path: Path,
    api_key: str,
) -> dict[str, Any]:
    """POST the file with exponential backoff retry on 5xx/timeouts."""
    delay = _INITIAL_DELAY
    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            file_bytes = file_path.read_bytes()
            files = {"file": (file_path.name, file_bytes)}
            headers = {"Authorization": f"Bearer {api_key}"}
            response = await client.post(
                url,
                files=files,
                headers=headers,
                timeout=_TIMEOUT_SECONDS,
            )

            if response.status_code >= 500:
                last_error = OCRError(
                    f"Server error {response.status_code}: {response.text}"
                )
                logger.warning(
                    "OCR attempt %d/%d failed: %s", attempt, _MAX_RETRIES, last_error
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(delay)
                    delay *= _BACKOFF_FACTOR
                continue

            if response.status_code >= 400:
                msg = f"Client error {response.status_code}: {response.text}"
                raise OCRError(msg)

            return response.json()

        except httpx.TimeoutException as exc:
            last_error = OCRError(f"Request timed out: {exc}")
            logger.warning("OCR attempt %d/%d timed out", attempt, _MAX_RETRIES)
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(delay)
                delay *= _BACKOFF_FACTOR

    msg = f"OCR failed after {_MAX_RETRIES} attempts"
    raise OCRError(msg) from last_error


async def extract_text(file_path: Path, config: Config) -> OCRResult:
    """Extract text from a document using DeepFellow easyOCR.

    Args:
        file_path: Path to PDF or image file.
        config: Application configuration.

    Returns:
        OCRResult with extracted text and page breakdown.

    Raises:
        OCRError: If extraction fails after retries.
    """
    _validate_file(file_path)
    url = _build_url(config)

    logger.info("Starting OCR extraction: %s", file_path.name)

    async with httpx.AsyncClient() as client:
        data = await _send_with_retry(client, url, file_path, config.deepfellow.api_key)

    result = _parse_response(data)
    logger.info("OCR complete: %s (%d pages)", file_path.name, len(result.pages))
    return result
