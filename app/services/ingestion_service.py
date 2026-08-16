import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv
from app.schemas.workflow import ComplianceChecklist

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """
You are an expert Forward Deployed AI Systems Architect specializing in workflow reconstruction.
Your task is to ingest messy, unstructured transcripts, interview notes, or rough SOP drafts provided by enterprise Subject Matter Experts (SMEs).

Analyze the input carefully to:
1. Extract implicit, undocumented operational habits ("tacit knowledge") that veteran operators perform but often forget to document.
2. Structure the core workflow into a clean, chronological sequence of executable steps.
3. Identify potential regulatory, operational, or compliance failure points.

You must output your findings by invoking the `extract_compliance_checklist` tool.
"""

def parse_sme_notes(raw_notes: str) -> ComplianceChecklist:
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        temperature=0.1,  # Low temperature for deterministic output
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user", 
                "content": f"Here are the raw SME notes to standardize:\n\n{raw_notes}"
            }
        ],
        tools=[
            {
                "name": "extract_compliance_checklist",
                "description": "Standardizes unstructured SME operational procedures into a validated compliance workflow.",
                "input_schema": ComplianceChecklist.model_json_schema()
            }
        ],
        tool_choice={"type": "tool", "name": "extract_compliance_checklist"}
    )
    
    # Extract tool call arguments
    for content_block in response.content:
        if content_block.type == "tool_use" and content_block.name == "extract_compliance_checklist":
            validated_output = ComplianceChecklist(**content_block.input)
            return validated_output

    raise ValueError("Failed to extract structured compliance checklist from LLM response.")