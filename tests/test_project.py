from pathlib import Path
import json
import tempfile

from backend.main import app
from fastapi.testclient import TestClient
from backend.service import analyze_repository
from llm_service import build_prompt, get_model_name
from repo_processor import RepositoryProcessingError, RepositoryProcessor

ROOT = Path(__file__).resolve().parents[1]


def test_root_files():
    assert (ROOT / "app.py").exists()
    assert (ROOT / "requirements.txt").exists()


def test_url_validation():
    assert RepositoryProcessor.validate_url("https://github.com/user/repo") == "https://github.com/user/repo.git"
    try:
        RepositoryProcessor.validate_url("http://github.com/user/repo")
        assert False
    except RepositoryProcessingError:
        pass


def test_classifier_and_inventory_categories():
    processor = RepositoryProcessor()
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "README.md").write_text("hello")
        (root / "main.py").write_text("print('x')")
        (root / "config.yaml").write_text("x: 1")
        (root / "data.csv").write_text("a,b\n1,2")
        (root / "image.png").write_bytes(b"\x89PNG\r\n")
        (root / ".env").write_text("TOKEN=secret")
        (root / "notebook.ipynb").write_text(json.dumps({"cells": [{"cell_type": "markdown", "source": ["# Title"]}, {"cell_type": "code", "source": ["print(1)"]}]}))
        records = processor._inventory(root)
        cats = {r.path: r.category for r in records}
        assert cats["README.md"] == "DOCUMENTATION"
        assert cats["main.py"] == "SOURCE"
        assert cats["config.yaml"] == "CONFIGURATION"
        assert cats["data.csv"] == "DATA/SCHEMA"
        assert cats["image.png"] == "BINARY/ASSET"
        assert cats[".env"] == "SENSITIVE"
        assert cats["notebook.ipynb"] == "NOTEBOOK"


def test_notebook_context_and_sensitive_protection():
    processor = RepositoryProcessor()
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        nb = root / "demo.ipynb"
        nb.write_text(json.dumps({"cells": [{"cell_type": "markdown", "source": ["# Demo"]}, {"cell_type": "code", "source": ["x = 1"]}]}))
        secret = root / ".env"
        secret.write_text("TOKEN=do-not-expose")
        records = processor._inventory(root)
        selected = processor._rank_files(records)
        context = processor._build_context(root, selected)
        assert "# Demo" in context
        assert "do-not-expose" not in context


def test_context_limit_and_no_duplicates():
    processor = RepositoryProcessor(max_total_context=1000, max_files_for_llm=10)
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for i in range(20):
            (root / f"file{i}.py").write_text("def function():\n    return 'x'\n" * 100)
        records = processor._inventory(root)
        selected = processor._rank_files(records)
        context = processor._build_context(root, selected)
        assert len(context) <= 1200
        headers = [line for line in context.splitlines() if line.startswith("=====")]
        assert len(headers) == len(set(headers))


def test_prompt_and_model_name():
    repository = {
        "repository_name": "demo", "repository_type": "Software/code project", "technologies": ["Python"],
        "file_inventory": [{"path": "README.md", "category": "DOCUMENTATION", "size_bytes": 10, "sensitive": False}],
        "folder_tree": ["README.md"], "code_context": "print('hello')"
    }
    prompt = build_prompt(repository)
    assert "Use ONLY the supplied repository evidence" in prompt
    assert get_model_name() == "HuggingFaceTB/SmolLM2-135M-Instruct"


def test_fastapi_routes():
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/docs").status_code == 200


def test_streamlit_entrypoint_has_no_external_backend():
    text = (ROOT / "app.py").read_text()
    assert "BACKEND_URL" not in text
    assert "OLLAMA" not in text
    assert "ngrok" not in text.lower()
    assert "streamlit run" not in text.lower()
