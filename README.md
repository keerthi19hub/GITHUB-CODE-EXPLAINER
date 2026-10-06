---
title: GitHub Repository Code Explainer
emoji: 🔎
sdk: docker
app_port: 8501
---

# GitHub Repository Code Explainer

A Streamlit GenAI application that accepts any public HTTPS GitHub repository, clones it safely with GitPython, inventories its files, selects a representative evidence-based context, and generates a beginner-friendly explanation with **HuggingFaceTB/SmolLM2-135M-Instruct** using local Transformers inference inside the application runtime.

## Streamlit deployment

- Repository: `pragathidevanga/GitHub-Code_Explainer`
- Branch: `main`
- Main file: `app.py`
- Secrets: none
- Run locally: `streamlit run app.py`

No Ollama, ngrok, cloudflared, external backend, or cloud LLM API is required.

## Architecture

Streamlit `app.py` → reusable backend service → GitPython repository analyzer → smart context → Transformers model → explanation.

FastAPI, Pydantic, and Uvicorn remain available in `backend/` for optional local API testing and use the same service functions. Streamlit Cloud does not start a separate FastAPI server.

## Security

The analyzer never executes repository code or notebook cells. Sensitive files are classified but their contents are excluded from model context. Binary assets are inventoried without sending raw bytes to the text model.
