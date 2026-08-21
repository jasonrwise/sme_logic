# SME Logic

Take raw SME feedback and deterministically transform it into a structured, validated knowledge representation.

Status: Draft (Milestone 1: standards-compliant ingestion pipeline + React frontend)

## Overview

SME Logic is a proof-of-concept pipeline that ingests unstructured SME notes/transcripts and converts them into validated JSON workflow/schema artifacts using Claude (Anthropic) models. The goal is deterministic, auditable extraction with strong guardrails and prompt caching to reduce cost.

## Key features

- Deterministic, schema-first extraction using Pydantic models and Anthropic's `messages.parse()` API.
- Explicit, typed error handling for model refusals, truncation (max_tokens), and SDK exceptions.
- Prompt caching for cost control and repeatability (prefix caching recommendations in PRD).
- Backend: FastAPI + Uvicorn, Python 3.11+, Pydantic v2.
- Frontend: React (Vite + TypeScript + Tailwind) that talks to the FastAPI backend.
- Tests: pytest suite with mocked Anthropic client covering happy path and error branches.

## Tech stack

- Python 3.11+
- FastAPI, Uvicorn
- Pydantic v2
- Anthropic Python SDK (Claude Opus 5 default)
- React + TypeScript + Tailwind (frontend/)
- python-dotenv for environment variables

## Environment variables

Create a `.env` file at the repository root and set the following variables (do not commit `.env`):

- ANTHROPIC_API_KEY — your Anthropic API key (e.g., `sk-...`). Required for any live extraction smoke tests.
- BACKEND_PORT — optional, port for the FastAPI app (default: `8000`).
- FRONTEND_URL — optional, URL where the frontend is served during local development (used for CORS in `app.main`).

Note: In production, protect the `/api/v1/ingest` endpoint behind your auth layer; the Anthropic key is only used server-side by the ingestion service.

## Quickstart

Assumptions:
- You have Python 3.11+ and Node.js installed.
- API keys (Anthropic) will be stored in a `.env` file at the repo root.

1. Backend: install Python dependencies

   pip install -r requirements.txt

2. Create a `.env` with your Anthropic key:

   ANTHROPIC_API_KEY=sk-...

3. Run the backend locally

   uvicorn app.main:app --reload --port 8000

4. Run the frontend

   cd frontend && npm install && npm run dev

5. Run tests

   pytest

6. Manual live-API smoke test (optional)

   python -m app.services.ingestion_service

## API: /api/v1/ingest

This endpoint accepts a JSON POST with an SME transcript (or other unstructured text) and returns a validated extraction according to the project's Pydantic schemas.

Request (curl):

  curl -X POST http://localhost:8000/api/v1/ingest \
    -H "Content-Type: application/json" \
    -d '{"transcript": "The customer reported intermittent auth failures when using SSO. Steps to reproduce: ...", "metadata": {"source": "interview-2026-08-20"}}'

Request (TypeScript, fetch):

  // frontend/src/api/ingest.ts
  export async function ingest(transcript: string, metadata = {}) {
    const res = await fetch('/api/v1/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript, metadata }),
    });
    if (!res.ok) throw new Error(`ingest failed: ${res.status}`);
    return res.json();
  }

Example expected response (shape depends on `app/schemas`):

  {
    "id": "ingest_abc123",
    "schema_version": "1.0",
    "extraction": {
      "workflow": [...],
      "entities": [...],
      "complianceChecklist": {
        "items": [
          {"id": "c1", "title": "Require unique user IDs", "status": "pass"}
        ]
      }
    },
    "warnings": [],
    "_internal": {
      "model": "claude-opus-5",
      "stop_reason": null,
      "cache_read_input_tokens": 128
    }
  }

Notes:
- The precise JSON fields are defined in `/app/schemas/` and enforced by the server using `messages.parse()`.
- If the model refuses or truncates output, the server surface structured error information (see PRD.md for handling rules).

## Project layout (high level)

- app/
  - main.py — FastAPI app and CORS setup
  - services/ingestion_service.py — Anthropic client, parse logic, prompt caching
  - prompts/ — prompt templates and examples
  - schemas/ — Pydantic models used for validated extraction
- frontend/ — React + TypeScript + Tailwind UI
- tests/ — pytest tests (mocked SDK)
- PRD.md — product requirements and engineering guidance
- requirements.txt — runtime/test dependencies

## Important engineering guidelines (from PRD)

- Deterministic outputs: always use Pydantic models and `messages.parse()` to enforce structure.
- Error handling: surface `refusal` and `max_tokens` clearly; handle SDK exception chain with typed catches.
- Prompt caching: keep stable content in the system prompt, avoid volatile interpolations, and verify `response.usage.cache_read_input_tokens > 0` on repeat requests.
- No secrets in repo: use `.env` and `python-dotenv`.

## Running and troubleshooting

- To debug prompt caching or production extraction issues, consult `PRD.md` for exact caching rules (minimum cacheable prefix sizes and common invalidators).
- If a model call returns `stop_reason: "refusal"`, do not attempt naive retries — inspect stop details and surface the refusal.

## Contributing

This repository follows a conservative change policy: keep changes surgical and limited to the request at hand. See CLAUDE.md for project-specific behavioral guidelines intended to reduce common LLM coding mistakes.

## License

TBD
