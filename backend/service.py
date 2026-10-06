from __future__ import annotations

import time
from typing import Any, Callable

from llm_service import generate_explanation
from repo_processor import RepositoryProcessor


ProgressCallback = Callable[[str], None] | None


def analyze_repository(url: str, progress: ProgressCallback = None) -> dict[str, Any]:
    processor = RepositoryProcessor()
    result = processor.process(url, progress=progress)
    if progress:
        progress("07 Generating AI explanation")
    t = time.perf_counter()
    explanation = generate_explanation(result)
    result["explanation"] = explanation
    result["timings"]["model_inference"] = time.perf_counter() - t
    result["timings"]["total"] = sum(v for k, v in result["timings"].items() if k != "total")
    if progress:
        progress("08 Finalizing report")
    return result
