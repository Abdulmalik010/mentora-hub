"""Generate original synthetic thesis excerpts for intake demos and tests.

Run from the project root: ``python -m scripts.make_samples``. Writes two
small files plus ``expected.json`` under ``samples/``. All text is original,
labeled sample data, with planted flaws for the diagnosis agent to find.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
SAMPLE_TAG = "[SAMPLE DATA - synthetic thesis excerpt for development and demo only.]"

PDF_FILENAME = "thesis_excerpt_stats.pdf"
DOCX_FILENAME = "thesis_excerpt_methods.docx"

# One source of truth: expected.json quotes are drawn from these constants,
# so they are always verbatim substrings of the generated files.
PDF_PAGES: list[list[str]] = [
    [
        SAMPLE_TAG,
        "Chapter 4: Effect of Peer Tutorials on Test Scores",
        "I compared final test scores for 40 students who attended peer",
        "tutorials against 40 who did not.",
        "The tutorial group averaged 68.4 and the control group averaged 64.1.",
        "With p = 0.06, we accept the null hypothesis and conclude the",
        "tutorial has no effect.",
        "The analysis is complete and no further checks are needed.",
    ],
    [
        "I also interviewed 8 friends from my hostel about their study habits.",
        "These interviews prove that all undergraduates in Nigeria prefer",
        "group study.",
        "No previous study has ever examined study habits, so there is no",
        "literature to review.",
        "I therefore cite no prior work in this chapter.",
    ],
]

DOCX_PARAGRAPHS: list[str] = [
    SAMPLE_TAG,
    "Chapter 3: Survey of Campus Study Spaces",
    "I collected 200 questionnaire responses from the library exit.",
    "I removed 80 responses as outliers because they disagreed with my hypothesis, leaving 120.",
    "To measure deep learning, I recorded attendance: students who showed up must have learned deeply.",
    "Results were good.",
    "TODO: expand this section before submission.",
]

# NOTE: multi-line PDF constants join with a space when read back, because
# pypdf inserts newlines between Tj lines that normalize_text collapses.
PDF_FLAWS: list[dict[str, str]] = [
    {
        "category": "statistics",
        "quote": "With p = 0.06, we accept the null hypothesis and conclude the tutorial has no effect.",
        "note": "Accepts the null at p = 0.06 with no power or effect-size discussion.",
    },
    {
        "category": "methodology",
        "quote": "These interviews prove that all undergraduates in Nigeria prefer group study.",
        "note": "Generalizes from 8 hostel friends to all undergraduates in Nigeria.",
    },
    {
        "category": "literature",
        "quote": "No previous study has ever examined study habits, so there is no literature to review.",
        "note": "Sweeping claim with zero citations and no review attempted.",
    },
]

DOCX_FLAWS: list[dict[str, str]] = [
    {
        "category": "data",
        "quote": "I removed 80 responses as outliers because they disagreed with my hypothesis, leaving 120.",
        "note": "Drops 40% of responses for disagreeing with the hypothesis.",
    },
    {
        "category": "theory",
        "quote": "To measure deep learning, I recorded attendance: students who showed up must have learned deeply.",
        "note": "Measures attendance while claiming the construct is deep learning.",
    },
    {
        "category": "writing",
        "quote": "TODO: expand this section before submission.",
        "note": "Leftover drafting note plus a one-sentence results paragraph.",
    },
]


def _pdf_escape(text: str) -> str:
    """Escape PDF literal-string metacharacters."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_bytes(pages: list[list[str]]) -> bytes:
    """Build a minimal multi-page PDF; one text line per string, ASCII only."""
    objects: list[bytes] = []
    page_numbers: list[int] = []
    next_number = 4  # 1 catalog, 2 pages, 3 font
    for lines in pages:
        content_lines = []
        y = 720
        for line in lines:
            content_lines.append(f"72 {y} Td ({_pdf_escape(line)}) Tj")
            y -= 20
        content = ("BT /F1 12 Tf " + " ".join(content_lines) + " ET").encode("latin-1")
        page_number = next_number
        content_number = next_number + 1
        page_numbers.append(page_number)
        objects.append(
            f"{page_number} 0 obj\n<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {content_number} 0 R >>\nendobj\n".encode("latin-1")
        )
        objects.append(
            f"{content_number} 0 obj\n<< /Length {len(content)} >>\nstream\n".encode("latin-1")
            + content
            + b"\nendstream\nendobj\n"
        )
        next_number += 2
    kids = " ".join(f"{number} 0 R" for number in page_numbers)
    header = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>\nendobj\n".encode("latin-1"),
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    ordered = header + objects
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    # NOTE: objects carry their own numbers, so order must match numbering.
    for body in ordered:
        offsets.append(len(out))
        out += body
    xref_at = len(out)
    out += f"xref\n0 {len(ordered) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(ordered) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)


def docx_bytes(paragraphs: list[str]) -> bytes:
    """Build a minimal readable DOCX from plain-text paragraphs."""
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    runs = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
        for text in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{runs}</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def expected_flaws() -> dict[str, dict[str, object]]:
    """Flaw catalog keyed by sample filename (quotes are verbatim)."""
    return {
        PDF_FILENAME: {"label": SAMPLE_TAG, "flaws": PDF_FLAWS},
        DOCX_FILENAME: {"label": SAMPLE_TAG, "flaws": DOCX_FLAWS},
    }


def main() -> None:
    """Write the sample files and expected.json under samples/."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    (SAMPLES_DIR / PDF_FILENAME).write_bytes(pdf_bytes(PDF_PAGES))
    (SAMPLES_DIR / DOCX_FILENAME).write_bytes(docx_bytes(DOCX_PARAGRAPHS))
    with open(SAMPLES_DIR / "expected.json", "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(expected_flaws(), indent=2) + "\n")
    print(f"Wrote samples to {SAMPLES_DIR}")


if __name__ == "__main__":
    main()
