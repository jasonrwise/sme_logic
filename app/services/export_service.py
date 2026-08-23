"""Render a WorkflowResult (metadata + extracted checklist) to an export file.

Two output formats: markdown (plain string) and PDF (fpdf2, core Helvetica
font — latin-1 only, hence _sanitize_pdf_text below). See PRD.md standard #3:
services stay decoupled from API routing.
"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.schemas.workflow import WorkflowResult

# fpdf2's core fonts (Helvetica/Times/Courier) only support latin-1. LLM
# output routinely contains smart quotes/dashes from real transcripts, which
# would otherwise raise inside fpdf2. Normalize the common ones and fall
# back to "?" for anything else rather than crashing the export.
_PDF_CHAR_REPLACEMENTS = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "…": "...",
}


def _sanitize_pdf_text(text: str) -> str:
    for orig, repl in _PDF_CHAR_REPLACEMENTS.items():
        text = text.replace(orig, repl)
    return text.encode("latin-1", "replace").decode("latin-1")


def render_markdown(result: WorkflowResult) -> str:
    md = result.metadata
    checklist = result.checklist

    lines = [
        f"# {md.title}",
        "",
        f"**Date:** {md.date.isoformat()}  ",
        f"**Domain:** {checklist.domain}",
    ]
    if md.notes:
        lines.append(f"**Notes:** {md.notes}")

    lines += [
        "",
        "## Summary of Tacit Knowledge",
        "",
        checklist.summary_of_tacit_knowledge,
        "",
        "## Steps",
        "",
    ]
    for step in checklist.steps:
        flag = " ⚠ Compliance-critical" if step.is_compliance_critical else ""
        lines.append(f"{step.step_number}. **{step.action_name}** ({step.actor_role}){flag}")
        lines.append(f"   {step.description}")
        if step.deterministic_rule:
            lines.append(f"   *Rule: {step.deterministic_rule}*")
        lines.append("")

    if checklist.identified_risks:
        lines.append("## Identified Risks")
        lines.append("")
        for risk in checklist.identified_risks:
            lines.append(f"- {risk}")
        lines.append("")

    return "\n".join(lines)


def _line(pdf: FPDF, h: float, text: str) -> None:
    """multi_cell wrapper that resets the cursor to the left margin afterward.

    fpdf2's multi_cell default (new_x=XPos.RIGHT) leaves x at the right edge,
    which raises "Not enough horizontal space" on the next full-width call.
    """
    pdf.multi_cell(0, h, _sanitize_pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def render_pdf(result: WorkflowResult) -> bytes:
    md = result.metadata
    checklist = result.checklist

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    _line(pdf, 10, md.title)

    pdf.set_font("Helvetica", "", 10)
    _line(pdf, 6, f"Date: {md.date.isoformat()}    Domain: {checklist.domain}")
    if md.notes:
        _line(pdf, 6, f"Notes: {md.notes}")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    _line(pdf, 8, "Summary of Tacit Knowledge")
    pdf.set_font("Helvetica", "", 10)
    _line(pdf, 6, checklist.summary_of_tacit_knowledge)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    _line(pdf, 8, "Steps")
    for step in checklist.steps:
        flag = " [COMPLIANCE-CRITICAL]" if step.is_compliance_critical else ""
        pdf.set_font("Helvetica", "B", 10)
        _line(pdf, 6, f"{step.step_number}. {step.action_name} ({step.actor_role}){flag}")
        pdf.set_font("Helvetica", "", 10)
        _line(pdf, 6, step.description)
        if step.deterministic_rule:
            _line(pdf, 6, f"Rule: {step.deterministic_rule}")
        pdf.ln(2)

    if checklist.identified_risks:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 13)
        _line(pdf, 8, "Identified Risks")
        pdf.set_font("Helvetica", "", 10)
        for risk in checklist.identified_risks:
            _line(pdf, 6, f"- {risk}")

    return bytes(pdf.output())
