from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.services.ingestion_service import parse_sme_notes
from app.schemas.workflow import ComplianceChecklist

app = FastAPI(title="SME Logic Ingestion Agent API", version="1.0.0")

# Enable CORS for local v0/React prototyping
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IngestionRequest(BaseModel):
    raw_text: str

@app.post("/api/v1/ingest", response_model=ComplianceChecklist)
async def ingest_notes(payload: IngestionRequest):
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")
    try:
        return parse_sme_notes(payload.raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}