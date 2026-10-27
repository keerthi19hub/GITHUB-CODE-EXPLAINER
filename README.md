# 🔍 GitHub Code Explainer — GenAI-Powered Codebase Analysis Tool

> **Privacy-first GenAI developer tool that analyses, parses, and explains any GitHub or local repository using local LLMs — no code leaves your machine.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLMs-black)](https://ollama.ai)

---

## Problem Statement

Onboarding onto unfamiliar codebases is time-consuming and hindered by incomplete or absent documentation. Reading through hundreds of files manually is inefficient for developers and students alike.

## What it Does

1. **Accepts** a GitHub repository URL or local folder path.
2. **Crawls** the repository — extracting the full directory tree and source files.
3. **Chunks** code context and streams it to a local Ollama LLM.
4. **Generates** real-time architectural summaries, file-level explanations, complexity assessments, and dependency maps.
5. **Outputs** a clean, readable HTML/Streamlit dashboard — without transmitting code to external APIs.

## Key Features

- 🔒 **100% Private:** All LLM inference runs locally via Ollama (Llama 3, Mistral, CodeLlama).
- 🌲 **Directory Tree Visualisation:** Instant repo structure overview.
- 📄 **File-Level Explanations:** Module purpose, function summaries, algorithmic complexity.
- 🧪 **Test Suite:** Automated `pytest` unit tests for parser and chunker components.
- ☁️ **Streamlit Cloud Ready:** Deployable on Streamlit Community Cloud.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| UI | Streamlit |
| LLM | Ollama (Llama 3 / Mistral / CodeLlama) |
| Code Parsing | Python AST · LangChain text splitters |
| Testing | pytest |
| Language | Python 3.10+ |

## Quickstart

```bash
# 1. Prerequisites: Install Ollama
# https://ollama.ai → download & install
ollama pull llama3

# 2. Clone & setup
git clone https://github.com/keerthi19hub/GITHUB-CODE-EXPLAINER.git
cd GITHUB-CODE-EXPLAINER

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate    # Linux/Mac

pip install -r requirements.txt

# 3. Run
streamlit run app.py

# 4. Run tests
pytest tests/
```

## Architecture

```
GITHUB-CODE-EXPLAINER/
├── app.py              # Streamlit application entry point
├── backend/
│   ├── crawler.py      # Repository directory walker & file reader
│   ├── chunker.py      # LangChain-based context chunking
│   └── explainer.py    # Ollama LLM interaction & prompt engineering
├── components/
│   ├── tree_view.py    # Directory tree UI component
│   └── code_card.py    # File explanation card widget
├── tests/
│   ├── test_crawler.py
│   └── test_chunker.py
├── requirements.txt
└── pytest.ini
```

## Author

**Keerthi N** — Repository file crawler, prompt engineering pipeline, Streamlit UI, and unit testing suite.

*Alliance University, BCA — 2026*

---

Released under the [MIT License](https://opensource.org/licenses/MIT).
