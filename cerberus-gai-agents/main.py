# main.py — Cerberus GAI Agents
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict
import os
import httpx

app = FastAPI(title="Cerberus GAI Agents", version="1.0.0")

# ===== Configuration (module-level so it's always defined) =====
# Overridable via environment variables in docker-compose.
RAG_BASE_URL    = os.getenv("RAG_BASE_URL", "http://cerberus-rag:8002")
RAG_PATH        = os.getenv("RAG_PATH", "/query")   # Your RAG exposes POST /query
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15"))  # seconds


# ===== Health endpoints =====
@app.get("/healthz")
def healthz() -> Dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> Dict[str, bool]:
    """Readiness probe – verifies the RAG dependency is reachable."""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(f"{RAG_BASE_URL}/healthz")
            r.raise_for_status()
        return {"ready": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"dependency not ready: {e}")


# ===== Helpers =====
async def forward_to_rag(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Forward a JSON payload to RAG and return its JSON response."""
    url = f"{RAG_BASE_URL}{RAG_PATH}"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        # Upstream returned non-2xx: surface that response text/status.
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        # Network/timeout/serialization errors.
        raise HTTPException(status_code=502, detail=f"RAG upstream error: {e}")


def extract_query(body: Dict[str, Any]) -> str:
    """
    Accept either {"query": "..."} or {"question": "..."} and return the string.
    Raises HTTP 4xx if invalid.
    """
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid JSON")
    q = body.get("query") or body.get("question")
    if not q or not isinstance(q, str):
        raise HTTPException(status_code=422, detail="missing 'query' or 'question'")
    return q


# ===== Main API =====
@app.post("/ask")
async def ask(req: Request):
    """
    Accepts: {"query": "...", "top_k": 2}  OR  {"question": "...", "top_k": 2}
    Forwards to RAG /query with {"question": "...", "top_k": ...} and returns RAG's JSON.
    """
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    question = extract_query(body)
    top_k = body.get("top_k", 2)
    if not isinstance(top_k, int) or top_k <= 0:
        raise HTTPException(status_code=422, detail="'top_k' must be a positive integer")

    # RAG expects "question"
    rag_payload = {"question": question, "top_k": top_k}
    data = await forward_to_rag(rag_payload)
    return JSONResponse(data)
