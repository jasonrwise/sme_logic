from datetime import date

from app.schemas.workflow import ComplianceChecklist, WorkflowMetadata, WorkflowResult, WorkflowStep
from app.services.export_service import render_markdown, render_pdf


def _fake_result() -> WorkflowResult:
    checklist = ComplianceChecklist(
        workflow_name="Cold Chain Intake QC",
        domain="Life Sciences",
        summary_of_tacit_knowledge="Technicians shake-test boxes before opening.",
        steps=[
            WorkflowStep(
                step_number=1,
                action_name="Scan Barcode",
                description="Scan the shipment barcode into the LIMS system.",
                actor_role="Lab Tech",
                is_compliance_critical=True,
                deterministic_rule="Temperature must stay below 8°C",
            )
        ],
        identified_risks=["Only one technician is certified on the new logger reader."],
    )
    metadata = WorkflowMetadata(title="Cold Chain Intake", date=date(2026, 8, 20), notes="Draft pass")
    return WorkflowResult(metadata=metadata, checklist=checklist)


def test_render_markdown_includes_metadata_and_steps():
    md = render_markdown(_fake_result())

    assert "# Cold Chain Intake" in md
    assert "2026-08-20" in md
    assert "Draft pass" in md
    assert "Scan Barcode" in md
    assert "⚠ Compliance-critical" in md
    assert "Only one technician is certified" in md


def test_render_pdf_returns_pdf_bytes():
    pdf_bytes = render_pdf(_fake_result())

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 0


def test_render_pdf_handles_non_latin1_characters_without_raising():
    result = _fake_result()
    result.checklist.summary_of_tacit_knowledge = "Unicode test: — ‘quoted’ … ☃"
    pdf_bytes = render_pdf(result)
    assert pdf_bytes.startswith(b"%PDF")
