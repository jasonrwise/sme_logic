from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.workflow import ComplianceChecklist
from app.services.ingestion_service import IngestionError
from app.services.file_extraction import FileExtractionError

client = TestClient(app)


def _fake_checklist() -> ComplianceChecklist:
    return ComplianceChecklist(
        workflow_name="Cold Chain Intake QC",
        domain="Life Sciences",
        summary_of_tacit_knowledge="Technicians shake-test boxes before opening.",
        steps=[],
        identified_risks=[],
    )


def _fake_metadata_form():
    return {"title": "Cold Chain Intake", "date": "2026-08-20", "notes": "Draft pass"}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ingest_missing_text_and_file_returns_400():
    response = client.post("/api/v1/ingest", data=_fake_metadata_form())
    assert response.status_code == 400


def test_ingest_blank_text_returns_400():
    response = client.post(
        "/api/v1/ingest", data={**_fake_metadata_form(), "raw_text": "   "}
    )
    assert response.status_code == 400


@patch("app.main.parse_sme_notes")
def test_ingest_happy_path_with_pasted_text(mock_parse):
    mock_parse.return_value = _fake_checklist()

    response = client.post(
        "/api/v1/ingest",
        data={**_fake_metadata_form(), "raw_text": "some raw SME notes"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["checklist"]["workflow_name"] == "Cold Chain Intake QC"
    assert body["metadata"] == {
        "title": "Cold Chain Intake",
        "date": "2026-08-20",
        "notes": "Draft pass",
    }


@patch("app.main.parse_sme_notes")
def test_ingest_happy_path_with_file_upload(mock_parse):
    mock_parse.return_value = _fake_checklist()

    with patch("app.main.extract_text", return_value="extracted transcript text") as mock_extract:
        response = client.post(
            "/api/v1/ingest",
            data=_fake_metadata_form(),
            files={"file": ("notes.docx", b"fake docx bytes", "application/octet-stream")},
        )

    assert response.status_code == 200
    mock_extract.assert_called_once_with("notes.docx", b"fake docx bytes")
    mock_parse.assert_called_once_with("extracted transcript text")


def test_ingest_rejects_both_text_and_file():
    response = client.post(
        "/api/v1/ingest",
        data={**_fake_metadata_form(), "raw_text": "some notes"},
        files={"file": ("notes.docx", b"fake docx bytes", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_ingest_unsupported_file_type_returns_400():
    with patch("app.main.extract_text", side_effect=FileExtractionError("Unsupported file type")):
        response = client.post(
            "/api/v1/ingest",
            data=_fake_metadata_form(),
            files={"file": ("notes.txt", b"plain text", "text/plain")},
        )
    assert response.status_code == 400


@patch("app.main.parse_sme_notes")
def test_ingest_ingestion_error_returns_502(mock_parse):
    mock_parse.side_effect = IngestionError("boom")

    response = client.post(
        "/api/v1/ingest",
        data={**_fake_metadata_form(), "raw_text": "some raw SME notes"},
    )

    assert response.status_code == 502


def _fake_workflow_result_payload():
    return {
        "metadata": {"title": "Cold Chain Intake", "date": "2026-08-20", "notes": "Draft pass"},
        "checklist": _fake_checklist().model_dump(mode="json"),
    }


def test_export_markdown_returns_downloadable_file():
    response = client.post("/api/v1/export/markdown", json=_fake_workflow_result_payload())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "cold-chain-intake.md" in response.headers["content-disposition"]
    assert "Cold Chain Intake" in response.text


def test_export_pdf_returns_downloadable_file():
    response = client.post("/api/v1/export/pdf", json=_fake_workflow_result_payload())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "cold-chain-intake.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
