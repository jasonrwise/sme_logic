from types import SimpleNamespace
from unittest.mock import MagicMock

import anthropic
import httpx
import pytest

from app.schemas.workflow import ComplianceChecklist
from app.services import ingestion_service
from app.services.ingestion_service import IngestionError, parse_sme_notes

SAMPLE_NOTES = "Some raw SME notes about a cold chain QC process."


def _fake_checklist() -> ComplianceChecklist:
    return ComplianceChecklist(
        workflow_name="Cold Chain Intake QC",
        domain="Life Sciences",
        summary_of_tacit_knowledge="Technicians shake-test boxes before opening.",
        steps=[
            {
                "step_number": 1,
                "action_name": "Scan Barcode",
                "description": "Scan the shipment barcode into the LIMS system.",
                "actor_role": "Lab Tech",
                "is_compliance_critical": False,
                "deterministic_rule": None,
            }
        ],
        identified_risks=["Only one technician is certified on the new logger reader."],
    )


def _mock_response(stop_reason="end_turn", parsed_output=None, stop_details=None):
    return SimpleNamespace(
        stop_reason=stop_reason, parsed_output=parsed_output, stop_details=stop_details
    )


def _api_status_error(exc_cls, status_code):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code, request=request)
    return exc_cls("boom", response=response, body=None)


def _api_connection_error():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIConnectionError(message="boom", request=request)


def test_parse_sme_notes_happy_path(monkeypatch):
    expected = _fake_checklist()
    mock_parse = MagicMock(return_value=_mock_response(parsed_output=expected))
    monkeypatch.setattr(ingestion_service.client.messages, "parse", mock_parse)

    result = parse_sme_notes(SAMPLE_NOTES)

    assert result == expected
    mock_parse.assert_called_once()
    # System prompt must be cacheable — assert the breakpoint is present.
    _, kwargs = mock_parse.call_args
    assert kwargs["system"][-1]["cache_control"] == {"type": "ephemeral"}


def test_parse_sme_notes_refusal_raises(monkeypatch):
    stop_details = SimpleNamespace(category="cyber")
    mock_parse = MagicMock(
        return_value=_mock_response(stop_reason="refusal", stop_details=stop_details)
    )
    monkeypatch.setattr(ingestion_service.client.messages, "parse", mock_parse)

    with pytest.raises(IngestionError, match="refused"):
        parse_sme_notes(SAMPLE_NOTES)


def test_parse_sme_notes_max_tokens_raises(monkeypatch):
    mock_parse = MagicMock(return_value=_mock_response(stop_reason="max_tokens"))
    monkeypatch.setattr(ingestion_service.client.messages, "parse", mock_parse)

    with pytest.raises(IngestionError, match="max_tokens"):
        parse_sme_notes(SAMPLE_NOTES)


def test_parse_sme_notes_truncated_json_raises(monkeypatch):
    # client.messages.parse() validates the model's JSON internally and
    # raises ValidationError directly (rather than returning a response with
    # stop_reason="max_tokens") when the output is truncated mid-JSON — the
    # failure mode this test reproduces.
    with pytest.raises(Exception) as truncation_exc_info:
        ComplianceChecklist.model_validate_json('{"workflow_name": "Truncated')

    mock_parse = MagicMock(side_effect=truncation_exc_info.value)
    monkeypatch.setattr(ingestion_service.client.messages, "parse", mock_parse)

    with pytest.raises(IngestionError, match="truncated"):
        parse_sme_notes(SAMPLE_NOTES)


@pytest.mark.parametrize(
    "make_exc",
    [
        lambda: _api_status_error(anthropic.NotFoundError, 404),
        lambda: _api_status_error(anthropic.RateLimitError, 429),
        lambda: _api_status_error(anthropic.APIStatusError, 400),
        lambda: _api_connection_error(),
    ],
    ids=["not_found", "rate_limit", "api_status", "connection"],
)
def test_parse_sme_notes_sdk_errors_raise_ingestion_error(monkeypatch, make_exc):
    mock_parse = MagicMock(side_effect=make_exc())
    monkeypatch.setattr(ingestion_service.client.messages, "parse", mock_parse)

    with pytest.raises(IngestionError):
        parse_sme_notes(SAMPLE_NOTES)
