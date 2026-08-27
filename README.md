# SME Logic

SME Logic is a proof-of-concept pipeline that ingests unstructured SME notes, interview transcripts or draft SOPs and transforms them into validated compliance checklists, workflows and knowledge base entries. Using Claude AI for structured extraction, the system reconstructs messy field knowledge into machine-readable workflows - complete with identified risks, compliance flags and explicit capture of tacit operational habits.


## Overview

Enterprise operations depend on tacit knowledge - procedures, workarounds and safety habits that live in the heads of experienced Subject Matter Experts (SMEs) and get lost when they leave. Most SOPs document only the official process; the hidden wisdom that keeps operations safe and efficient stays unwritten and is unavailable for use in the knowledge bases that power AI solutions. Loss or lack of documentation of this tacit knowledge represents a company's intellectual property that is not being fully leveraged.

## Key features

- Deterministic, schema-first extraction using Pydantic models and Anthropic's `messages.parse()` API.
- Intake from pasted text, `.docx`, or `.pdf` (text-layer only — scanned/image-based PDFs aren't supported).
- User-entered metadata (title, date, notes) captured on the intake form and carried through to export.
- Export a completed workflow as Markdown or PDF.
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
- python-docx, pypdf (file intake parsing)
- fpdf2 (PDF export)
- React + TypeScript + Tailwind (frontend/)
- python-dotenv for environment variables

## Environment variables

Create a `.env` file at the repository root and set the following variables (do not commit `.env`):

- `ANTHROPIC_API_KEY` — your Anthropic API key (e.g., `sk-...`). Required for any live extraction smoke tests.
- `BACKEND_PORT` — optional, port for the FastAPI app when run via `python -m app.main` (default: `8000`). If you invoke `uvicorn` directly instead, pass `--port` on the command line — it won't read this variable.
- `FRONTEND_URL` — optional, restricts CORS to a single origin (e.g. `http://localhost:5173`) instead of the local-dev default of `*`.

Note: In production, protect the `/api/v1/ingest` endpoint behind your auth layer; the Anthropic key is only used server-side by the ingestion service.

## Quickstart

Assumptions:
- You have Python 3.11+ and Node.js installed.
- API keys (Anthropic) will be stored in a `.env` file at the repo root.

1. Backend: install Python dependencies

   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` with your Anthropic key:

   ```bash
   ANTHROPIC_API_KEY=sk-...
   ```

3. Run the backend locally

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. Run the frontend

   ```bash
   cd frontend && npm install && npm run dev
   ```

5. Run tests

   ```bash
   pytest
   ```

6. Manual live-API smoke test (optional)

   ```bash
   python -m app.services.ingestion_service
   ```

## API

### `POST /api/v1/ingest`

Accepts a `multipart/form-data` request — the intake form's metadata fields, plus either pasted text or an uploaded file (never both).

| Field      | Type          | Required | Notes                                              |
|------------|---------------|----------|-----------------------------------------------------|
| `title`    | string        | yes      | Workflow title                                      |
| `date`     | string (ISO)  | yes      | e.g. `2026-08-20`                                   |
| `notes`    | string        | no       |                                                      |
| `raw_text` | string        | one of `raw_text` / `file` | Pasted transcript text                |
| `file`     | file          | one of `raw_text` / `file` | `.docx` or `.pdf`, text-layer only    |

Request (curl, pasted text):

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "title=Cold Chain Intake QC" \
  -F "date=2026-08-20" \
  -F "notes=Interview with Maria Chen" \
  -F "raw_text=So basically when a shipment comes in, first thing is scanning the barcode..."
```

Request (curl, file upload):

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "title=Cold Chain Intake QC" \
  -F "date=2026-08-20" \
  -F "file=@transcript.pdf"
```

Response (`WorkflowResult`):

```json
{
  "metadata": {
    "title": "Cold Chain Intake QC",
    "date": "2026-08-20",
    "notes": "Interview with Maria Chen"
  },
  "checklist": {
    "workflow_name": "Cold Chain Shipment Intake",
    "domain": "Life Sciences",
    "summary_of_tacit_knowledge": "Technicians shake-test boxes before opening, an unwritten habit learned from prior bad shipments.",
    "steps": [
      {
        "step_number": 1,
        "action_name": "Scan Barcode",
        "description": "Scan the shipment barcode into the LIMS system.",
        "actor_role": "Lab Tech",
        "is_compliance_critical": false,
        "deterministic_rule": null
      }
    ],
    "identified_risks": [
      "Only one technician is certified on the new logger reader."
    ]
  }
}
```

Errors: `400` for missing/conflicting intake fields or an unreadable/unsupported file; `502` if the Anthropic extraction pipeline fails (refusal, truncation, or SDK error — see PRD.md).

### `POST /api/v1/export/markdown` and `POST /api/v1/export/pdf`

Accept a JSON body shaped like the `WorkflowResult` returned by `/api/v1/ingest` (i.e. re-post what you got back, possibly after edits) and return the rendered file as a download (`Content-Disposition: attachment`).

```bash
curl -X POST http://localhost:8000/api/v1/export/markdown \
  -H "Content-Type: application/json" \
  -d @workflow_result.json \
  -o workflow.md
```

## Project layout (high level)

- app/
  - main.py — FastAPI app, CORS setup, ingest + export routes
  - services/ingestion_service.py — Anthropic client, parse logic, prompt caching
  - services/file_extraction.py — `.docx`/`.pdf` text extraction for file uploads
  - services/export_service.py — Markdown/PDF rendering for workflow export
  - prompts/ — prompt templates and examples
  - schemas/ — Pydantic models used for validated extraction and API contracts
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
- Large intake sources (e.g. PDF/docx transcripts) can produce a checklist whose JSON gets truncated at `max_tokens` before `client.messages.parse()` can validate it — this raises a `pydantic.ValidationError` directly, before any `response.stop_reason` is available, so it's caught separately in `ingestion_service.py` and surfaced as a `502`.

## Contributing

This repository follows a conservative change policy: keep changes surgical and limited to the request at hand. See CLAUDE.md for project-specific behavioral guidelines intended to reduce common LLM coding mistakes.

## License

TBD
