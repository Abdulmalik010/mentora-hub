"""Session-notes PDF: branded, Unicode, generated on demand from the DB.

Uses fpdf2 (pure Python, no system dependencies) with Inter Regular/Bold
embedded from ``app/assets/fonts/`` (SIL OFL 1.1, license committed
alongside). Bytes are generated per call — nothing relies on local disk,
so free-tier hosts without persistent storage stay supported.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

_NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_REGULAR = FONTS_DIR / "Inter-Regular.ttf"
FONT_BOLD = FONTS_DIR / "Inter-Bold.ttf"

INK = (11, 27, 51)
BRAND = (14, 107, 92)
GOLD = (201, 162, 39)
MUTED = (91, 100, 117)
WHITE = (255, 255, 255)


class NotesPDF(FPDF):
    """Branded page frame: header band on page 1, footer on every page."""

    fidelity_line: str = ""

    def header(self) -> None:
        """Brand band with the product name (first page only)."""
        if self.page_no() != 1:
            return
        self.set_fill_color(*BRAND)
        self.set_text_color(*WHITE)
        self.set_font("Inter", "B", 16)
        self.cell(0, 12, "Mentora Academic Hub", fill=True, **_NEXT_LINE)
        self.set_font("Inter", "", 11)
        self.cell(0, 8, "Session notes", fill=True, **_NEXT_LINE)
        self.ln(4)
        self.set_text_color(*INK)

    def footer(self) -> None:
        """Fidelity note plus page number on every page."""
        self.set_y(-15)
        self.set_font("Inter", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 10, f"{self.fidelity_line}  ·  Page {self.page_no()}")


def _section(pdf: NotesPDF, title: str) -> None:
    """Gold-ruled section heading."""
    pdf.set_font("Inter", "B", 13)
    pdf.set_text_color(*INK)
    pdf.cell(0, 8, title, **_NEXT_LINE)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)


def _body(pdf: NotesPDF, text: str) -> None:
    """Wrapped body paragraph."""
    pdf.set_font("Inter", "", 11)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 6, text)
    pdf.ln(1)


def _bullets(pdf: NotesPDF, items: list[str]) -> None:
    """Bulleted lines with hanging indent."""
    pdf.set_font("Inter", "", 11)
    pdf.set_text_color(*INK)
    for item in items:
        x = pdf.get_x()
        pdf.cell(6, 6, "\u2022")
        pdf.multi_cell(0, 6, item)
        pdf.set_x(x)
    pdf.ln(1)


def _flagged(text: str, item: dict[str, Any]) -> str:
    """Append a partial-verification flag when the reviewer hedged."""
    if item.get("partial"):
        return f"{text}  [partly verified: {item.get('partial_note', '')}]"
    return text


def build_session_notes_pdf(
    *,
    student_name: str,
    professor_name: str,
    slot_text: str,
    final_notes: dict[str, Any],
    fidelity_rate: float | None,
) -> bytes:
    """Render finalized notes to PDF bytes (raises when fonts are missing)."""
    for path in (FONT_REGULAR, FONT_BOLD):
        if not path.is_file():
            raise FileNotFoundError(
                f"PDF font missing: {path} (commit app/assets/fonts/ first)"
            )
    pdf = NotesPDF()
    pdf.fidelity_line = (
        f"Fidelity: {fidelity_rate:.0%} of note items verified"
        if fidelity_rate is not None
        else "Fidelity review pending"
    )
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_font("Inter", "", str(FONT_REGULAR))
    pdf.add_font("Inter", "B", str(FONT_BOLD))
    pdf.add_page()

    _section(pdf, "Session details")
    _body(pdf, f"Student: {student_name}\nProfessor: {professor_name}\nSlot: {slot_text}")

    _section(pdf, "Summary")
    _body(pdf, str(final_notes.get("summary", "") or "—"))

    key_points = final_notes.get("key_points", []) or []
    if key_points:
        _section(pdf, "Key points")
        _bullets(pdf, [
            _flagged(str(item.get("text", "")), item)
            for item in key_points if isinstance(item, dict)
        ])

    actions = [
        item for item in final_notes.get("action_items", []) or []
        if isinstance(item, dict)
    ]
    if actions:
        _section(pdf, "Action items")
        for owner in ("student", "professor"):
            owned = [
                item for item in actions
                if str(item.get("owner", "")).lower() == owner
            ]
            if not owned:
                continue
            pdf.set_font("Inter", "B", 11)
            pdf.cell(0, 7, f"For the {owner}", **_NEXT_LINE)
            lines = []
            for item in owned:
                task = str(item.get("task", ""))
                due = str(item.get("due", "") or "").strip()
                if due:
                    task += f" (due: {due})"
                lines.append(_flagged(task, item))
            _bullets(pdf, lines)

    concepts = final_notes.get("concepts_explained", []) or []
    if concepts:
        _section(pdf, "Concepts explained")
        for item in concepts:
            if not isinstance(item, dict):
                continue
            pdf.set_font("Inter", "B", 11)
            pdf.cell(0, 7, str(item.get("term", "")), **_NEXT_LINE)
            _body(pdf, _flagged(str(item.get("explanation", "")), item))

    decisions = final_notes.get("decisions", []) or []
    if decisions:
        _section(pdf, "Decisions")
        _bullets(pdf, [
            _flagged(str(item.get("text", "")), item)
            for item in decisions if isinstance(item, dict)
        ])

    resources = final_notes.get("resources", []) or []
    if resources:
        _section(pdf, "Resources")
        _bullets(pdf, [
            _flagged(str(item.get("text", "")), item)
            for item in resources if isinstance(item, dict)
        ])

    open_questions = final_notes.get("open_questions", []) or []
    if open_questions:
        _section(pdf, "Open questions")
        _bullets(pdf, [
            _flagged(str(item.get("text", "")), item)
            for item in open_questions if isinstance(item, dict)
        ])

    suggestion = final_notes.get("next_session_suggestion")
    if isinstance(suggestion, dict) and suggestion.get("text"):
        _section(pdf, "Next steps")
        _body(pdf, _flagged(str(suggestion["text"]), suggestion))

    return bytes(pdf.output())
