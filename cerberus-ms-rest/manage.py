from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

class AskPayload(BaseModel):
    query: str
    top_k: int = 2

@app.post("/ask")
async def ask(payload: AskPayload):
    return {"echo": payload.query, "top_k": payload.top_k}
