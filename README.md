# Mini Project: Local GitHub Repository Code Explainer

An open-source, GenAI-powered web application that takes any public GitHub repository URL and automatically produces a clear, beginner-friendly explanation of the codebase.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Problem Statement](#problem-statement)
3. [Objective](#objective)
4. [How the Project Works](#how-the-project-works)
5. [System Architecture](#system-architecture)
6. [Technologies Used](#technologies-used)
7. [How Repository Processing Works](#how-repository-processing-works)
8. [How the Language Model (LLM) Works](#how-the-language-model-llm-works)
9. [Frontend Design](#frontend-design)
10. [Backend & Service Layer](#backend--service-layer)
11. [Example Input and Output](#example-input-and-output)
12. [Local Development Guide](#local-development-guide)
13. [Public Streamlit Cloud Deployment Guide](#public-streamlit-cloud-deployment-guide)
14. [Testing & Verification](#testing--verification)
15. [Limitations & Expected Latency](#limitations--expected-latency)
16. [Future Improvements](#future-improvements)
17. [Viva & Teacher Demonstration Notes](#viva--teacher-demonstration-notes)

---

## Project Overview

When students, teachers, or junior developers explore open-source projects on GitHub, reading thousands of lines of unfamiliar source code and directory structures can be overwhelming.

The **GitHub Repository Code Explainer** automates this by:
1. Cloning a public repository safely into an isolated workspace.
2. Scanning and cataloging the repository's files while protecting sensitive keys and secrets.
3. Extracting key source files, configs, and documentation within a bounded context window.
4. Passing this grounded context to an in-process, open-source language model (**HuggingFaceTB/SmolLM2-135M-Instruct**).
5. Generating a clean, structured explanation that anyone can understand without confusing jargon.

---

## Problem Statement

Understanding unfamiliar codebases is slow and intimidating. Traditional cloud LLM tools require paid API keys (OpenAI, Gemini, Anthropic), subscription billing, and risk credential leaks. Local LLM servers (like Ollama on a personal laptop) cannot be accessed by external evaluators once the student's laptop is closed or turned off.

There is a need for a **self-contained, 100% free, open-source GenAI application** that can be publicly demonstrated online without requiring external API keys, external servers, or a running personal computer.

---

## Objective

Build a working GenAI web application that:
- Accepts a public GitHub repository link (e.g., `https://github.com/psf/requests`).
- Processes repository files using GitPython safely (read-only, no code execution).
- Uses a local/open-source language model running directly inside the application environment.
- Follows a modular architecture: **Frontend (Streamlit)** → **Backend Service Layer** → **Repository Processor** → **In-Process LLM**.
- Deploys publicly on Streamlit Community Cloud so teachers can evaluate it independently at any time.

---

## How the Project Works

The application follows an 8-stage execution pipeline:

```
1. Validating GitHub URL
        ↓
2. Cloning repository (shallow git clone, depth=1)
        ↓
3. Scanning repository (directory traversal, excluding cache/build dirs)
        ↓
4. Classifying files (Source, Dependencies, Docs, Sensitive, Notebooks, Binaries)
        ↓
5. Detecting technologies (from requirements.txt, package.json, and source imports)
        ↓
6. Building AI context (ranking important files, intelligent excerpting)
        ↓
7. Generating AI explanation (in-process SmolLM2-135M-Instruct model)
        ↓
8. Finalizing report (rendering metrics, structure, and explanation in UI)
```

---

## System Architecture

```
+-------------------------------------------------------------+
|                        USER BROWSER                         |
|   (Enters public GitHub URL & clicks "Explain Repository")  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                  STREAMLIT FRONTEND (app.py)                |
|  - Renders input UI, progress updates, and explanation      |
|  - Displays metrics, file inventory, and timings            |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|             BACKEND SERVICE (backend/service.py)            |
|  - Coordinates repository cloning, file ranking, and LLM    |
|  - Measures performance stages using time.perf_counter()    |
+-------------------------------------------------------------+
               |                               |
               v                               v
+-----------------------------+ +-----------------------------+
|     REPOSITORY PROCESSOR    | |         LLM SERVICE         |
|    (repo_processor.py)      | |      (llm_service.py)       |
| - Git shallow clone         | | - SmolLM2-135M-Instruct     |
| - File classification       | | - Cached via @st.cache_     |
| - Sensitive file shielding  | |   resource                  |
| - Notebook JSON parser      | | - Repetition penalties      |
| - Technology detector       | | - Grounded system prompt    |
+-----------------------------+ +-----------------------------+
```

> **Architecture Note for Viva:**  
> The project maintains a clean separation of concerns. The FastAPI server in `backend/main.py` demonstrates API-based backend architecture for local development, while Streamlit (`app.py`) directly invokes `backend/service.py`. This ensures Streamlit Cloud runs in a single, robust process without relying on fragile multi-process networking or localhost ports.

---

## Technologies Used

| Category | Technology | Purpose |
|---|---|---|
| **Frontend** | Streamlit | Clean, interactive web UI with real-time status widgets |
| **Backend Service** | Python 3.12 / FastAPI | Service coordinator & optional REST API endpoints |
| **Git Automation** | GitPython | Safe, shallow cloning (`depth=1`) of public repositories |
| **GenAI / LLM** | Hugging Face Transformers | In-process neural network inference |
| **Deep Learning Engine** | PyTorch | CPU/GPU tensor computation for model weights |
| **Language Model** | `HuggingFaceTB/SmolLM2-135M-Instruct` | Lightweight (~135M parameters, ~270MB) open-source LLM |
| **Data Validation** | Pydantic | Validates URLs and API request structures |
| **Testing** | pytest | Automated test suite validating all 8 core features |

---

## How Repository Processing Works

1. **URL Validation & Normalization:** Checks that the URL belongs to `github.com` and has both an owner and repository name.
2. **Shallow Clone (`depth=1`):** Downloads only the latest commit of the repository to minimize bandwidth, disk space, and clone time.
3. **No Code Execution:** Repository code is **NEVER executed**. No Python scripts, shell scripts, or notebooks are ever run. Files are strictly opened as read-only text.
4. **File Classification:** Each file is categorized into one of:
   - `SOURCE` (.py, .js, .ts, .java, .cpp, .go, etc.)
   - `DEPENDENCIES` (requirements.txt, package.json, Cargo.toml, go.mod, pom.xml)
   - `CONFIGURATION` (.yaml, .json, .toml, .ini)
   - `DOCUMENTATION` (README.md, docs, .txt)
   - `NOTEBOOK` (.ipynb)
   - `TESTS` (test folders or test filenames)
   - `DATA/SCHEMA` (.csv, .jsonl, .sql)
   - `BINARY/ASSET` (.png, .pdf, .zip, .exe, .pyc)
   - `SENSITIVE` (.env, credentials, secrets, private keys)
5. **Sensitive File Protection:** Any file matching sensitive keywords (`.env`, `credentials`, `secret`, `id_rsa`) is flagged as `SENSITIVE`. Its contents are completely excluded from AI context and never displayed in the UI.
6. **Safe Notebook Parsing:** Jupyter notebooks (`.ipynb`) are parsed as JSON to extract markdown and code cell texts without running the notebook kernel.
7. **Evidence-Based Technology Detection:** Technologies are reported **strictly** based on verified evidence:
   - Dependencies listed in `requirements.txt` or `package.json`.
   - Programming languages counted from source extensions.
   - Verified framework imports in code.
   - If not established, the system explicitly reports: *"Not clearly established from the available repository files."*
8. **Smart Context Excerpting:** Large files are excerpted (head, key function/class definitions, tail) and labeled with `[FILE CONTENT TRUNCATED FOR CONTEXT LIMIT]` to keep total prompt length within memory bounds.

---

## How the Language Model (LLM) Works

### Local Open-Source LLM Architecture
- **Model Selected:** `HuggingFaceTB/SmolLM2-135M-Instruct`
- **Why this model?**
  1. **Very Compact:** ~135 Million parameters (~270MB download).
  2. **Fast on CPU:** Runs smoothly inside Streamlit Cloud's free CPU container without GPU requirements.
  3. **Low Memory Usage:** Consumes less than 500MB RAM, staying well below Streamlit Cloud's 1GB/3GB limits.
  4. **Self-Contained:** Runs directly within Python using Hugging Face Transformers. No Ollama daemon or paid API keys required!

### Zero-Reload Caching
The model and tokenizer are cached using Streamlit's `@st.cache_resource` decorator:
```python
@st.cache_resource(show_spinner=False)
def load_model_and_tokenizer():
    ...
```
This guarantees the model weights are loaded into memory once and reused across all subsequent user requests.

### Anti-Repetition & Grounded Prompting
To prevent the repetitive token loops common in small models:
- `repetition_penalty=1.15` and `no_repeat_ngram_size=3` are applied during generation.
- The system prompt strictly prohibits hallucinations and instructs the model to structure answers into 12 clear sections:
  1. Project Overview
  2. What the Project Does
  3. Main Features
  4. Repository Structure
  5. Important Files
  6. Technologies Used
  7. How the Application Works
  8. Main Code Components
  9. Data Flow
  10. Dependencies / Configuration
  11. How to Run It (if evident from repository files)
  12. Limitations / Missing Information

---

## Frontend Design

The frontend is built using **Streamlit** and features:
- **Header & Description:** Clear title and usage instructions.
- **Sidebar:** Live architecture diagram and model metadata.
- **Repository Input:** Text input accepting any public GitHub URL with placeholder `https://github.com/psf/requests`.
- **Status Widget:** Real-time updates as each stage of analysis completes.
- **7 Output Panels:**
  1. **Repository Overview:** Metric cards for file counts, owner, name, and total processing duration.
  2. **Technologies Used:** Badges of detected tools and breakdown of programming languages.
  3. **Important Files:** Ranked list of files included in the AI context.
  4. **Repository Structure:** Expandable complete file inventory with size and protection markers.
  5. **AI-Generated Project Explanation:** Markdown explanation generated by the local model.
  6. **Performance Information:** Execution duration for each stage using `time.perf_counter()`.
  7. **Model Information:** Full description of the model, architecture, and runtime.

---

## Backend & Service Layer

The project includes a two-tiered backend design:
1. **`backend/service.py`:** Shared Python service function `analyze_repository(url, progress)` that performs the analysis workflow.
2. **`backend/main.py`:** A FastAPI application exposing:
   - `GET /`: API status information.
   - `GET /api/health`: Health-check endpoint returning `{"status": "ok"}`.
   - `POST /api/explain`: Endpoint accepting a JSON body `{"repository_url": "..."}` and returning full analysis data.

---

## Example Input and Output

### Input
```text
https://github.com/octocat/Hello-World
```

### Output
- **Repository Overview:** Total Files: 1 | Documentation: 1 | Type: Documentation Project
- **Technologies Used:** Not clearly established from the available repository files.
- **Important Files:** `README`
- **AI Explanation Preview:**
  > **1. Project Overview:** This repository is the canonical Hello-World demonstration project by GitHub.  
  > **2. What the Project Does:** It provides a basic repository to help beginners learn Git and GitHub workflows.  
  > **3. Repository Structure:** Contains a single README document.  
  > ...

---

## Local Development Guide

### 1. Clone the repository
```bash
git clone https://github.com/keerthi19hub/GITHUB-CODE-EXPLAINER.git
cd GITHUB-CODE-EXPLAINER
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install requirements
```bash
pip install -r requirements.txt
```

### 4. Run the Streamlit web application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 5. Optional: Run the FastAPI backend server
```bash
uvicorn backend.main:app --reload --port 8000
```
API documentation will be available at `http://localhost:8000/docs`.

---

## Public Streamlit Cloud Deployment Guide

The application is fully prepared for one-click deployment on **Streamlit Community Cloud**:

1. Ensure the code is committed and pushed to the `main` branch of:
   `https://github.com/keerthi19hub/GITHUB-CODE-EXPLAINER`
2. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
3. Click **New app**.
4. Configure the deployment settings:
   - **Repository:** `keerthi19hub/GITHUB-CODE-EXPLAINER`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **Deploy!**
6. **No secrets or environment variables are required!**
7. Once deployed, copy your public Streamlit URL (e.g., `https://github-code-explainer.streamlit.app`).

---

## Testing & Verification

The project includes an automated test suite verifying all 8 core features.

To run the tests:
```bash
pytest -v tests/test_project.py
```

### Test Suite Summary:
- `test_required_root_files_exist`: Verifies core files are present.
- `test_github_url_validation`: Verifies URL format validation and normalization.
- `test_file_classification`: Verifies categorization of code, docs, data, and config.
- `test_sensitive_file_protection`: Verifies `.env` and secrets are never leaked to LLM context.
- `test_notebook_parsing_without_execution`: Verifies Jupyter notebooks are parsed safely as text.
- `test_context_size_limits`: Verifies prompt length constraints are respected.
- `test_technology_detection`: Verifies frameworks are detected strictly from evidence.
- `test_fastapi_health_endpoint`: Verifies REST API routes function properly.
- `test_streamlit_entrypoint_is_self_contained`: Verifies Streamlit app does not depend on external servers.

---

## Limitations & Expected Latency

1. **Initial Model Download:** On the very first run in a fresh container, Hugging Face downloads the ~270MB model weights (takes ~15–30 seconds). Subsequent requests use the cached model in RAM immediately.
2. **CPU Inference Latency:** On free cloud CPU tiers, generating 300–400 tokens takes approximately 5–15 seconds depending on server load.
3. **Repository Scope:** Repositories are cloned with shallow depth (`depth=1`). Very large repositories (millions of lines) are prioritized and truncated to prevent memory exhaustion.
4. **Public Repositories Only:** Only public GitHub repositories are accessible without authentication. Private repositories are safely rejected.

---

## Future Improvements

- Add support for GitLab and Bitbucket URLs.
- Include architectural diagram generation (Mermaid.js code) directly from code analysis.
- Add multi-language translation for project explanations.
- Support optional user-provided API keys (OpenAI / Claude / Gemini) for users wanting ultra-large model explanations while keeping local SmolLM2 as the free default.

---

## Viva & Teacher Demonstration Notes

### How to Explain This Project in Viva:
1. **"What is the objective of this project?"**
   > *"Mam, our project is a Generative AI application that takes any public GitHub repository link and generates a clear, simple-language explanation of what the codebase does, its technologies, and its structure."*

2. **"Where is the LLM running?"**
   > *"Mam, the application uses an open-source model called SmolLM2-135M-Instruct from Hugging Face. It runs locally inside our Python application process using PyTorch and Transformers. It does not use any paid cloud APIs like OpenAI or Gemini."*

3. **"Why didn't you use Ollama for the final deployment?"**
   > *"Mam, Ollama is great for local laptop development, but if we deploy to the cloud, an Ollama server running on my personal laptop stops working whenever my laptop is closed or turned off. By loading a lightweight 135M open-source model directly inside the Streamlit runtime, the application is 100% self-contained and anyone can open the public website from any laptop at any time."*

4. **"How do you handle security?"**
   > *"Mam, we have three safety guarantees: first, we never execute any code from the repository. Second, we parse Jupyter notebooks as raw JSON without running kernels. Third, any sensitive files like `.env`, secret keys, or credentials are automatically filtered out so their contents are never sent to the model or displayed in the UI."*

5. **"What is the role of FastAPI and Streamlit?"**
   > *"Streamlit provides the user-facing web interface. In the backend, we created a reusable service layer in `backend/service.py` that both Streamlit and our FastAPI REST endpoints can use. Streamlit calls this service directly so it doesn't need a separate server process in cloud deployment."*
