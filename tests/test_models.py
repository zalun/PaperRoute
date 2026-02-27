from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from docproc.models import (
    Classification,
    OCRResult,
    PageText,
    ProcessedDocument,
    ProcessingJob,
    ReconciledDocument,
    VisionResult,
)

# --- ProcessingJob ---


def test_processing_job_creates_with_minimal_fields():
    job = ProcessingJob(file_path="/tmp/doc.pdf", file_type="pdf")
    assert job.file_path == Path("/tmp/doc.pdf")
    assert job.file_type == "pdf"


def test_processing_job_defaults_status_to_pending():
    job = ProcessingJob(file_path="/tmp/doc.pdf", file_type="pdf")
    assert job.status == "pending"


def test_processing_job_defaults_created_at_to_now():
    before = datetime.now(UTC)
    job = ProcessingJob(file_path="/tmp/doc.pdf", file_type="pdf")
    after = datetime.now(UTC)
    assert before <= job.created_at <= after


def test_processing_job_accepts_string_path():
    job = ProcessingJob(file_path="/tmp/doc.pdf", file_type="pdf")
    assert isinstance(job.file_path, Path)


def test_processing_job_rejects_invalid_status():
    with pytest.raises(ValidationError):
        ProcessingJob(file_path="/tmp/doc.pdf", file_type="pdf", status="unknown")


def test_processing_job_status_is_mutable():
    job = ProcessingJob(file_path="/tmp/doc.pdf", file_type="pdf")
    job.status = "processing"
    assert job.status == "processing"


def test_processing_job_rejects_invalid_status_on_assignment():
    job = ProcessingJob(file_path="/tmp/doc.pdf", file_type="pdf")
    with pytest.raises(ValidationError):
        job.status = "invalid"


@pytest.mark.parametrize("file_type", ["", "   "])
def test_processing_job_rejects_blank_file_type(file_type):
    with pytest.raises(ValidationError):
        ProcessingJob(file_path="/tmp/doc.pdf", file_type=file_type)


def test_processing_job_strips_and_lowercases_file_type():
    job = ProcessingJob(file_path="/tmp/doc.pdf", file_type="  PDF  ")
    assert job.file_type == "pdf"


def test_processing_job_json_roundtrip():
    job = ProcessingJob(file_path="/tmp/doc.pdf", file_type="pdf")
    data = job.model_dump_json()
    restored = ProcessingJob.model_validate_json(data)
    assert restored.file_path == job.file_path
    assert restored.status == job.status


# --- PageText ---


def test_page_text_creates_with_valid_data():
    page = PageText(page_number=1, text="Hello")
    assert page.page_number == 1
    assert page.text == "Hello"


@pytest.mark.parametrize("page_number", [0, -1])
def test_page_text_rejects_page_number_less_than_one(page_number):
    with pytest.raises(ValidationError):
        PageText(page_number=page_number, text="Hello")


# --- OCRResult ---


def test_ocr_result_creates_with_valid_data():
    result = OCRResult(
        text="Hello world",
        pages=[PageText(page_number=1, text="Hello world")],
        confidence=0.95,
    )
    assert result.text == "Hello world"
    assert len(result.pages) == 1
    assert result.confidence == 0.95


def test_ocr_result_defaults_confidence_to_none():
    result = OCRResult(text="Hello", pages=[])
    assert result.confidence is None


@pytest.mark.parametrize("confidence", [-0.1, 1.5])
def test_ocr_result_rejects_confidence_outside_range(confidence):
    with pytest.raises(ValidationError):
        OCRResult(text="Hello", pages=[], confidence=confidence)


# --- VisionResult ---


def test_vision_result_creates_with_content_only():
    result = VisionResult(content="# Document Title")
    assert result.content == "# Document Title"


def test_vision_result_defaults_optionals_to_none():
    result = VisionResult(content="text")
    assert result.tables is None
    assert result.structural_notes is None


# --- ReconciledDocument ---


def test_reconciled_document_creates_with_markdown_only():
    doc = ReconciledDocument(markdown="# Hello")
    assert doc.markdown == "# Hello"
    assert doc.document_date is None
    assert doc.title is None
    assert doc.language is None


@pytest.mark.parametrize(
    "date_str,expected",
    [
        ("2024-03-15", date(2024, 3, 15)),
        ("2024-03-15T10:30:00", date(2024, 3, 15)),
        ("2024-03-15T00:00:00Z", date(2024, 3, 15)),
        ("15/03/2024", date(2024, 3, 15)),
        ("15.03.2024", date(2024, 3, 15)),
        ("  2024-03-15  ", date(2024, 3, 15)),
    ],
)
def test_reconciled_document_parses_date_formats(date_str, expected):
    doc = ReconciledDocument(markdown="text", document_date=date_str)
    assert doc.document_date == expected


def test_reconciled_document_accepts_date_object():
    d = date(2024, 1, 1)
    doc = ReconciledDocument(markdown="text", document_date=d)
    assert doc.document_date == d


def test_reconciled_document_rejects_unparseable_date():
    with pytest.raises(ValidationError):
        ReconciledDocument(markdown="text", document_date="not-a-date")


def test_reconciled_document_rejects_non_string_date():
    with pytest.raises(ValidationError, match="Cannot parse date from int"):
        ReconciledDocument(markdown="text", document_date=12345)


def test_reconciled_document_converts_datetime_to_date():
    dt = datetime(2024, 3, 15, 10, 30, tzinfo=UTC)
    doc = ReconciledDocument(markdown="text", document_date=dt)
    assert doc.document_date == date(2024, 3, 15)


def test_reconciled_document_validates_date_on_assignment():
    doc = ReconciledDocument(markdown="text", document_date="2024-03-15")
    doc.document_date = "15/03/2024"
    assert doc.document_date == date(2024, 3, 15)
    with pytest.raises(ValidationError):
        doc.document_date = "not-a-date"


# --- Classification ---


def test_classification_creates_with_required_fields():
    cls = Classification(recipient="Alice", category="invoices", subject="Water bill")
    assert cls.recipient == "Alice"
    assert cls.category == "invoices"
    assert cls.subject == "Water bill"


@pytest.mark.parametrize("field", ["recipient", "category", "subject"])
def test_classification_rejects_empty_strings(field):
    kwargs = {
        "recipient": "Alice",
        "category": "invoices",
        "subject": "Water bill",
    }
    kwargs[field] = ""
    with pytest.raises(ValidationError):
        Classification(**kwargs)


@pytest.mark.parametrize("field", ["recipient", "category", "subject"])
def test_classification_rejects_whitespace_only_strings(field):
    kwargs = {
        "recipient": "Alice",
        "category": "invoices",
        "subject": "Water bill",
    }
    kwargs[field] = "   "
    with pytest.raises(ValidationError):
        Classification(**kwargs)


def test_classification_strips_whitespace():
    cls = Classification(
        recipient="  Alice  ", category="  invoices  ", subject="  Water bill  "
    )
    assert cls.recipient == "Alice"
    assert cls.category == "invoices"
    assert cls.subject == "Water bill"


def test_classification_validates_on_assignment():
    cls = Classification(recipient="Alice", category="invoices", subject="Bill")
    cls.recipient = "  Bob  "
    assert cls.recipient == "Bob"
    with pytest.raises(ValidationError):
        cls.recipient = "   "


def test_classification_defaults_optionals_to_none():
    cls = Classification(recipient="Alice", category="invoices", subject="Water bill")
    assert cls.confidence is None
    assert cls.reasoning is None


def test_classification_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        Classification(
            recipient="Alice",
            category="invoices",
            subject="Bill",
            confidence=2.0,
        )


# --- ProcessedDocument ---


def test_processed_document_creates_with_all_fields():
    cls = Classification(recipient="Alice", category="invoices", subject="Bill")
    doc = ProcessedDocument(
        original_path="/tmp/doc.pdf",
        output_path="/tmp/output/doc.md",
        markdown="# Bill",
        classification=cls,
        document_date=date(2024, 1, 1),
        indexed=True,
        metadata={"source": "email"},
    )
    assert doc.original_path == Path("/tmp/doc.pdf")
    assert doc.indexed is True
    assert doc.metadata == {"source": "email"}


def test_processed_document_defaults_indexed_and_metadata():
    cls = Classification(recipient="Alice", category="invoices", subject="Bill")
    doc = ProcessedDocument(
        original_path="/tmp/doc.pdf",
        output_path="/tmp/output/doc.md",
        markdown="# Bill",
        classification=cls,
    )
    assert doc.indexed is False
    assert doc.metadata == {}


def test_processed_document_accepts_string_paths():
    cls = Classification(recipient="Alice", category="invoices", subject="Bill")
    doc = ProcessedDocument(
        original_path="/tmp/doc.pdf",
        output_path="/tmp/output/doc.md",
        markdown="# Bill",
        classification=cls,
    )
    assert isinstance(doc.original_path, Path)
    assert isinstance(doc.output_path, Path)


def test_processed_document_parses_date_string():
    cls = Classification(recipient="Alice", category="invoices", subject="Bill")
    doc = ProcessedDocument(
        original_path="/tmp/doc.pdf",
        output_path="/tmp/output/doc.md",
        markdown="# Bill",
        classification=cls,
        document_date="15/03/2024",
    )
    assert doc.document_date == date(2024, 3, 15)


def test_processed_document_json_roundtrip():
    cls = Classification(recipient="Alice", category="invoices", subject="Bill")
    doc = ProcessedDocument(
        original_path="/tmp/doc.pdf",
        output_path="/tmp/output/doc.md",
        markdown="# Bill",
        classification=cls,
        document_date=date(2024, 1, 1),
    )
    data = doc.model_dump_json()
    restored = ProcessedDocument.model_validate_json(data)
    assert restored.classification.recipient == "Alice"
    assert restored.document_date == date(2024, 1, 1)
