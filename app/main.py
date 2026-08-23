import os
import re
from datetime import date

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.services.export_service import render_markdown, render_pdf
from app.services.file_extraction import FileExtractionError, extract_text
from app.services.ingestion_service import parse_sme_notes, IngestionError
from app.schemas.workflow import WorkflowMetadata, WorkflowResult

app = FastAPI(title="SME Logic Ingestion Agent API", version="1.0.0")

# Enable CORS for local v0/React prototyping.
# FRONTEND_URL restricts this to a single known origin (e.g. in a deployed
# environment); unset, it falls back to "*" for local dev convenience.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
    return slug or "workflow"


@app.post("/api/v1/ingest", response_model=WorkflowResult)
async def ingest_notes(
    title: str = Form(...),
    date: date = Form(...),
    notes: str | None = Form(None),
    raw_text: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    has_text = bool(raw_text and raw_text.strip())
    has_file = bool(file and file.filename)

    if has_text and has_file:
        raise HTTPException(
            status_code=400, detail="Provide either pasted text or a file upload, not both."
        )
    if not has_text and not has_file:
        raise HTTPException(status_code=400, detail="Provide pasted text or upload a file.")

    if has_file:
        content = await file.read()
        try:
            source_text = extract_text(file.filename, content)
        except FileExtractionError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        source_text = raw_text

    try:
        checklist = parse_sme_notes(source_text)
    except IngestionError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    metadata = WorkflowMetadata(title=title, date=date, notes=notes)
    return WorkflowResult(metadata=metadata, checklist=checklist)


@app.post("/api/v1/export/markdown")
async def export_markdown(payload: WorkflowResult):
    content = render_markdown(payload)
    filename = f"{_slugify(payload.metadata.title)}.md"
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/v1/export/pdf")
async def export_pdf(payload: WorkflowResult):
    content = render_pdf(payload)
    filename = f"{_slugify(payload.metadata.title)}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    # Alternative to `uvicorn app.main:app --reload --port <N>`: honors
    # BACKEND_PORT so the value documented in the README is real.
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("BACKEND_PORT", 8000)), reload=True)
