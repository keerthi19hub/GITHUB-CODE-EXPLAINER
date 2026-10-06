from __future__ import annotations

import os
from typing import Any

import streamlit as st

MODEL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "350"))


def get_model_name() -> str:
    return MODEL_ID


@st.cache_resource(show_spinner=False)
def load_model_and_tokenizer() -> tuple[Any, Any, str]:
    """Load the model once per Streamlit runtime and choose CUDA or CPU safely."""
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
        raise RuntimeError("The open-source Hugging Face model could not be loaded. Please try again after the model finishes downloading.") from exc


def build_prompt(repository: dict[str, Any]) -> str:
    inventory = repository.get("file_inventory", [])
    compact_inventory = "\n".join(
        f"- {item['path']} | {item['category']} | {item['size_bytes']} bytes"
        for item in inventory
        if not item.get("sensitive")
    )
    technologies = ", ".join(repository.get("technologies", [])) or "No specific technologies established"
    tree = "\n".join(repository.get("folder_tree", [])[:250])
    return f"""You are explaining a GitHub repository to a beginner.

Use ONLY the supplied repository evidence.
Do not invent files, technologies, frameworks, databases, APIs, features, or behavior.
If information cannot be determined from the supplied evidence, clearly say that it cannot be determined.

Repository: {repository.get('repository_name')}
Repository type: {repository.get('repository_type')}
Detected technologies from evidence: {technologies}

Repository inventory:
{compact_inventory}

Repository structure:
{tree}

Selected repository context:
{repository.get('code_context', '')}

Explain:
1. Project Overview
2. Main Purpose
3. Repository Structure
4. Important Files
5. Main Technologies
6. How the Application Works
7. Important Code Components
8. Data Flow
9. Dependencies and Configuration
10. How to Run the Project, only when supported by evidence
11. Notable Implementation Details
12. Limitations or missing information

Use simple language while remaining technically useful. Keep the explanation focused and evidence-based."""


def generate_explanation(repository: dict[str, Any]) -> str:
    try:
        import torch
        tokenizer, model, device = load_model_and_tokenizer()
        prompt = build_prompt(repository)
        messages = [
            {"role": "system", "content": "You are a careful software engineer. Use only supplied evidence and never invent repository facts."},
            {"role": "user", "content": prompt},
        ]
        if hasattr(tokenizer, "apply_chat_template"):
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            text = f"System: {messages[0]['content']}\nUser: {prompt}\nAssistant:"
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=8192)
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
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
        raise RuntimeError("AI explanation generation failed. The repository was processed, but the model could not produce an explanation.") from exc
