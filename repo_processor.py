from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from git import Repo


class RepositoryProcessingError(Exception):
    """Friendly, expected repository-analysis error."""


@dataclass
class FileRecord:
    path: str
    category: str
    extension: str
    size_bytes: int
    language: str | None = None
    sensitive: bool = False
    readable: bool = False


LANGUAGE_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".java": "Java", ".c": "C", ".h": "C/C++ header", ".cpp": "C++", ".cc": "C++", ".hpp": "C++ header",
    ".cs": "C#", ".go": "Go", ".rs": "Rust", ".php": "PHP", ".rb": "Ruby", ".kt": "Kotlin", ".kts": "Kotlin",
    ".swift": "Swift", ".dart": "Dart", ".r": "R", ".R": "R", ".sql": "SQL", ".sh": "Shell", ".bash": "Shell",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "Sass", ".vue": "Vue", ".svelte": "Svelte",
}
SOURCE_EXTS = set(LANGUAGE_BY_EXT)
CONFIG_EXTS = {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf", ".xml", ".properties", ".env.example", ".editorconfig"}
DATA_EXTS = {".csv", ".tsv", ".jsonl", ".ndjson", ".parquet", ".db", ".sqlite", ".sqlite3"}
DOC_EXTS = {".md", ".markdown", ".rst", ".txt", ".adoc", ".textile"}
DEPENDENCY_NAMES = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    "pom.xml", "build.gradle", "build.gradle.kts", "gradle.properties", "cargo.toml", "go.mod",
    "go.sum", "composer.json", "gemfile", "gemfile.lock", "packages.config", "pubspec.yaml",
}
BUILD_NAMES = {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "makefile", "justfile"}
TEST_PARTS = {"test", "tests", "spec", "specs", "__tests__"}
SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development", "credentials", "credentials.json",
    "secrets.json", "secret.json", "id_rsa", "id_ed25519", "private.key", "private.pem",
}
IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules",
               "dist", "build", "target", ".idea", ".vscode", ".next", ".nuxt", "coverage"}
BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg", ".pdf", ".zip", ".tar", ".gz",
               ".7z", ".rar", ".exe", ".dll", ".so", ".dylib", ".bin", ".woff", ".woff2", ".ttf", ".otf", ".mp3",
               ".mp4", ".mov", ".avi", ".class", ".jar", ".pyc", ".pkl", ".npy", ".npz", ".parquet", ".db", ".sqlite", ".sqlite3"}

MAX_FILE_SIZE_FOR_CONTEXT = 30_000
MAX_TOTAL_CONTEXT = 50_000
MAX_FILES_FOR_LLM = 32


class RepositoryProcessor:
    """Safely clone and inspect public GitHub repositories without executing repository code."""

    def __init__(self, max_total_context: int = MAX_TOTAL_CONTEXT, max_files_for_llm: int = MAX_FILES_FOR_LLM):
        self.max_total_context = max_total_context
        self.max_files_for_llm = max_files_for_llm

    @staticmethod
    def validate_url(url: str) -> str:
        raw = url.strip()
        parsed = urlparse(raw)
        if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
            raise RepositoryProcessingError("Please enter a public HTTPS GitHub repository URL, for example https://github.com/user/repository")
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) < 2 or parts[0].startswith(".") or parts[1].startswith("."):
            raise RepositoryProcessingError("The GitHub URL must contain a valid username and repository name.")
        return f"https://github.com/{parts[0]}/{parts[1]}.git"

    def process(self, url: str, progress=None) -> dict[str, Any]:
        timings: dict[str, float] = {}
        start_total = time.perf_counter()
        t = time.perf_counter()
        clone_url = self.validate_url(url)
        timings["validation"] = time.perf_counter() - t
        if progress:
            progress("01 Validating repository")
            progress("02 Cloning repository")

        temp_dir = Path(tempfile.mkdtemp(prefix="github_explainer_"))
        try:
            destination = temp_dir / "repo"
            t = time.perf_counter()
            try:
                Repo.clone_from(clone_url, destination, depth=1, single_branch=True)
            except Exception as exc:
                raise RepositoryProcessingError("Unable to clone this repository. Make sure it is public, exists, and the URL is correct.") from exc
            timings["clone"] = time.perf_counter() - t

            if progress:
                progress("03 Scanning repository")
            t = time.perf_counter()
            records = self._inventory(destination)
            timings["scan"] = time.perf_counter() - t
            if progress:
                progress("04 Classifying files")

            meaningful = [r for r in records if r.category != "BINARY/ASSET" and not r.sensitive]
            if not meaningful:
                raise RepositoryProcessingError("This repository contains no meaningful readable project content to analyze.")

            t = time.perf_counter()
            technologies = self._detect_technologies(destination, records)
            timings["technology_detection"] = time.perf_counter() - t
            if progress:
                progress("05 Detecting technologies")
                progress("06 Preparing smart context")

            t = time.perf_counter()
            selected = self._rank_files(records)
            context = self._build_context(destination, selected)
            timings["context"] = time.perf_counter() - t
            timings["total"] = time.perf_counter() - start_total

            return {
                "repository_name": destination.name,
                "repository_owner": clone_url.rstrip(".git").split("/")[-2],
                "repository_url": url.strip(),
                "file_inventory": [asdict(r) for r in records],
                "file_counts": self._counts(records),
                "language_counts": self._language_counts(records),
                "technologies": technologies,
                "folder_tree": self._folder_tree(records),
                "important_files": [r.path for r in selected[:15]],
                "selected_files": [r.path for r in selected],
                "code_context": context,
                "repository_type": self._infer_type(records, technologies),
                "timings": timings,
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _inventory(self, root: Path) -> list[FileRecord]:
        records: list[FileRecord] = []
        for path in root.rglob("*"):
            try:
                if not path.is_file() or path.is_symlink():
                    continue
                rel = path.relative_to(root)
                if any(part in IGNORE_DIRS for part in rel.parts):
                    continue
                stat = path.stat()
                category, language, readable, sensitive = self._classify(path, rel, stat.st_size)
                records.append(FileRecord(str(rel).replace("\\", "/"), category, path.suffix.lower(), stat.st_size, language, sensitive, readable))
            except OSError:
                continue
        return sorted(records, key=lambda r: r.path.lower())

    def _classify(self, path: Path, rel: Path, size: int) -> tuple[str, str | None, bool, bool]:
        name = path.name.lower()
        sensitive = self._is_sensitive(path, rel)
        if sensitive:
            return "SENSITIVE", None, False, True
        if path.suffix.lower() in BINARY_EXTS:
            return "BINARY/ASSET", None, False, False
        if name in DEPENDENCY_NAMES:
            return "DEPENDENCIES", LANGUAGE_BY_EXT.get(path.suffix.lower()), True, False
        if name in BUILD_NAMES or name.startswith(".github") or "/.github/" in str(rel).replace("\\", "/"):
            return "BUILD/DEPLOYMENT", None, True, False
        if any(part.lower() in TEST_PARTS for part in rel.parts) or re.search(r"(^|[_-])(test|spec)([_-]|$)", name):
            return "TESTS", LANGUAGE_BY_EXT.get(path.suffix.lower()), True, False
        if path.name == "Dockerfile" or name.startswith("docker-compose"):
            return "BUILD/DEPLOYMENT", None, True, False
        if path.suffix.lower() == ".ipynb":
            return "NOTEBOOK", "Jupyter Notebook", True, False
        if path.suffix.lower() in DOC_EXTS or name.startswith("readme") or name.startswith("changelog"):
            return "DOCUMENTATION", None, True, False
        if path.suffix.lower() in DATA_EXTS:
            return "DATA/SCHEMA", None, True, False
        if path.suffix.lower() in CONFIG_EXTS or name in {".gitignore", ".gitattributes"}:
            return "CONFIGURATION", None, True, False
        if path.suffix.lower() in {".html", ".htm", ".css", ".scss", ".sass", ".vue", ".svelte"}:
            return "WEB", LANGUAGE_BY_EXT.get(path.suffix.lower()), True, False
        if path.suffix.lower() in SOURCE_EXTS:
            return "SOURCE", LANGUAGE_BY_EXT.get(path.suffix.lower()), True, False
        readable = self._is_readable_text(path, size)
        return ("UNKNOWN READABLE TEXT" if readable else "BINARY/ASSET", None, readable, False)

    @staticmethod
    def _is_sensitive(path: Path, rel: Path) -> bool:
        name = path.name.lower()
        if name in SENSITIVE_NAMES:
            return True
        if name.startswith(".env.") and name not in {".env.example", ".env.sample", ".env.template"}:
            return True
        joined = str(rel).lower().replace("\\", "/")
        return any(token in name for token in ("secret", "credential", "private_key", "access_token")) or ".ssh/" in joined

    @staticmethod
    def _is_readable_text(path: Path, size: int) -> bool:
        if size > 2_000_000:
            return False
        try:
            sample = path.read_bytes()[:4096]
            if b"\x00" in sample:
                return False
            sample.decode("utf-8")
            return True
        except (OSError, UnicodeDecodeError):
            return False

    def _rank_files(self, records: list[FileRecord]) -> list[FileRecord]:
        candidates = [r for r in records if r.readable and not r.sensitive and r.category not in {"BINARY/ASSET", "SENSITIVE"}]
        def score(r: FileRecord) -> tuple[int, int, int, str]:
            name = Path(r.path).name.lower()
            base = 0
            if name in {"readme.md", "readme", "readme.txt"}: base += 1000
            if r.category == "DEPENDENCIES": base += 850
            if name in {"main.py", "app.py", "index.js", "main.js", "server.py", "manage.py", "main.go", "main.rs"}: base += 750
            if r.category == "CONFIGURATION": base += 500
            if r.category == "BUILD/DEPLOYMENT": base += 450
            if r.category == "SOURCE": base += 400
            if r.category == "TESTS": base += 250
            if r.category == "NOTEBOOK": base += 220
            if r.category == "DOCUMENTATION": base += 200
            if r.category == "DATA/SCHEMA": base += 180
            depth_penalty = len(Path(r.path).parts)
            size_penalty = min(r.size_bytes // 5000, 20)
            return (-base, depth_penalty, size_penalty, r.path.lower())
        return sorted(candidates, key=score)[: self.max_files_for_llm]

    def _build_context(self, root: Path, selected: list[FileRecord]) -> str:
        chunks: list[str] = []
        remaining = self.max_total_context
        for record in selected:
            if remaining <= 0:
                break
            path = root / record.path
            text = self._read_for_context(path, record)
            if not text.strip():
                continue
            header = f"\n===== {record.category}: {record.path} =====\n"
            budget = min(MAX_FILE_SIZE_FOR_CONTEXT, remaining - len(header))
            if budget <= 0:
                break
            if len(text) > budget:
                text = self._smart_excerpt(text, budget)
                text += "\n[FILE CONTENT TRUNCATED FOR CONTEXT LIMIT]"
            chunk = header + text + "\n"
            chunks.append(chunk)
            remaining -= len(chunk)
        return "".join(chunks)

    def _read_for_context(self, path: Path, record: FileRecord) -> str:
        try:
            if record.category == "NOTEBOOK":
                data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
                cells = []
                for cell in data.get("cells", []):
                    ctype = cell.get("cell_type")
                    if ctype not in {"markdown", "code"}:
                        continue
                    source = "".join(cell.get("source", []))
                    if source.strip():
                        cells.append(f"[{ctype}]\n{source}")
                return "\n\n".join(cells)
            return path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return ""

    @staticmethod
    def _smart_excerpt(text: str, budget: int) -> str:
        if len(text) <= budget:
            return text
        head = int(budget * 0.55)
        tail = int(budget * 0.25)
        middle_budget = budget - head - tail
        lines = text.splitlines()
        important = [line for line in lines if re.match(r"\s*(class |def |function |export |import |from |const |let |var |public |private |fn |func |SELECT |CREATE )", line, re.I)]
        middle = "\n".join(important)[:middle_budget]
        return text[:head] + "\n[...important declarations excerpt...]\n" + middle + "\n[...file middle omitted...]\n" + text[-tail:]

    @staticmethod
    def _counts(records: list[FileRecord]) -> dict[str, int]:
        return {category: sum(1 for r in records if r.category == category) for category in sorted({r.category for r in records})}

    @staticmethod
    def _language_counts(records: list[FileRecord]) -> dict[str, int]:
        result: dict[str, int] = {}
        for r in records:
            if r.language:
                result[r.language] = result.get(r.language, 0) + 1
        return dict(sorted(result.items(), key=lambda x: (-x[1], x[0])))

    @staticmethod
    def _folder_tree(records: list[FileRecord], max_lines: int = 250) -> list[str]:
        return [r.path for r in records[:max_lines]]

    def _detect_technologies(self, root: Path, records: list[FileRecord]) -> list[str]:
        found: set[str] = set(self._language_counts(records).keys())
        names = {r.path.lower(): r for r in records}
        if "package.json" in names:
            try:
                data = json.loads((root / "package.json").read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                for dep in deps:
                    found.add(dep)
            except Exception:
                pass
        text_snippets = []
        for r in records:
            if r.sensitive or not r.readable or r.size_bytes > 30_000:
                continue
            if r.category in {"SOURCE", "DEPENDENCIES", "CONFIGURATION"}:
                try:
                    text_snippets.append((root / r.path).read_text(encoding="utf-8", errors="ignore")[:30_000])
                except OSError:
                    pass
        evidence = "\n".join(text_snippets)
        mapping = {
            "streamlit": "Streamlit", "fastapi": "FastAPI", "flask": "Flask", "django": "Django", "react": "React",
            "next": "Next.js", "express": "Express", "tensorflow": "TensorFlow", "torch": "PyTorch", "sklearn": "scikit-learn",
            "pandas": "Pandas", "numpy": "NumPy", "matplotlib": "Matplotlib", "seaborn": "Seaborn", "sqlalchemy": "SQLAlchemy",
            "firebase": "Firebase", "mongodb": "MongoDB", "postgres": "PostgreSQL", "mysql": "MySQL", "docker": "Docker",
        }
        low = evidence.lower()
        for token, label in mapping.items():
            if re.search(rf"\b{re.escape(token)}\b", low):
                found.add(label)
        return sorted(found)

    @staticmethod
    def _infer_type(records: list[FileRecord], technologies: list[str]) -> str:
        cats = {r.category for r in records}
        if "NOTEBOOK" in cats and "SOURCE" not in cats:
            return "Notebook/data science project"
        if "DOCUMENTATION" in cats and len(cats) == 1:
            return "Documentation project"
        if "DATA/SCHEMA" in cats and "SOURCE" not in cats:
            return "Data/schema project"
        if "SOURCE" in cats or "WEB" in cats:
            return "Software/code project"
        if "CONFIGURATION" in cats:
            return "Configuration/project metadata repository"
        return "General GitHub project"
