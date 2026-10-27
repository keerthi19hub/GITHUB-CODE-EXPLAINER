# 🔍 GitHub Code Explainer — AST Semantic Code Intelligence & Repository Parser

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0F172A,0284C7,38BDF8&height=220&section=header&text=GitHub%20Code%20Explainer&fontSize=42&fontColor=ffffff&fontAlignY=38&desc=AST%20Semantic%20Code%20Intelligence%20%26%20Repository%20Parser&descSize=18&descAlignY=60&descAlign=50" width="100%" alt="GitHub Code Explainer Banner" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Language-Python%203.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Interface-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/Inference-Local%20Ollama-000000?style=for-the-badge" alt="Ollama" />
  <img src="https://img.shields.io/badge/Testing-Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/Deployment-Streamlit%20Cloud%20Ready-FF4B4B?style=for-the-badge" alt="Streamlit Cloud" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

---

## 📌 Table of Contents

- [📖 Executive Summary](#-executive-summary)
- [🎯 Real-World Problem & Solution](#-real-world-problem--solution)
- [✨ Key Features & Capabilities](#-key-features--capabilities)
- [🏗️ System Architecture & Workflow](#️-system-architecture--workflow)
- [🛠️ Tech Stack Matrix](#️-tech-stack-matrix)
- [⚙️ Reproducible Quickstart & Setup](#️-reproducible-quickstart--setup)
- [📁 Project Structure](#-project-structure)
- [🧪 Testing & Validation](#-testing--validation)
- [👩‍💻 Author & Contributions](#-author--contributions)

---

## 📖 Executive Summary

**GitHub Code Explainer** is a privacy-first GenAI developer tool and static analysis workbench that ingests, parses, chunks, and explains arbitrary source code repositories. Powered by **Python, Streamlit**, and an air-gapped **Local Ollama LLM** inference pipeline (supporting CodeLlama, Llama 3, and Mistral), the platform enables software engineers to onboard onto complex unfamiliar codebases in minutes—extracting syntax trees, module dependency graphs, and algorithmic complexity assessments without ever leaking confidential code to third-party APIs.

---

## 🎯 Real-World Problem & Solution

- **The Problem:** Software engineering teams spend up to 60% of onboarding time reading undocumented codebases. Cloud-based GenAI tools (ChatGPT, Claude) pose severe IP theft and confidentiality risks for private corporate repositories.
- **The Solution:** A local-first code intelligence platform. It crawls repositories locally, runs Abstract Syntax Tree (AST) token parsing and chunking, and queries local LLMs via Ollama to generate instantaneous architectural summaries, function explanations, and complexity audits.

---

## ✨ Key Features & Capabilities

- **🔒 100% Air-Gapped Privacy:** Zero remote API calls; all token parsing and LLM inference executes completely on the local machine.
- **🌲 Dynamic Repository Tree Visualization:** Automated file walker generating clean hierarchical directory trees and language distributions.
- **📑 AST-Aware Code Chunking:** Parses source files using syntax boundaries rather than arbitrary character slicing, preserving semantic coherence.
- **⚡ Granular File & Function Summaries:** Explains module responsibilities, algorithmic complexities ($O(n)$ notation), and integration points.
- **🧪 Automated Pytest Test Suite:** Comprehensive unit tests covering repository crawlers, token filters, and chunking integrity.
- **☁️ Streamlit Community Cloud Ready:** Pre-configured with `runtime.txt`, `DEPLOY_ON_STREAMLIT.md`, and modular backend abstractions.

---

## 🏗️ System Architecture & Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     GitHub Code Explainer Architecture                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Input Layer: Local Folder Path OR Cloned Git Repository URL                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Repository Processing Layer (`repo_processor.py` & `backend/`)              │
│ - Directory Tree Walker & .gitignore Filtering                              │
│ - Multi-Language File Ingestion (.py, .js, .ts, .java, .cpp)                │
│ - Semantic Syntax & AST Context Chunking                                    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LLM Intelligence Layer (`llm_service.py`)                                   │
│ - Ollama Local Model Bridge (Llama 3 / CodeLlama / Mistral)                 │
│ - Structured Prompt Engineering: Architecture, Functionality, Complexity    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Presentation Layer (`app.py` - Streamlit Reactive Dashboard)                │
│ ┌─────────────────────────┐ ┌─────────────────────────┐ ┌────────────────┐  │
│ │ File Explorer Sidebar   │ │ Markdown Summary Stream │ │ Metric Badges  │  │
│ └─────────────────────────┘ └─────────────────────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack Matrix

| Domain | Technology | Implementation Role |
| :--- | :--- | :--- |
| **Interface** | Streamlit | Reactive frontend, collapsible sidebars, real-time streaming |
| **Inference Engine** | Ollama API / Client | Local execution of CodeLlama, Llama 3, and Mistral |
| **Parsing & Chunking** | Python AST & Custom Chunker | Code traversal, token window management, semantic boundaries |
| **Testing** | Pytest (`pytest.ini`) | Test harness verifying tree generation and token extraction |
| **Environment** | Python 3.10+ | Core language environment |

---

## ⚙️ Reproducible Quickstart & Setup

### Prerequisites
1. Python 3.10 or newer.
2. [Ollama installed](https://ollama.ai) with a local model pulled:
   ```bash
   ollama pull llama3
   # Or: ollama pull codellama
   ```

### 1. Clone the Repository
```bash
git clone https://github.com/keerthi19hub/GITHUB-CODE-EXPLAINER.git
cd GITHUB-CODE-EXPLAINER
```

### 2. Setup Virtual Environment & Dependencies
```bash
python -m venv venv
venv\Scripts\activate  # Linux/macOS: source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Verify Ollama Service & Launch
Ensure Ollama is running (`ollama serve`), then launch the Streamlit app:
```bash
streamlit run app.py
```
Open `http://localhost:8501` to analyze any repository.

---

## 📁 Project Structure

```text
GITHUB-CODE-EXPLAINER/
├── app.py                      # Streamlit application user interface
├── repo_processor.py           # Repository tree crawler and file reader
├── llm_service.py              # Ollama API interaction and prompt templates
├── backend/                    # Core business logic and AST parser components
├── tests/                      # Automated unit tests for crawler and chunker
├── requirements.txt            # Application dependencies
├── pytest.ini                  # Pytest configuration directives
├── runtime.txt                 # Streamlit Cloud Python runtime declaration
├── DEPLOY_ON_STREAMLIT.md      # Deployment guidelines for cloud hosting
└── README.md                   # Production technical documentation
```

---

## 🧪 Testing & Validation

Run the automated test suite verifying codebase indexing and parsing:
```bash
pytest tests/ -v
```

---

## 👩‍💻 Author & Contributions

**Keerthi N**  
- **GitHub:** [@keerthi19hub](https://github.com/keerthi19hub)  
- **Portfolio:** [keerthi19hub.github.io](https://keerthi19hub.github.io)  
- **Role:** Full-stack development, AST parsing architecture, Ollama integration, Streamlit UI, and unit test suite.

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0F172A,0284C7,38BDF8&height=100&section=footer" width="100%" alt="Footer Banner" />
</p>
