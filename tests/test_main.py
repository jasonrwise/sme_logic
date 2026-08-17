from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.workflow import ComplianceChecklist
from app.services.ingestion_service import IngestionError

client = TestClient(app)


def _fake_checklist() -> ComplianceChecklist:
    return ComplianceChecklist(
        workflow_name="Cold Chain Intake QC",
        domain="Life Sciences",
        summary_of_tacit_knowledge="Technicians shake-test boxes before opening.",
        steps=[],
        identified_risks=[],
    )


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ingest_empty_text_returns_400():
    response = client.post("/api/v1/ingest", json={"raw_text": "   "})
    assert response.status_code == 400


@patch("app.main.parse_sme_notes")
def test_ingest_happy_path(mock_parse):
    mock_parse.return_value = _fake_checklist()

    response = client.post("/api/v1/ingest", json={"raw_text": "some raw SME notes"})

    assert response.status_code == 200
    assert response.json()["workflow_name"] == "Cold Chain Intake QC"


@patch("app.main.parse_sme_notes")
def test_ingest_ingestion_error_returns_502(mock_parse):
    mock_parse.side_effect = IngestionError("boom")

    response = client.post("/api/v1/ingest", json={"raw_text": "some raw SME notes"})

    assert response.status_code == 502
