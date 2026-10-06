"""
tests/test_project.py
=====================
Test suite for the GitHub Repository Code Explainer.
Covers:
1. GitHub URL validation
2. File classification
3. Sensitive file protection
4. Notebook parsing without execution
5. Context size limits and smart excerpting
6. Technology detection from evidence
7. FastAPI health and root endpoints
8. Streamlit entrypoint independence (no external backend/Ollama dependency)
"""

import json
import sys
import tempfile
from pathlib import Path

# Ensure workspace root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.service import analyze_repository
from llm_service import build_prompt, get_model_name
from repo_processor import RepositoryProcessingError, RepositoryProcessor


def test_required_root_files_exist():
    """Verify that all core files are present in the repository root."""
    expected_files = [
        "app.py",
        "repo_processor.py",
        "llm_service.py",
        "requirements.txt",
        "runtime.txt",
        "README.md",
        ".gitignore",
    ]
    for filename in expected_files:
        assert (ROOT / filename).exists(), f"Missing required file: {filename}"


def test_github_url_validation():
    """Test 1: Validate GitHub URLs and error handling for invalid formats."""
    # Valid URLs
    assert RepositoryProcessor.validate_url("https://github.com/psf/requests") == "https://github.com/psf/requests.git"
    assert RepositoryProcessor.validate_url("https://github.com/psf/requests.git") == "https://github.com/psf/requests.git"
    assert RepositoryProcessor.validate_url("github.com/psf/requests") == "https://github.com/psf/requests.git"

    # Invalid URLs should raise RepositoryProcessingError
    with pytest.raises(RepositoryProcessingError):
        RepositoryProcessor.validate_url("")

    with pytest.raises(RepositoryProcessingError):
        RepositoryProcessor.validate_url("https://gitlab.com/user/project")

    with pytest.raises(RepositoryProcessingError):
        RepositoryProcessor.validate_url("https://github.com/incomplete")


def test_file_classification():
    """Test 2: Ensure correct classification of various repository file types."""
    processor = RepositoryProcessor()
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        (root / "README.md").write_text("# Project", encoding="utf-8")
        (root / "main.py").write_text("print('hello')", encoding="utf-8")
        (root / "app.js").write_text("console.log('hi')", encoding="utf-8")
        (root / "config.yaml").write_text("env: prod", encoding="utf-8")
        (root / "data.csv").write_text("id,name\n1,alice", encoding="utf-8")
        (root / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (root / ".env").write_text("SECRET_KEY=12345", encoding="utf-8")
        (root / "notebook.ipynb").write_text(
            json.dumps({"cells": [{"cell_type": "markdown", "source": ["# Title"]}]}),
            encoding="utf-8",
        )

        records = processor._inventory(root)
        categories = {r.path: r.category for r in records}

        assert categories["README.md"] == "DOCUMENTATION"
        assert categories["main.py"] == "SOURCE"
        assert categories["app.js"] == "SOURCE"
        assert categories["config.yaml"] == "CONFIGURATION"
        assert categories["data.csv"] == "DATA/SCHEMA"
        assert categories["photo.png"] == "BINARY/ASSET"
        assert categories[".env"] == "SENSITIVE"
        assert categories["notebook.ipynb"] == "NOTEBOOK"


def test_sensitive_file_protection():
    """Test 3: Verify sensitive file contents are strictly protected and never sent to context."""
    processor = RepositoryProcessor()
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        (root / ".env").write_text("SUPER_SECRET_PASSWORD=xyz_token_secret", encoding="utf-8")
        (root / "credentials.json").write_text('{"api_key": "private_secret"}', encoding="utf-8")
        (root / "main.py").write_text("print('safe code')", encoding="utf-8")

        records = processor._inventory(root)
        selected = processor._rank_files(records)
        context = processor._build_context(root, selected)

        # Sensitive content must NEVER appear in LLM context
        assert "SUPER_SECRET_PASSWORD" not in context
        assert "private_secret" not in context
        assert "safe code" in context


def test_notebook_parsing_without_execution():
    """Test 4: Extract cells from Jupyter notebooks safely without executing code."""
    processor = RepositoryProcessor()
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        nb_file = root / "analysis.ipynb"
        nb_data = {
            "cells": [
                {"cell_type": "markdown", "source": ["## Model Training Step"]},
                {"cell_type": "code", "source": ["model.fit(X, y)\nprint('Done')"]},
            ]
        }
        nb_file.write_text(json.dumps(nb_data), encoding="utf-8")

        records = processor._inventory(root)
        selected = processor._rank_files(records)
        context = processor._build_context(root, selected)

        assert "## Model Training Step" in context
        assert "model.fit(X, y)" in context


def test_context_size_limits():
    """Test 5: Verify that repository context stays strictly within budget limits."""
    max_context = 1500
    processor = RepositoryProcessor(max_total_context=max_context, max_files_for_llm=5)

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        for i in range(10):
            (root / f"module_{i}.py").write_text("def run_job():\n    return 42\n" * 50, encoding="utf-8")

        records = processor._inventory(root)
        selected = processor._rank_files(records)
        context = processor._build_context(root, selected)

        assert len(context) <= max_context + 200  # Allow slight margin for final truncated suffix


def test_technology_detection():
    """Test 6: Verify evidence-based technology detection from manifests and source code."""
    processor = RepositoryProcessor()
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        (root / "requirements.txt").write_text("flask==3.0.0\npandas>=2.0.0\n", encoding="utf-8")
        (root / "app.py").write_text("from flask import Flask\napp = Flask(__name__)", encoding="utf-8")

        records = processor._inventory(root)
        technologies = processor._detect_technologies(root, records)

        assert "Python" in technologies
        assert "Flask" in technologies


def test_fastapi_health_endpoint():
    """Test 7: Verify FastAPI service layer and health endpoints."""
    client = TestClient(app)
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    assert health_resp.json() == {"status": "ok", "service": "github-code-explainer"}

    root_resp = client.get("/")
    assert root_resp.status_code == 200


def test_streamlit_entrypoint_is_self_contained():
    """Test 8: Verify that Streamlit app is self-contained and does not rely on external servers."""
    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "BACKEND_URL" not in app_text
    assert "localhost:8000" not in app_text
    assert "127.0.0.1:8000" not in app_text
    assert "ollama" not in app_text.lower()
    assert "ngrok" not in app_text.lower()
    assert "cloudflared" not in app_text.lower()
    assert get_model_name() == "HuggingFaceTB/SmolLM2-135M-Instruct"
