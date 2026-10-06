"""
app.py
======
Main Streamlit application for the Local GitHub Repository Code Explainer.
Entrypoint for Streamlit Community Cloud deployment:
    streamlit run app.py

Features:
- Self-contained: directly calls the backend service layer (no separate server process needed).
- Fully open-source: runs HuggingFaceTB/SmolLM2-135M-Instruct directly in Python via Transformers.
- Safe & read-only: shallow clones repositories (depth=1), never executes untrusted code.
"""

from __future__ import annotations

import time
import streamlit as st

from backend.service import analyze_repository
from llm_service import get_model_name

# Configure page metadata
st.set_page_config(
    page_title="GitHub Repository Code Explainer",
    page_icon="💻",
    layout="wide",
)

# App header
st.title("GitHub Repository Code Explainer")
st.write("Enter a public GitHub repository URL to get a simple-language explanation of the codebase.")

# Sidebar with architecture overview and model status
with st.sidebar:
    st.header("Project Architecture")
    st.markdown(
        """
        ```
        GitHub Repository
               ↓
        Code Processing
               ↓
        Local LLM Inference
               ↓
        Backend Service Layer
               ↓
        Streamlit Frontend
               ↓
        Simple Explanation
        ```
        """
    )
    st.divider()
    st.subheader("Model Information")
    st.write(f"**Model ID:** `{get_model_name()}`")
    st.write("**Runtime:** Transformers & PyTorch (In-Process)")
    st.write("**Inference Mode:** CPU / GPU (CUDA)")
    st.write("**External APIs:** None (100% Free & Open Source)")
    st.caption("Self-contained runtime • No external servers or API keys required.")

# Input section
repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/psf/requests",
    help="Enter any public GitHub repository link to inspect and explain.",
)

col_btn, _ = st.columns([1, 3])
with col_btn:
    explain_clicked = st.button("Explain this GitHub Repository", type="primary", use_container_width=True)

if explain_clicked:
    cleaned_url = repo_url.strip()
    if not cleaned_url:
        st.error("Please enter a public GitHub repository URL (e.g., https://github.com/psf/requests).")
        st.stop()

    status_widget = st.status("Analyzing repository...", expanded=True)
    seen_stages: list[str] = []

    def on_progress(stage: str) -> None:
        if stage not in seen_stages:
            seen_stages.append(stage)
            status_widget.write(f"⏳ {stage}")

    try:
        start_time = time.perf_counter()
        result = analyze_repository(cleaned_url, progress=on_progress)
        total_time = time.perf_counter() - start_time

        status_widget.update(label="Analysis complete!", state="complete", expanded=False)

        # ---------------------------------------------------------
        # 1. Repository Overview
        # ---------------------------------------------------------
        st.header("Repository Overview")
        counts = result.get("file_counts", {})
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Files", len(result.get("file_inventory", [])))
        m2.metric("Source Files", counts.get("SOURCE", 0))
        m3.metric("Documentation", counts.get("DOCUMENTATION", 0))
        m4.metric("Notebooks", counts.get("NOTEBOOK", 0))
        m5.metric("Protected Files", sum(1 for f in result.get("file_inventory", []) if f.get("sensitive")))

        col_left, col_right = st.columns(2)
        with col_left:
            st.write(f"**Repository Name:** `{result.get('repository_name')}`")
            st.write(f"**Repository Owner:** `{result.get('repository_owner')}`")
        with col_right:
            st.write(f"**Detected Type:** {result.get('repository_type')}")
            st.write(f"**Total Analysis Time:** {total_time:.2f} seconds")

        st.divider()

        # ---------------------------------------------------------
        # 2. Technologies Used
        # ---------------------------------------------------------
        st.header("Technologies Used")
        technologies = result.get("technologies", [])
        if technologies:
            st.write("**Detected Technologies & Frameworks (from Evidence):**")
            st.write(", ".join([f"`{t}`" for t in technologies]))
        else:
            st.info("Not clearly established from the available repository files.")

        lang_counts = result.get("language_counts", {})
        if lang_counts:
            st.write("**Programming Languages Found:**")
            lang_cols = st.columns(min(len(lang_counts), 4))
            for i, (lang, count) in enumerate(lang_counts.items()):
                lang_cols[i % len(lang_cols)].write(f"• **{lang}:** {count} file{'s' if count > 1 else ''}")

        st.divider()

        # ---------------------------------------------------------
        # 3. Important Files
        # ---------------------------------------------------------
        st.header("Important Files")
        selected_files = result.get("selected_files", [])
        if selected_files:
            st.write(f"Top {len(selected_files)} high-priority files selected for AI context analysis:")
            for f in selected_files:
                st.write(f"• `{f}`")
        else:
            st.write("No specific primary source files were highlighted.")

        st.divider()

        # ---------------------------------------------------------
        # 4. Repository Structure
        # ---------------------------------------------------------
        st.header("Repository Structure")
        with st.expander("View Full File Inventory and Structure", expanded=False):
            st.write(f"Total files scanned: **{len(result.get('file_inventory', []))}**")
            for item in result.get("file_inventory", []):
                if item.get("sensitive"):
                    st.write(f"🔒 `{item['path']}` — **SENSITIVE FILE** (contents excluded from AI context)")
                else:
                    st.write(f"`{item['path']}` — *{item['category']}* ({item['size_bytes']:,} bytes)")

        st.divider()

        # ---------------------------------------------------------
        # 5. AI-Generated Project Explanation
        # ---------------------------------------------------------
        st.header("AI-Generated Project Explanation")
        st.markdown(result.get("explanation", "*No explanation produced.*"))

        st.divider()

        # ---------------------------------------------------------
        # 6. Performance Information
        # ---------------------------------------------------------
        st.header("Performance Information")
        timings = result.get("timings", {})
        t_cols = st.columns(min(len(timings), 4))
        for idx, (stage, sec) in enumerate(timings.items()):
            label = stage.replace("_", " ").title()
            t_cols[idx % len(t_cols)].metric(f"{label} Time", f"{sec:.2f}s")

        st.divider()

        # ---------------------------------------------------------
        # 7. Model Information
        # ---------------------------------------------------------
        st.header("Model Information")
        st.markdown(
            f"""
            - **Model Identifier:** `{get_model_name()}`
            - **Parameters:** ~135 Million parameters (Lightweight SmolLM2 Instruct architecture)
            - **Framework:** Hugging Face Transformers & PyTorch
            - **Execution Mode:** In-Process Local Inference (runs directly within the Streamlit container runtime)
            - **Memory Caching:** `@st.cache_resource` ensures the model is cached in RAM and only loaded once
            - **Cloud Readiness:** Works independently on Streamlit Community Cloud without needing a running laptop, local servers, or paid cloud LLM API keys.
            """
        )

    except Exception as exc:
        status_widget.update(label="Analysis failed", state="error", expanded=True)
        st.error(f"Error: {exc}")
