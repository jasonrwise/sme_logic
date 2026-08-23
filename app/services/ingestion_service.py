import logging
import os

import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from app.prompts.extraction import SYSTEM_PROMPT
from app.schemas.workflow import ComplianceChecklist

load_dotenv()

logger = logging.getLogger(__name__)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-opus-5"
# Larger intake sources (e.g. PDF/docx transcripts) can produce checklists
# with many steps; too low a ceiling here is the most common cause of the
# ValidationError handled below (see _call_model).
MAX_OUTPUT_TOKENS = 8192


class IngestionError(Exception):
    """Raised when the extraction pipeline cannot produce a valid ComplianceChecklist."""


def _call_model(raw_notes: str):
    """Make the underlying Anthropic call and return the raw parsed response.

    Catches the typed SDK exception chain (most-specific first) and re-raises
    everything as IngestionError so callers only need to handle one error type.
    See PRD.md standard #2.
    """
    try:
        return client.messages.parse(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"Here are the raw SME notes to standardize:\n\n{raw_notes}",
                }
            ],
            output_format=ComplianceChecklist,
        )
    except ValidationError as e:
        # client.messages.parse() validates the model's JSON internally and
        # raises here directly if it doesn't parse — most commonly because
        # output was truncated at max_tokens before the JSON closed. This
        # happens before we ever get a response object back, so the
        # stop_reason=="max_tokens" check in parse_sme_notes never runs for
        # this case; it must be caught here instead.
        logger.error("Model output failed schema validation (likely truncated JSON): %s", e)
        raise IngestionError(
            "Model output could not be parsed as valid JSON — this usually means the "
            f"response was truncated before completing (max_tokens={MAX_OUTPUT_TOKENS}). "
            "Try a shorter/smaller input, or raise MAX_OUTPUT_TOKENS if this persists."
        ) from e
    except anthropic.NotFoundError as e:
        logger.error("Anthropic model not found: %s", e)
        raise IngestionError(f"Model not found: {e}") from e
    except anthropic.RateLimitError as e:
        logger.warning("Anthropic rate limit hit: %s", e)
        raise IngestionError(f"Rate limited by Anthropic API: {e}") from e
    except anthropic.APIStatusError as e:
        logger.error("Anthropic API returned an error status: %s", e)
        raise IngestionError(f"Anthropic API error ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        logger.error("Failed to reach Anthropic API: %s", e)
        raise IngestionError(f"Could not reach Anthropic API: {e}") from e


def parse_sme_notes(raw_notes: str) -> ComplianceChecklist:
    response = _call_model(raw_notes)

    # messages.parse() enforces the schema server-side, so the real failure
    # modes are stop reasons, not parse errors — check before touching
    # parsed_output. See PRD.md standard #2.
    if response.stop_reason == "refusal":
        category = response.stop_details.category if response.stop_details else None
        logger.error("Anthropic refused the request (category=%s)", category)
        raise IngestionError(
            f"Request was refused by the model's safety classifier (category: {category})."
        )
    if response.stop_reason == "max_tokens":
        logger.error("Response truncated at max_tokens")
        raise IngestionError(
            "Response was truncated at max_tokens; raise max_tokens and retry rather than "
            "repairing the fragment."
        )

    return response.parsed_output


if __name__ == "__main__":
    # Manual smoke test against the real API (PRD.md Testing Strategy).
    # Run: python -m app.services.ingestion_service
    from pathlib import Path

    fixture_path = (
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "sample_transcript.txt"
    )
    sample_notes = fixture_path.read_text()

    print("First call (cold cache)...")
    response_1 = _call_model(sample_notes)
    print(f"cache_read_input_tokens: {response_1.usage.cache_read_input_tokens}")
    print(response_1.parsed_output.model_dump_json(indent=2))

    print("\nSecond call (should hit cache)...")
    response_2 = _call_model(sample_notes)
    cache_read = response_2.usage.cache_read_input_tokens
    print(f"cache_read_input_tokens: {cache_read}")

    assert cache_read > 0, (
        "Expected cache_read_input_tokens > 0 on the second call — the system "
        "prompt prefix may be under the cacheable minimum or a silent invalidator "
        "is present. See PRD.md standard #5."
    )
    print("\n✅ Prompt caching verified.")
