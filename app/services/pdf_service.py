"""Session-notes PDF generation (stub; library decision pending).

The reportlab-vs-WeasyPrint choice is intentionally deferred to the notes-PDF
step. This module fixes the interface now so callers do not need to change.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


def build_session_notes_pdf(
    *,
    title: str,
    sections: Mapping[str, str],
    output_path: str | Path,
) -> Path:
    """Render titled sections to a PDF file; raises until a library is chosen."""
    raise NotImplementedError(
        "PDF library not chosen (reportlab vs WeasyPrint decision pending)"
    )
