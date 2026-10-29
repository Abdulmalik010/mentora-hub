"""Student upload validation, storage and text extraction.

Accepted types: PDF (via pypdf), DOCX (via stdlib zipfile + ElementTree) and
plain UTF-8 text (.txt, .md). Files are validated by extension and signature,
stored under the upload folder with UUID names, and extracted with
``[[page N]]`` markers. A PDF that yields almost no text is reported as
scanned so the caller can fall back to native PDF model input.
"""
from __future__ import annotations

import io
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from xml.etree import ElementTree

from pypdf import PdfReader

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = ("pdf", "docx", "txt", "md")
# Below this many extracted chars per PDF page, treat the PDF as scanned.
SCANNED_CHARS_PER_PAGE = 50


class ExtractionError(ValueError):
    """Upload rejected or text extraction failed."""


@dataclass(frozen=True)
class ExtractedText:
    """Extraction result with explicit page markers in ``text``."""

    text: str
    pages: int
    scanned: bool = False


def validate_upload(filename: str, data: bytes) -> str:
    """Check name, size and signature; return the lowercase extension."""
    if "." not in filename:
        raise ExtractionError("uploaded file needs an extension (pdf, docx, txt, md)")
    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ExtractionError(f".{ext} uploads are not accepted")
    if not data:
        raise ExtractionError("uploaded file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ExtractionError("uploaded file exceeds the 10 MB limit")
    if ext == "pdf" and not data.startswith(b"%PDF-"):
        raise ExtractionError("file is not a real PDF (bad signature)")
    if ext == "docx" and not _looks_like_docx(data):
        raise ExtractionError("file is not a real DOCX (bad signature)")
    if ext in ("txt", "md"):
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise ExtractionError("text file is not valid UTF-8") from None
    return ext


def _looks_like_docx(data: bytes) -> bool:
    """True when the bytes are a zip archive containing a Word document."""
    if not data.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False


def save_upload(data: bytes, ext: str, upload_dir: str | Path) -> Path:
    """Store bytes under a UUID filename; return the absolute path."""
    folder = Path(upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}.{ext}"
    path.write_bytes(data)
    return path.resolve()


def extract_text(path: str | Path, ext: str) -> ExtractedText:
    """Extract text with ``[[page N]]`` markers for a validated upload."""
    raw = Path(path).read_bytes()
    if ext == "pdf":
        return _extract_pdf(raw)
    if ext == "docx":
        return _extract_docx(raw)
    text = raw.decode("utf-8")
    return ExtractedText(text=f"[[page 1]]\n{text.strip()}", pages=1)


def _extract_pdf(raw: bytes) -> ExtractedText:
    """Per-page pypdf extraction with a scanned-document check."""
    try:
        reader = PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise ExtractionError(f"could not read PDF: {exc}") from exc
    if not pages:
        raise ExtractionError("PDF has no pages")
    marked = "\n\n".join(f"[[page {n}]]\n{text.strip()}" for n, text in enumerate(pages, 1))
    chars = sum(len(text) for text in pages)
    scanned = chars < SCANNED_CHARS_PER_PAGE * len(pages)
    return ExtractedText(text=marked, pages=len(pages), scanned=scanned)


def _extract_docx(raw: bytes) -> ExtractedText:
    """Paragraph text via stdlib zipfile + ElementTree (single page marker)."""
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml)
    except Exception as exc:
        raise ExtractionError(f"could not read DOCX: {exc}") from exc
    paragraphs = []
    for para in root.iter(f"{namespace}p"):
        runs = [
            node.text for node in para.iter(f"{namespace}t") if node.text
        ]
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)
    if not paragraphs:
        raise ExtractionError("DOCX has no readable paragraphs")
    return ExtractedText(text="[[page 1]]\n" + "\n\n".join(paragraphs), pages=1)


def read_upload_file(storage: BinaryIO, filename: str) -> tuple[bytes, str]:
    """Read a Werkzeug upload stream and validate it; return (bytes, ext)."""
    data = storage.read()
    if isinstance(data, str):
        data = data.encode("utf-8")
    return bytes(data), validate_upload(filename, bytes(data))
