import os
import json
from typing import Any

import requests

HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"


def _post_hf_chat(
    hf_token: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: int = 75,
) -> str:
    resp = requests.post(
        HF_CHAT_URL,
        headers={
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0.3,
            "messages": messages,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _trim_to_one_page(text: str, max_words: int = 230) -> str:
    words = (text or "").strip().split()
    if len(words) <= max_words:
        return (text or "").strip()
    return " ".join(words[:max_words]).strip() + "..."


def _cv_payload(parsed_cv: dict[str, Any]) -> dict[str, Any]:
    experiences = []
    for exp in (parsed_cv.get("experiences") or [])[:4]:
        experiences.append(
            {
                "title": str(exp.get("title", "")).strip(),
                "company": str(exp.get("company", "")).strip(),
                "description": str(exp.get("description", "")).strip()[:260],
            }
        )

    return {
        "summary": str(parsed_cv.get("summary", "")).strip()[:500],
        "skills": (parsed_cv.get("skills") or [])[:20],
        "education": (parsed_cv.get("education") or [])[:4],
        "experiences": experiences,
    }


def _job_payload(parsed_job: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(parsed_job.get("title", "")).strip(),
        "required_skills": (parsed_job.get("required_skills") or [])[:10],
        "preferred_skills": (parsed_job.get("preferred_skills") or [])[:8],
        "responsibilities": (parsed_job.get("responsibilities") or [])[:8],
        "keywords": (parsed_job.get("keywords") or [])[:12],
    }


def generate_cover_letter_with_llm(
    parsed_cv: dict[str, Any],
    parsed_job: dict[str, Any],
    selected_projects: list[dict[str, Any]],
    output_language: str = "fr",
) -> str:
    hf_token = os.getenv("HF_TOKEN", "").strip()
    if not hf_token:
        raise RuntimeError("HF_TOKEN is not set")

    primary_model = os.getenv("GEN_MODEL", "google/gemma-2-2b-it").strip()
    fallback_model = os.getenv("GEN_FALLBACK_MODEL", "meta-llama/Llama-3.1-8B-Instruct").strip()
    models = [m for m in [primary_model, fallback_model] if m]

    lang = "English" if output_language == "en" else "French"
    projects = [
        {
            "name": str(p.get("name", "")).strip(),
            "description": str(p.get("description", "")).strip()[:260],
            "reason": str(p.get("reason", "")).strip()[:180],
        }
        for p in (selected_projects or [])[:3]
    ]

    user_payload = {
        "language": lang,
        "constraints": {
            "max_words": 230,
            "max_paragraphs": 5,
            "tone": "professional, concrete, non-generic",
            "format": "plain text only, no markdown, no bullet points",
        },
        "target_job": _job_payload(parsed_job),
        "candidate_profile": _cv_payload(parsed_cv),
        "selected_projects": projects,
        "safety": "Use only facts present in the input. Do not invent companies, durations or achievements.",
    }

    system_prompt = (
        "You are an expert career writer. Generate a concise, high-quality cover letter. "
        "Respect constraints strictly."
    )

    for model in models:
        try:
            raw = _post_hf_chat(
                hf_token=hf_token,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
            )
            cleaned = raw.strip().strip("`").strip()
            if cleaned:
                return _trim_to_one_page(cleaned, max_words=230)
        except Exception:
            continue

    raise RuntimeError("LLM cover letter generation failed")
