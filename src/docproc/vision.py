"""Vision LLM extraction via DeepFellow OpenAI-compatible API.

Converts PDF pages to images using PyMuPDF, sends base64-encoded images
to a vision model via chat completions, and returns structured markdown.
Runs async for parallel execution with OCR extraction.
"""

import asyncio
import base64
import logging
from pathlib import Path

import pymupdf
from openai import APIConnectionError, APIStatusError, AsyncOpenAI

from docproc.config import Config
from docproc.models import VisionResult

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"})
_PDF_EXTENSION = ".pdf"
_IMAGE_DPI = 150
_MAX_RETRIES = 3
_INITIAL_DELAY = 1.0
_BACKOFF_FACTOR = 2.0
_MAX_TOKENS = 4096

_EXTRACTION_PROMPT = """\
Extract all text content from this document image.
Preserve the structure including headers, paragraphs, and lists.
Format tables as markdown tables.
Note any structural elements (letterhead, signatures, stamps).
Output everything in clean markdown format.\
"""


class VisionError(Exception):
    """Raised when Vision extraction fails."""


def _validate_file(file_path: Path) -> None:
    if not file_path.is_file():
        msg = f"File not found or not a regular file: {file_path}"
        raise VisionError(msg)
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        msg = f"Unsupported file type: {ext}"
        raise VisionError(msg)


def _pdf_to_images(file_path: Path) -> list[bytes]:
    """Render each PDF page as PNG bytes using PyMuPDF."""
    try:
        doc = pymupdf.open(file_path)
    except Exception as exc:
        msg = f"Failed to open PDF: {file_path}: {exc}"
        raise VisionError(msg) from exc
    try:
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=_IMAGE_DPI)
            images.append(pix.tobytes("png"))
        return images
    except Exception as exc:
        msg = f"Failed to render PDF pages: {file_path}: {exc}"
        raise VisionError(msg) from exc
    finally:
        doc.close()


def _encode_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


async def _call_vision_api(
    client: AsyncOpenAI,
    model: str,
    encoded_image: str,
) -> str:
    """Send a single image to the vision model with retry on failures."""
    delay = _INITIAL_DELAY
    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _EXTRACTION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{encoded_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=_MAX_TOKENS,
            )
            content = response.choices[0].message.content
            return content or ""

        except APIStatusError as exc:
            if exc.status_code >= 500:
                last_error = exc
                logger.warning(
                    "Vision attempt %d/%d failed (HTTP %d): %s",
                    attempt,
                    _MAX_RETRIES,
                    exc.status_code,
                    str(exc)[:200],
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(delay)
                    delay *= _BACKOFF_FACTOR
                continue
            msg = f"Client error {exc.status_code}: {exc}"
            raise VisionError(msg) from exc

        except APIConnectionError as exc:
            last_error = exc
            logger.warning(
                "Vision attempt %d/%d failed with connection error: %s",
                attempt,
                _MAX_RETRIES,
                exc,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(delay)
                delay *= _BACKOFF_FACTOR

    msg = f"Vision extraction failed after {_MAX_RETRIES} attempts"
    raise VisionError(msg) from last_error


async def extract_with_vision(file_path: Path, config: Config) -> VisionResult:
    """Extract content from a document using a Vision LLM model.

    Converts PDF pages to images, sends each to the vision model,
    and returns structured markdown content.

    Args:
        file_path: Path to PDF or image file.
        config: Application configuration.

    Returns:
        VisionResult with markdown content.

    Raises:
        VisionError: If extraction fails after retries.
    """
    _validate_file(file_path)

    ext = file_path.suffix.lower()
    if ext == _PDF_EXTENSION:
        image_pages = _pdf_to_images(file_path)
    else:
        try:
            image_pages = [file_path.read_bytes()]
        except OSError as exc:
            msg = f"Failed to read file {file_path}: {exc}"
            raise VisionError(msg) from exc

    logger.info(
        "Starting Vision extraction: %s (%d pages)",
        file_path.name,
        len(image_pages),
    )

    client = AsyncOpenAI(
        base_url=config.deepfellow.base_url,
        api_key=config.deepfellow.api_key,
    )

    page_results = []
    for i, page_bytes in enumerate(image_pages, 1):
        encoded = _encode_image(page_bytes)
        text = await _call_vision_api(client, config.deepfellow.vision_model, encoded)
        page_results.append(text)
        logger.debug("Vision page %d/%d complete", i, len(image_pages))

    content = "\n\n".join(page_results)
    logger.info("Vision complete: %s (%d pages)", file_path.name, len(image_pages))
    return VisionResult(content=content)
