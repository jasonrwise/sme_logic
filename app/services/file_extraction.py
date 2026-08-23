"""Extract raw text from uploaded intake files (.docx, .pdf).

Text-layer extraction only — scanned/image-based PDFs with no embedded text
layer are out of scope (would require OCR) and raise FileExtractionError.
See PRD.md standard #3: services stay decoupled from API routing.
"""

import logging
from io import BytesIO
from pathlib import Path

import docx
import pypdf

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".docx", ".pdf"}


class FileExtractionError(Exception):
    """Raised when text cannot be extracted from an uploaded intake file."""


def extract_text(filename: str, content: bytes) -> str:
    """Dispatch to the right extractor based on file extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".docx":
        return _extract_docx(content)
    if ext == ".pdf":
        return _extract_pdf(content)
    raise FileExtractionError(
        f"Unsupported file type '{ext or filename}'. Supported types: "
        f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
    )


def _extract_docx(content: bytes) -> str:
    try:
        document = docx.Document(BytesIO(content))
    except Exception as e:
        logger.error("Failed to read .docx file: %s", e)
        raise FileExtractionError(f"Could not read .docx file: {e}") from e

    text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
    if not text.strip():
        raise FileExtractionError("No extractable text found in .docx file.")
    return text


def _extract_pdf(content: bytes) -> str:
    try:
        reader = pypdf.PdfReader(BytesIO(content))
    except Exception as e:
        logger.error("Failed to read .pdf file: %s", e)
        raise FileExtractionError(f"Could not read .pdf file: {e}") from e

    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        raise FileExtractionError(
            "No extractable text found in .pdf file. It may be a scanned/"
            "image-based PDF, which isn't supported."
        )
    return text
