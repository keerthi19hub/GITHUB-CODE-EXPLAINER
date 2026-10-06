from __future__ import annotations

import time

import streamlit as st

from backend.service import analyze_repository
from llm_service import get_model_name

st.set_page_config(page_title="GitHub Repository Code Explainer", page_icon="🔎", layout="wide")

st.title("🔎 GitHub Repository Code Explainer")
st.caption("Explain any public HTTPS GitHub repository using a small open-source Hugging Face model running inside this application runtime.")

with st.sidebar:
    st.header("LOCAL GENAI PIPELINE")
    st.write("GitHub → GitPython → Repository Analyzer → Smart Context → Transformers Model → AI Explanation")
    st.divider()
    st.caption(f"Model: {get_model_name()}")
    st.caption("No Ollama • No external backend • No API key")

repo_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/username/repository")

if st.button("Explain this GitHub Repository", type="primary", use_container_width=True):
    if not repo_url.strip():
        st.error("Please enter a public HTTPS GitHub repository URL.")
        st.stop()

    progress_box = st.empty()
    status = st.status("Analyzing repository...", expanded=True)
    stages_seen: list[str] = []

    def progress(stage: str) -> None:
        if stage not in stages_seen:
            stages_seen.append(stage)
            progress_box.info(stage)
            status.write(stage)

    try:
        started = time.perf_counter()
        result = analyze_repository(repo_url.strip(), progress=progress)
        total = time.perf_counter() - started
        status.update(label="Analysis complete", state="complete")
        progress_box.success("08 Finalizing report — complete")

        counts = result["file_counts"]
        st.subheader("Repository Overview")
        cols = st.columns(5)
        cols[0].metric("Total files", len(result["file_inventory"]))
        cols[1].metric("Source", counts.get("SOURCE", 0))
        cols[2].metric("Documentation", counts.get("DOCUMENTATION", 0))
        cols[3].metric("Notebooks", counts.get("NOTEBOOK", 0))
        cols[4].metric("Binary/assets", counts.get("BINARY/ASSET", 0))

        left, right = st.columns(2)
        with left:
            st.markdown("### Technologies")
            st.write(", ".join(result["technologies"]) or "No specific technologies established from repository evidence.")
            st.markdown("### Language counts")
            for language, count in result["language_counts"].items():
                st.write(f"**{language}:** {count}")
        with right:
            st.markdown("### Repository information")
            st.write(f"**Owner:** {result['repository_owner']}")
            st.write(f"**Name:** {result['repository_name']}")
            st.write(f"**Type:** {result['repository_type']}")
            st.write(f"**Files selected for model:** {len(result['selected_files'])}")
            st.write(f"**Model context:** {len(result['code_context']):,} characters")
            st.write(f"**Total analysis time:** {total:.2f}s")

        with st.expander("Repository structure / complete inventory"):
            for item in result["file_inventory"]:
                if item["sensitive"]:
                    st.write(f"🔒 `{item['path']}` — sensitive file (contents protected)")
                else:
                    st.write(f"`{item['path']}` — {item['category']} — {item['size_bytes']:,} bytes")

        with st.expander("Files selected for AI context"):
            for path in result["selected_files"]:
                st.write(f"• `{path}`")

        st.subheader("🤖 AI-Generated Project Explanation")
        st.markdown(result["explanation"])

        with st.expander("Performance"):
            for key, value in result["timings"].items():
                st.write(f"**{key.replace('_', ' ').title()}:** {value:.2f}s")

    except Exception as exc:
        status.update(label="Analysis failed", state="error")
        progress_box.empty()
        st.error(str(exc))
