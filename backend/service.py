"""
backend/service.py
==================
Shared service layer that coordinates repository cloning, file analysis,
and AI explanation generation.

This service is called directly by Streamlit (allowing the app to be completely
self-contained without requiring a separate FastAPI process), and can also be
used by the FastAPI endpoints for local API testing.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from llm_service import generate_explanation
from repo_processor import RepositoryProcessor

ProgressCallback = Callable[[str], None] | None


def analyze_repository(url: str, progress: ProgressCallback = None) -> dict[str, Any]:
    """
    Coordinates the full repository analysis workflow:
    1-6. Validating URL, cloning, scanning, classifying, detecting technologies, building context.
    7. Generating AI explanation with the open-source model.
    8. Finalizing report.
    """
    processor = RepositoryProcessor()
    result = processor.process(url, progress=progress)

    if progress:
        progress("7. Generating AI explanation")
    t = time.perf_counter()
    explanation = generate_explanation(result)
    result["explanation"] = explanation
    result["timings"]["model_inference"] = time.perf_counter() - t
    result["timings"]["total"] = sum(v for k, v in result["timings"].items() if k != "total")

    if progress:
        progress("8. Finalizing report")
    return result
