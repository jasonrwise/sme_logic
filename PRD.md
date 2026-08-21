# Project: SME Logic Ingestion & Workflow Schema Agent

## Role & Objectives
You are an elite, full-stack software engineer and senior technical architect assisting a Forward Deployed AI Product Manager (FDPM). 
The goal of this project is to build an enterprise-grade proof of concept that ingests unstructured, messy SME notes/transcripts and deterministically transforms them into structured, validated JSON workflow schemas and compliance checklists.

## Technology Stack
- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2
- **AI Orchestration & LLM Client:** Anthropic Python SDK (`anthropic`), Claude Opus 5 (`claude-opus-5`) as the default extraction model; Claude Sonnet 5 (`claude-sonnet-5`) for high-volume/cost-sensitive passes
- **Frontend / Scaffolding:** React (via v0 / Tailwind CSS / shadcn/ui) — decided over Streamlit; lives in a separate `/frontend` directory and talks to the FastAPI backend over the CORS-enabled `/api/v1` routes.
- **Environment Management:** `python-dotenv` for API key handling (keys stored strictly in `.env`)

## Architectural & Code Standards
1. **Deterministic Guardrails:** Never return raw, unvalidated markdown or open-ended strings for workflow actions. Always enforce structured outputs using Pydantic models — use `client.messages.parse(..., output_format=MySchema)` and read `response.parsed_output`, which validates the response against the schema server-side. Do NOT use assistant-message prefilling (`{"role": "assistant", "content": "{"}`) to force JSON: it returns a 400 on current models.
2. **Explicit Error Handling:** Wrap all model calls and schema validations in try/catch blocks. Log any stochastic variance or JSON parsing failures cleanly. With `messages.parse()` the schema is enforced server-side, so the real failure modes are **stop reasons, not parse errors** — check `response.stop_reason` before touching `parsed_output`:
   - `"refusal"` — a safety classifier declined the request; `parsed_output` will not conform to the schema. Inspect `response.stop_details.category` for the reason and surface it; do not retry the identical prompt.
   - `"max_tokens"` — output was truncated, so the JSON is incomplete. Raise `max_tokens` and retry rather than attempting to repair the fragment.
   - Catch a **chain** of typed SDK exceptions, most-specific first, so retryable and non-retryable failures stay distinguishable: `anthropic.NotFoundError` (bad model ID) → `anthropic.RateLimitError` (back off; the SDK already retries twice) → `anthropic.APIStatusError` (other non-2xx) → `anthropic.APIConnectionError` (network). A single broad `except Exception` collapses all of these and is not acceptable here.
3. **Modularity:** Keep API routers, Pydantic schemas, and LLM prompt templates decoupled:
   - `/app/schemas/` -> Pydantic models
   - `/app/prompts/` -> Jinja2 or formatted string prompt templates
   - `/app/services/` -> Anthropic API client and parser logic
   - `/app/main.py` -> FastAPI endpoints and CORS setup
4. **No Secrets in Repo:** Never hardcode API keys. Always load `ANTHROPIC_API_KEY` via `os.getenv()`.
5. **Prompt Caching (ingestion cost control):** The extraction prompt is a large, stable prefix (schema description + extraction rules + few-shot examples) run against many different SME transcripts — the ideal caching shape. Cache the prefix and keep the transcript after it:
   - Caching is a **prefix match** over the rendered order `tools` → `system` → `messages`. Put everything stable in `system` with `cache_control={"type": "ephemeral"}` on the last system block; the per-request transcript goes in the user turn, after the breakpoint.
   - **Never interpolate volatile values into the system prompt** — `datetime.now()`, a UUID, a session/transcript ID, or `json.dumps()` without `sort_keys=True` changes the prefix bytes and silently invalidates the cache for every request. This is the single most common way caching quietly stops working.
   - Keep the tool list and model fixed for a given pipeline run. Tools render at position 0, so adding, removing, or reordering one invalidates everything; caches are also model-scoped.
   - Minimum cacheable prefix is **512 tokens on `claude-opus-5`** and **1024 on `claude-sonnet-5`**. Below that it silently will not cache — no error, just `cache_creation_input_tokens: 0`.
   - **Verify, don't assume:** assert `response.usage.cache_read_input_tokens > 0` on the second and later requests of a batch. If it stays 0, a silent invalidator is in the prefix.

## Testing Strategy
1. **Unit tests (`/tests`, pytest):** Mock the Anthropic client so schema validation, error-handling branches (refusal, max_tokens, each typed exception), and prompt-assembly logic are verified deterministically, for free, and safely in CI — no live API calls in the automated suite.
2. **Manual live-API smoke script (`app/services/ingestion_service.py` `__main__` block, or a dedicated `scripts/` entry):** Runs one real request against a sanitized sample SME transcript to sanity-check end-to-end behavior and confirm prompt caching is actually hitting (`cache_read_input_tokens > 0` on the second run). Sample transcripts are sanitized fixtures committed under version control (never real client data — see `.gitignore`'s `data/`/`outputs/` exclusion).

## Terminal & Workflow Commands
- Run backend locally: `uvicorn app.main:app --reload --port 8000`
- Install backend dependencies: `pip install -r requirements.txt`
- Run backend tests: `pytest`
- Run manual ingestion smoke test: `python -m app.services.ingestion_service`
- Run frontend locally: `cd frontend && npm run dev`