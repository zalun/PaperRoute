"""Pydantic data models for the PaperRoute processing pipeline.

Data flows through the pipeline as:
ProcessingJob → OCRResult + VisionResult → ReconciledDocument
→ Classification → ProcessedDocument
"""

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

_DATE_FORMATS = ("%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y")


def _parse_date(value: object) -> date | None:
    """Try ISO format first, then common date formats."""
    if value is None or isinstance(value, date):
        return value
    if not isinstance(value, str):
        msg = f"Cannot parse date from {type(value).__name__}"
        raise ValueError(msg)
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    msg = f"Cannot parse date: {value!r}"
    raise ValueError(msg)


class ProcessingJob(BaseModel):
    file_path: Path
    file_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["pending", "processing", "done", "failed"] = "pending"


class PageText(BaseModel):
    page_number: int = Field(ge=1)
    text: str


class OCRResult(BaseModel):
    text: str
    pages: list[PageText]
    confidence: float | None = None

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 1.0):
            msg = "Confidence must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class VisionResult(BaseModel):
    content: str
    tables: list[str] | None = None
    structural_notes: str | None = None


class ReconciledDocument(BaseModel):
    markdown: str
    document_date: date | None = None
    title: str | None = None
    language: str | None = None

    @field_validator("document_date", mode="before")
    @classmethod
    def parse_document_date(cls, v: object) -> date | None:
        return _parse_date(v)


class Classification(BaseModel):
    recipient: str = Field(min_length=1)
    category: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    confidence: float | None = None
    reasoning: str | None = None

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 1.0):
            msg = "Confidence must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ProcessedDocument(BaseModel):
    original_path: Path
    output_path: Path
    markdown: str
    classification: Classification
    document_date: date | None = None
    indexed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
