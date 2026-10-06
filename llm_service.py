"""
llm_service.py
==============
Service for loading and running open-source language models locally inside
the Streamlit application runtime.

Why SmolLM2-135M-Instruct?
- Small footprint (~135M parameters, ~270MB on disk).
- Runs directly on CPU with very low RAM usage (under 500MB).
- Self-contained inside the Streamlit Cloud container.
- Eliminates the need for external paid APIs (OpenAI/Gemini/Claude)
  and eliminates the need for a local Ollama server running on a laptop.
"""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

MODEL_ID = os.getenv("MODEL_ID", "HuggingFaceTB/SmolLM2-135M-Instruct")
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "380"))


def get_model_name() -> str:
    """Return the active model identifier."""
    return MODEL_ID


@st.cache_resource(show_spinner=False)
def load_model_and_tokenizer() -> tuple[Any, Any, str]:
    """
    Load the tokenizer and model once per Streamlit runtime session.
    Cached via @st.cache_resource so it does not reload on user interactions.
    Automatically uses CUDA if a GPU is available; otherwise safely defaults to CPU.
    """
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32

        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=dtype,
            low_cpu_mem_usage=True,
        )
        model.to(device)
        model.eval()
        return tokenizer, model, device
    except Exception as exc:
        raise RuntimeError(
            f"The open-source Hugging Face model '{MODEL_ID}' could not be loaded. "
            f"Please verify network connection. Details: {exc}"
        ) from exc


def build_prompt(repository: dict[str, Any]) -> str:
    """
    Construct a grounded, evidence-based prompt from scanned repository data.
    Instructs the LLM to explain the project in beginner-friendly language
    without hallucinating any files, frameworks, or features.
    """
    inventory = repository.get("file_inventory", [])
    compact_inventory = "\n".join(
        f"- {item['path']} ({item['category']}, {item['size_bytes']} bytes)"
        for item in inventory[:40]
        if not item.get("sensitive")
    )
    technologies = ", ".join(repository.get("technologies", [])) or "Not clearly established from the available repository files."
    tree = "\n".join(repository.get("folder_tree", [])[:40])

    return f"""You are a helpful software engineer explaining a GitHub repository to a beginner college student.

CRITICAL INSTRUCTIONS:
- Use ONLY the repository evidence provided below.
- Do NOT invent or assume files, technologies, frameworks, databases, APIs, or features.
- If information is missing or not clearly established from the files, state: "Not clearly established from repository files".
- Write in simple, beginner-friendly language with straightforward explanations.

=== REPOSITORY INFORMATION ===
Repository Name: {repository.get('repository_name')}
Repository Owner: {repository.get('repository_owner', 'Unknown')}
Project Type: {repository.get('repository_type')}
Technologies Detected from Evidence: {technologies}

=== REPOSITORY STRUCTURE ===
{tree}

=== FILE INVENTORY SAMPLE ===
{compact_inventory}

=== EXTRACTED CODE & DOCUMENTATION ===
{repository.get('code_context', '')}

=== TASK ===
Provide a beginner-friendly explanation structured with the following exact sections:
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
11. How to Run It, if this can be established from the repository
12. Limitations / Missing Information
"""


def generate_explanation(repository: dict[str, Any]) -> str:
    """
    Generate an explanation of the repository using the in-process open-source model.
    Uses repetition penalties and token limits for low latency and coherent output.
    """
    try:
        import torch

        tokenizer, model, device = load_model_and_tokenizer()
        prompt = build_prompt(repository)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a careful software engineer explaining codebases to students. "
                    "Use strictly the provided repository evidence. Never hallucinate facts."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        if hasattr(tokenizer, "apply_chat_template"):
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            text = f"System: {messages[0]['content']}\nUser: {prompt}\nAssistant:"

        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=4096)
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                repetition_penalty=1.15,
                no_repeat_ngram_size=3,
                pad_token_id=tokenizer.eos_token_id,
            )

        generated = output[0][inputs["input_ids"].shape[1]:]
        answer = tokenizer.decode(generated, skip_special_tokens=True).strip()

        if not answer:
            raise RuntimeError("The model returned an empty explanation.")

        return answer

    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"AI explanation generation failed. The repository was scanned successfully, "
            f"but the language model could not produce an explanation: {exc}"
        ) from exc
