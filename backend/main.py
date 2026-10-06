"""
backend/main.py
===============
FastAPI application providing a RESTful API layer for the repository explainer.

This file demonstrates backend API architecture and is useful for local API
development/testing, while the public Streamlit app uses backend/service.py
directly so no separate server process is required.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

from backend.service import analyze_repository

app = FastAPI(
    title="GitHub Code Explainer API",
    description="REST API for analyzing and explaining public GitHub repositories using local LLM inference.",
    version="1.0.0",
)


class ExplainRequest(BaseModel):
    repository_url: HttpUrl


@app.get("/")
def root():
    return {
        "title": "GitHub Code Explainer API",
        "status": "online",
        "description": "FastAPI service layer for GitHub repository code explanation",
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "github-code-explainer"}


@app.post("/api/explain")
def explain(request: ExplainRequest):
    try:
        return analyze_repository(str(request.repository_url))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
