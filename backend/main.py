from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

from backend.service import analyze_repository

app = FastAPI(title="GitHub Code Explainer API", version="2.0.0")


class ExplainRequest(BaseModel):
    repository_url: HttpUrl


@app.get("/")
def root():
    return {"message": "GitHub Code Explainer API is available for optional local API use."}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "github-code-explainer"}


@app.post("/api/explain")
def explain(request: ExplainRequest):
    try:
        return analyze_repository(str(request.repository_url))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
