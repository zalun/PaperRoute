"""Pydantic data models for the PaperRoute processing pipeline.

Data flows through the pipeline as:
ProcessingJob → OCRResult + VisionResult → ReconciledDocument
→ Classification → ProcessedDocument
"""

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Slash-separated dates are interpreted as European (dd/mm/YYYY).
# US month-first format is excluded to avoid silent misinterpretation
# of ambiguous dates like "03/04/2024".
_DATE_FORMATS = ("%d/%m/%Y", "%d.%m.%Y")

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


def _parse_date(value: object) -> date | None:
    """Try ISO format first, then common date formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        msg = f"Cannot parse date from {type(value).__name__}"
        raise ValueError(msg)
    value = value.strip()
    if not value:
        msg = "Cannot parse date from empty string"
        raise ValueError(msg)
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(value).date()
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
    model_config = ConfigDict(validate_assignment=True)

    file_path: Path
    file_type: str = Field(min_length=1)

    @field_validator("file_type")
    @classmethod
    def file_type_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip().lower()
        if not stripped:
            msg = "file_type must not be blank"
            raise ValueError(msg)
        return stripped

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["pending", "processing", "done", "failed"] = "pending"


class PageText(BaseModel):
    page_number: int = Field(ge=1)
    text: str


class OCRResult(BaseModel):
    text: str
    pages: list[PageText]
    confidence: Confidence | None = None


class VisionResult(BaseModel):
    content: str
    tables: list[str] | None = None
    structural_notes: str | None = None


class ReconciledDocument(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    markdown: str
    document_date: date | None = None
    title: str | None = None
    language: str | None = None

    @field_validator("document_date", mode="before")
    @classmethod
    def parse_document_date(cls, v: object) -> date | None:
        return _parse_date(v)


class Classification(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    recipient: str = Field(min_length=1)
    category: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    confidence: Confidence | None = None
    reasoning: str | None = None

    @field_validator("recipient", "category", "subject")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            msg = "Field must not be blank"
            raise ValueError(msg)
        return stripped


class ProcessedDocument(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    original_path: Path
    output_path: Path
    markdown: str
    classification: Classification
    document_date: date | None = None
    indexed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("document_date", mode="before")
    @classmethod
    def parse_document_date(cls, v: object) -> date | None:
        return _parse_date(v)
