"""
repo_processor.py
=================
Core module for cloning and inspecting public GitHub repositories.
Designed for simple, safe code analysis:
1. Clones public GitHub repositories using a shallow clone (depth=1).
2. Scans and classifies repository files without executing any repository code.
3. Extracts notebook cells (.ipynb) via JSON parsing (no execution).
4. Strictly protects sensitive files (.env, secrets, credentials, tokens).
5. Excludes binary files from model context.
6. Detects technologies based strictly on repository evidence.
7. Builds a concise, representative context within strict token budgets.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from git import Repo


class RepositoryProcessingError(Exception):
    """User-friendly exception for repository processing errors."""
    pass


@dataclass
class FileRecord:
    """Represents a single scanned file in the repository."""
    path: str
    category: str
    extension: str
    size_bytes: int
    language: str | None = None
    sensitive: bool = False
    readable: bool = False


# Mapping of common file extensions to programming languages
LANGUAGE_BY_EXT: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".swift": "Swift",
    ".dart": "Dart",
    ".r": "R",
    ".R": "R",
    ".sql": "SQL",
    ".sh": "Shell Script",
    ".bash": "Shell Script",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".vue": "Vue",
    ".svelte": "Svelte",
}

SOURCE_EXTS = set(LANGUAGE_BY_EXT.keys())
CONFIG_EXTS = {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf", ".xml", ".properties"}
DATA_EXTS = {".csv", ".tsv", ".jsonl", ".ndjson", ".parquet", ".db", ".sqlite", ".sqlite3"}
DOC_EXTS = {".md", ".markdown", ".rst", ".txt", ".adoc"}

DEPENDENCY_NAMES = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    "pom.xml", "build.gradle", "build.gradle.kts", "gradle.properties",
    "cargo.toml", "cargo.lock", "go.mod", "go.sum",
    "composer.json", "gemfile", "gemfile.lock", "pubspec.yaml",
}

BUILD_NAMES = {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "makefile", "justfile", "procfile"}
TEST_PARTS = {"test", "tests", "spec", "specs", "__tests__"}

# Sensitive filenames that should never have their contents exposed or sent to an LLM
SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development", ".env.staging",
    "credentials", "credentials.json", "secrets.json", "secret.json",
    "id_rsa", "id_ed25519", "private.key", "private.pem", "service_account.json",
}

# Directories to ignore during scanning to save time and memory
IGNORE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "node_modules", "dist", "build", "target", ".idea",
    ".vscode", ".next", ".nuxt", "coverage", ".tox",
}

# Common binary file extensions
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".woff", ".woff2", ".ttf", ".otf",
    ".mp3", ".wav", ".mp4", ".mov", ".avi",
    ".class", ".jar", ".pyc", ".pkl", ".npy", ".npz",
}

# Context budget limits for fast, CPU-friendly inference
MAX_FILE_SIZE_FOR_CONTEXT = 4_000   # Max characters extracted from a single file
MAX_TOTAL_CONTEXT = 16_000          # Max total characters sent in model prompt (~3500 tokens)
MAX_FILES_FOR_LLM = 20              # Maximum number of files included in the context


class RepositoryProcessor:
    """Clones and inspects public GitHub repositories safely without code execution."""

    def __init__(self, max_total_context: int = MAX_TOTAL_CONTEXT, max_files_for_llm: int = MAX_FILES_FOR_LLM):
        self.max_total_context = max_total_context
        self.max_files_for_llm = max_files_for_llm

    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validate and normalize a GitHub repository URL.
        Accepts:
          - https://github.com/owner/repo
          - http://github.com/owner/repo
          - github.com/owner/repo
        """
        raw = url.strip()
        if not raw:
            raise RepositoryProcessingError("Please enter a GitHub repository URL.")

        if not raw.startswith("http://") and not raw.startswith("https://"):
            raw = f"https://{raw}"

        parsed = urlparse(raw)
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise RepositoryProcessingError("Please enter a valid GitHub URL (domain must be github.com).")

        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) < 2 or parts[0].startswith(".") or parts[1].startswith("."):
            raise RepositoryProcessingError("The GitHub URL must include both owner and repository name (e.g., https://github.com/username/repository).")

        owner = parts[0]
        repo_name = parts[1].removesuffix(".git")
        return f"https://github.com/{owner}/{repo_name}.git"

    def process(self, url: str, progress: Callable[[str], None] | None = None) -> dict[str, Any]:
        """
        Main pipeline to clone, scan, classify, and extract repository context.
        """
        timings: dict[str, float] = {}
        start_total = time.perf_counter()

        # Step 1: Validate URL
        if progress:
            progress("1. Validating GitHub URL")
        t = time.perf_counter()
        clone_url = self.validate_url(url)
        timings["validation"] = time.perf_counter() - t

        # Step 2: Clone repository (shallow clone)
        if progress:
            progress("2. Cloning repository")
        temp_dir = Path(tempfile.mkdtemp(prefix="github_explainer_"))
        try:
            destination = temp_dir / "repo"
            t = time.perf_counter()
            try:
                Repo.clone_from(clone_url, destination, depth=1, single_branch=True)
            except Exception as exc:
                err_text = str(exc).lower()
                if any(k in err_text for k in ["not found", "authentication", "terminal prompts disabled"]):
                    raise RepositoryProcessingError(
                        "Could not clone repository. Please verify that the repository exists, is public (not private), and the URL is correct."
                    ) from exc
                raise RepositoryProcessingError(f"Failed to clone repository: {exc}") from exc
            timings["clone"] = time.perf_counter() - t

            # Step 3: Scan repository files
            if progress:
                progress("3. Scanning repository")
            t = time.perf_counter()
            records = self._inventory(destination)
            timings["scan"] = time.perf_counter() - t

            # Step 4: Classify files
            if progress:
                progress("4. Classifying files")
            meaningful = [r for r in records if r.category != "BINARY/ASSET" and not r.sensitive]
            if not meaningful:
                raise RepositoryProcessingError("This repository does not contain any readable source code or project documentation files to analyze.")

            # Step 5: Detect technologies from evidence
            if progress:
                progress("5. Detecting technologies")
            t = time.perf_counter()
            technologies = self._detect_technologies(destination, records)
            timings["technology_detection"] = time.perf_counter() - t

            # Step 6: Build AI context
            if progress:
                progress("6. Building AI context")
            t = time.perf_counter()
            selected = self._rank_files(records)
            context = self._build_context(destination, selected)
            timings["context"] = time.perf_counter() - t
            timings["total_processing"] = time.perf_counter() - start_total

            repo_owner = clone_url.rstrip(".git").split("/")[-2]
            repo_name = clone_url.rstrip(".git").split("/")[-1]

            return {
                "repository_name": repo_name,
                "repository_owner": repo_owner,
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
            # Always delete the temporary cloned directory to free up disk space
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _inventory(self, root: Path) -> list[FileRecord]:
        """Scan directory tree and return FileRecord entries."""
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
                records.append(
                    FileRecord(
                        path=str(rel).replace("\\", "/"),
                        category=category,
                        extension=path.suffix.lower(),
                        size_bytes=stat.st_size,
                        language=language,
                        sensitive=sensitive,
                        readable=readable,
                    )
                )
            except OSError:
                continue
        return sorted(records, key=lambda r: r.path.lower())

    def _classify(self, path: Path, rel: Path, size: int) -> tuple[str, str | None, bool, bool]:
        """Classify a file into a category, detect language, and flag sensitive/binary status."""
        name = path.name.lower()

        # Check for sensitive files first
        if self._is_sensitive(path, rel):
            return "SENSITIVE", None, False, True

        # Check for binary files
        if path.suffix.lower() in BINARY_EXTS:
            return "BINARY/ASSET", None, False, False

        # Dependency & package management files
        if name in DEPENDENCY_NAMES:
            return "DEPENDENCIES", LANGUAGE_BY_EXT.get(path.suffix.lower()), True, False

        # Build and CI/CD files
        if name in BUILD_NAMES or name.startswith(".github") or "/.github/" in str(rel).replace("\\", "/"):
            return "BUILD/DEPLOYMENT", None, True, False

        # Test files
        if any(part.lower() in TEST_PARTS for part in rel.parts) or re.search(r"(^|[_-])(test|spec)([_-]|$)", name):
            return "TESTS", LANGUAGE_BY_EXT.get(path.suffix.lower()), True, False

        # Jupyter notebooks
        if path.suffix.lower() == ".ipynb":
            return "NOTEBOOK", "Jupyter Notebook", True, False

        # Documentation
        if path.suffix.lower() in DOC_EXTS or name.startswith("readme") or name.startswith("changelog") or name.startswith("license"):
            return "DOCUMENTATION", None, True, False

        # Data & Database schemas
        if path.suffix.lower() in DATA_EXTS:
            return "DATA/SCHEMA", None, True, False

        # Configuration files
        if path.suffix.lower() in CONFIG_EXTS or name in {".gitignore", ".gitattributes", ".editorconfig"}:
            return "CONFIGURATION", None, True, False

        # Web files (HTML/CSS)
        if path.suffix.lower() in {".html", ".htm", ".css", ".scss", ".sass", ".vue", ".svelte"}:
            return "WEB", LANGUAGE_BY_EXT.get(path.suffix.lower()), True, False

        # Source code files
        if path.suffix.lower() in SOURCE_EXTS:
            return "SOURCE", LANGUAGE_BY_EXT.get(path.suffix.lower()), True, False

        # Fallback text check
        readable = self._is_readable_text(path, size)
        return ("UNKNOWN READABLE TEXT" if readable else "BINARY/ASSET", None, readable, False)

    @staticmethod
    def _is_sensitive(path: Path, rel: Path) -> bool:
        """Identify sensitive credential and secret files."""
        name = path.name.lower()
        if name in SENSITIVE_NAMES:
            return True
        if name.startswith(".env.") and name not in {".env.example", ".env.sample", ".env.template"}:
            return True
        joined = str(rel).lower().replace("\\", "/")
        sensitive_keywords = ("secret", "credential", "private_key", "access_token", "id_rsa", "id_ed25519")
        return any(token in name for token in sensitive_keywords) or ".ssh/" in joined

    @staticmethod
    def _is_readable_text(path: Path, size: int) -> bool:
        """Check if a file contains readable text without binary null bytes."""
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
        """Rank files by importance for LLM context inclusion."""
        candidates = [
            r for r in records
            if r.readable and not r.sensitive and r.category not in {"BINARY/ASSET", "SENSITIVE"}
        ]

        def score(r: FileRecord) -> tuple[int, int, int, str]:
            name = Path(r.path).name.lower()
            base = 0
            if name in {"readme.md", "readme", "readme.txt"}:
                base += 1000
            elif r.category == "DEPENDENCIES":
                base += 850
            elif name in {"main.py", "app.py", "index.js", "main.js", "server.py", "manage.py", "main.go", "main.rs"}:
                base += 750
            elif r.category == "CONFIGURATION":
                base += 500
            elif r.category == "BUILD/DEPLOYMENT":
                base += 450
            elif r.category == "SOURCE":
                base += 400
            elif r.category == "TESTS":
                base += 250
            elif r.category == "NOTEBOOK":
                base += 220
            elif r.category == "DOCUMENTATION":
                base += 200
            elif r.category == "DATA/SCHEMA":
                base += 180

            depth_penalty = len(Path(r.path).parts)
            size_penalty = min(r.size_bytes // 5000, 20)
            return (-base, depth_penalty, size_penalty, r.path.lower())

        return sorted(candidates, key=score)[: self.max_files_for_llm]

    def _build_context(self, root: Path, selected: list[FileRecord]) -> str:
        """Build the combined context text, respecting size limits with smart excerpting."""
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
        """Safely read text from a file or parse notebook cells."""
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
        """Intelligently excerpt large files by keeping head, declarations, and tail."""
        if len(text) <= budget:
            return text
        head = int(budget * 0.55)
        tail = int(budget * 0.25)
        middle_budget = max(0, budget - head - tail)

        lines = text.splitlines()
        important_decl = [
            line for line in lines
            if re.match(r"\s*(class |def |function |export |import |from |const |let |var |public |private |fn |func |SELECT |CREATE )", line, re.I)
        ]
        middle = "\n".join(important_decl)[:middle_budget]
        return text[:head] + "\n[...important declarations excerpt...]\n" + middle + "\n[...file middle omitted...]\n" + text[-tail:]

    @staticmethod
    def _counts(records: list[FileRecord]) -> dict[str, int]:
        """Count files per category."""
        return {
            category: sum(1 for r in records if r.category == category)
            for category in sorted({r.category for r in records})
        }

    @staticmethod
    def _language_counts(records: list[FileRecord]) -> dict[str, int]:
        """Count files per programming language."""
        result: dict[str, int] = {}
        for r in records:
            if r.language:
                result[r.language] = result.get(r.language, 0) + 1
        return dict(sorted(result.items(), key=lambda x: (-x[1], x[0])))

    @staticmethod
    def _folder_tree(records: list[FileRecord], max_lines: int = 150) -> list[str]:
        """Produce a clean list of repository file paths."""
        return [r.path for r in records[:max_lines]]

    def _detect_technologies(self, root: Path, records: list[FileRecord]) -> list[str]:
        """Detect technologies and frameworks strictly from actual repository evidence."""
        found: set[str] = set(self._language_counts(records).keys())
        names = {r.path.lower(): r for r in records}

        # Check package.json for npm packages
        if "package.json" in names:
            try:
                pkg_data = json.loads((root / "package.json").read_text(encoding="utf-8"))
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                for dep in deps:
                    found.add(dep)
            except Exception:
                pass

        # Check requirements.txt for Python packages
        for r in records:
            if r.path.lower().endswith("requirements.txt") and not r.sensitive:
                try:
                    lines = (root / r.path).read_text(encoding="utf-8", errors="ignore").splitlines()
                    for line in lines:
                        clean_line = line.strip().split("==")[0].split(">=")[0].split("<=")[0].strip()
                        if clean_line and not clean_line.startswith("#") and not clean_line.startswith("-"):
                            found.add(clean_line)
                except Exception:
                    pass

        # Scan text snippets from source files for well-known frameworks
        text_snippets = []
        for r in records:
            if r.sensitive or not r.readable or r.size_bytes > 30_000:
                continue
            if r.category in {"SOURCE", "DEPENDENCIES", "CONFIGURATION"}:
                try:
                    text_snippets.append((root / r.path).read_text(encoding="utf-8", errors="ignore")[:20_000])
                except OSError:
                    pass

        evidence = "\n".join(text_snippets).lower()
        framework_mapping = {
            "streamlit": "Streamlit",
            "fastapi": "FastAPI",
            "flask": "Flask",
            "django": "Django",
            "react": "React",
            "next": "Next.js",
            "express": "Express",
            "tensorflow": "TensorFlow",
            "torch": "PyTorch",
            "sklearn": "scikit-learn",
            "pandas": "Pandas",
            "numpy": "NumPy",
            "matplotlib": "Matplotlib",
            "seaborn": "Seaborn",
            "sqlalchemy": "SQLAlchemy",
            "docker": "Docker",
        }

        for token, label in framework_mapping.items():
            if re.search(rf"\b{re.escape(token)}\b", evidence):
                found.add(label)

        return sorted(found)

    @staticmethod
    def _infer_type(records: list[FileRecord], technologies: list[str]) -> str:
        """Infer high-level project type from file categories and detected technologies."""
        cats = {r.category for r in records}
        if "NOTEBOOK" in cats and "SOURCE" not in cats:
            return "Notebook / Data Science Project"
        if "DOCUMENTATION" in cats and len(cats) == 1:
            return "Documentation Project"
        if "DATA/SCHEMA" in cats and "SOURCE" not in cats:
            return "Data / Schema Repository"
        if "SOURCE" in cats or "WEB" in cats:
            if "Streamlit" in technologies:
                return "Streamlit Web Application"
            if "FastAPI" in technologies or "Flask" in technologies or "Django" in technologies:
                return "Python Web Service / API"
            if "React" in technologies or "Vue" in technologies:
                return "Frontend Web Application"
            return "Software / Source Code Project"
        if "CONFIGURATION" in cats:
            return "Configuration / Project Metadata Repository"
        return "General GitHub Repository"
