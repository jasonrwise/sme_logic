from io import BytesIO

import docx
import pytest
from fpdf import FPDF

from app.services.file_extraction import FileExtractionError, extract_text


def _make_docx_bytes(text: str) -> bytes:
    document = docx.Document()
    document.add_paragraph(text)
    buf = BytesIO()
    document.save(buf)
    return buf.getvalue()


def _make_pdf_bytes(text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, text)
    return bytes(pdf.output())


def _make_empty_pdf_bytes() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    return bytes(pdf.output())


def test_extract_text_from_docx():
    content = _make_docx_bytes("Interview notes about cold chain QC.")
    result = extract_text("transcript.docx", content)
    assert "cold chain QC" in result


def test_extract_text_from_pdf():
    content = _make_pdf_bytes("Interview notes about cold chain QC.")
    result = extract_text("transcript.pdf", content)
    assert "cold chain QC" in result


def test_extract_text_empty_pdf_raises():
    content = _make_empty_pdf_bytes()
    with pytest.raises(FileExtractionError, match="No extractable text"):
        extract_text("blank.pdf", content)


def test_extract_text_unsupported_extension_raises():
    with pytest.raises(FileExtractionError, match="Unsupported file type"):
        extract_text("notes.txt", b"plain text")


def test_extract_text_corrupt_docx_raises():
    with pytest.raises(FileExtractionError, match="Could not read .docx"):
        extract_text("notes.docx", b"not a real docx file")
