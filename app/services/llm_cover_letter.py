import os
import json
import re
from typing import Any

import requests

HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"


def default_cover_letter_salutation(output_language: str = "fr") -> str:
    return "Dear Hiring Team," if output_language == "en" else "Madame, Monsieur,"


def cover_letter_salutation(parsed_job: dict[str, Any] | None = None, output_language: str = "fr") -> str:
    suggested = str((parsed_job or {}).get("contact_salutation", "")).strip()
    return suggested or default_cover_letter_salutation(output_language)


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
        "contact_salutation": str(parsed_job.get("contact_salutation", "")).strip(),
    }


def _strip_markdown_fences(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("latex"):
            cleaned = cleaned[5:].strip()
        elif cleaned.lower().startswith("tex"):
            cleaned = cleaned[3:].strip()
    return cleaned.strip()


def _normalize_latex_output(text: str) -> str:
    cleaned = _strip_markdown_fences(text)
    if not cleaned:
        return ""

    if cleaned.startswith('"') and cleaned.endswith('"'):
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, str):
                cleaned = parsed
        except Exception:
            pass

    cleaned = cleaned.replace("\r\n", "\n")
    cleaned = cleaned.replace("\\n", "\n")

    # Some models over-escape LaTeX commands like \\documentclass or \\begin.
    cleaned = re.sub(r"(?<!\\)\\\\(?=[A-Za-z@]+)", r"\\", cleaned)
    return cleaned.strip()


def _extract_template_salutation(master_cover_letter_text: str, master_cover_letter_latex: str) -> str:
    text = (master_cover_letter_text or "").strip()
    if text:
        first_para = re.split(r"\n\s*\n", text, maxsplit=1)[0].strip()
        if first_para:
            return first_para

    latex = (master_cover_letter_latex or "").strip()
    match = re.search(r"\\opening\{([^}]*)\}", latex)
    if match:
        return match.group(1).strip()
    return ""


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", (text or "").strip()) if p.strip()]


def _extract_body_paragraphs(text: str) -> list[str]:
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return []

    if re.match(r"^(madame|monsieur|dear|hello|bonjour)\b", paragraphs[0], flags=re.IGNORECASE):
        paragraphs = paragraphs[1:]

    while paragraphs and re.match(
        r"^(cordialement|bien cordialement|sincerely|regards|best regards|merci)",
        paragraphs[-1],
        flags=re.IGNORECASE,
    ):
        paragraphs = paragraphs[:-1]

    return paragraphs


def _template_body_paragraph_count(master_cover_letter_text: str) -> int:
    return len(_extract_body_paragraphs(master_cover_letter_text))


def _split_paragraph_by_sentences(paragraph: str) -> list[str]:
    parts = re.split(r"(?<=[\.\!\?])\s+", paragraph.strip())
    return [p.strip() for p in parts if p.strip()]


def _enforce_body_paragraph_count(paragraphs: list[str], target_count: int) -> list[str]:
    if target_count <= 0:
        return paragraphs

    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    if not paragraphs:
        return paragraphs

    while len(paragraphs) > target_count:
        paragraphs[-2] = f"{paragraphs[-2]} {paragraphs[-1]}".strip()
        paragraphs.pop()

    while len(paragraphs) < target_count:
        split_index = max(range(len(paragraphs)), key=lambda i: len(paragraphs[i]))
        sentences = _split_paragraph_by_sentences(paragraphs[split_index])
        if len(sentences) < 2:
            break
        midpoint = max(1, len(sentences) // 2)
        first = " ".join(sentences[:midpoint]).strip()
        second = " ".join(sentences[midpoint:]).strip()
        paragraphs[split_index : split_index + 1] = [first, second]

    return paragraphs


def _force_salutation(
    text: str,
    output_language: str = "fr",
    parsed_job: dict[str, Any] | None = None,
    target_body_paragraph_count: int = 0,
) -> str:
    salutation = cover_letter_salutation(parsed_job=parsed_job, output_language=output_language)
    cleaned = (text or "").strip()
    if not cleaned:
        return salutation

    body_paragraphs = _extract_body_paragraphs(cleaned)
    body_paragraphs = _enforce_body_paragraph_count(body_paragraphs, target_body_paragraph_count)
    body = "\n\n".join(body_paragraphs).strip()
    return f"{salutation}\n\n{body}".strip() if body else salutation


def generate_cover_letter_with_llm(
    parsed_cv: dict[str, Any],
    parsed_job: dict[str, Any],
    selected_projects: list[dict[str, Any]],
    output_language: str = "fr",
    master_cover_letter_text: str = "",
    master_cover_letter_latex: str = "",
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
    template_salutation = _extract_template_salutation(
        master_cover_letter_text=master_cover_letter_text,
        master_cover_letter_latex=master_cover_letter_latex,
    )
    target_salutation = cover_letter_salutation(parsed_job=parsed_job, output_language=output_language)
    target_body_paragraph_count = _template_body_paragraph_count(master_cover_letter_text)

    user_payload = {
        "language": lang,
        "constraints": {
            "max_words": 230,
            "max_paragraphs": max(target_body_paragraph_count + 1, 5),
            "tone": "professional, concrete, non-generic",
            "format": "plain text only, no markdown, no bullet points",
            "required_salutation": target_salutation,
            "target_body_paragraph_count": target_body_paragraph_count or None,
        },
        "target_job": _job_payload(parsed_job),
        "candidate_profile": _cv_payload(parsed_cv),
        "selected_projects": projects,
        "template_letter": {
            "text": (master_cover_letter_text or "").strip()[:5000],
            "latex_preview": (master_cover_letter_latex or "").strip()[:7000],
            "instruction": (
                "If a template letter is provided, preserve its overall structure, sequencing, and tone "
                "while adapting the content to the target job and candidate profile."
            ),
            "forbidden_reuse": (
                f"Do not reuse template-specific addressees or names such as: {template_salutation}"
                if template_salutation
                else "Do not reuse template-specific addressees or names."
            ),
        },
        "safety": (
            "Use only facts present in the input. Do not invent companies, durations or achievements. "
            "Do not copy recipient names from the template unless they are explicitly present in the target job input."
        ),
    }

    system_prompt = (
        "You are an expert career writer. Generate a concise, high-quality cover letter. "
        "Respect constraints strictly. "
        "If a template letter is provided, reuse its structure and rhetorical flow instead of inventing a new outline. "
        "Never carry over recipient names or named addressees from the template unless they are present in the target job input. "
        f"Use this salutation exactly: {target_salutation}"
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
            cleaned = _strip_markdown_fences(raw)
            if cleaned:
                cleaned = _force_salutation(
                    cleaned,
                    output_language=output_language,
                    parsed_job=parsed_job,
                    target_body_paragraph_count=target_body_paragraph_count,
                )
                return _trim_to_one_page(cleaned, max_words=230)
        except Exception:
            continue

    raise RuntimeError("LLM cover letter generation failed")


def generate_cover_letter_latex_with_llm(
    parsed_cv: dict[str, Any],
    parsed_job: dict[str, Any],
    selected_projects: list[dict[str, Any]],
    master_cover_letter_latex: str,
    output_language: str = "fr",
) -> str:
    hf_token = os.getenv("HF_TOKEN", "").strip()
    if not hf_token:
        raise RuntimeError("HF_TOKEN is not set")

    template = (master_cover_letter_latex or "").strip()
    if not template:
        raise RuntimeError("master_cover_letter_latex is empty")

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
            "output": "Return only complete LaTeX",
            "preserve_template_structure": True,
            "preserve_macros_and_preamble": True,
            "do_not_add_markdown_fences": True,
        },
        "target_job": _job_payload(parsed_job),
        "candidate_profile": _cv_payload(parsed_cv),
        "selected_projects": projects,
        "template_latex": template[:14000],
        "safety": (
            "Use only facts present in the input. Keep the same LaTeX structure and commands whenever possible. "
            "Only adapt the human-readable letter content."
        ),
    }

    system_prompt = (
        "You adapt cover letters in LaTeX. "
        "Return only valid LaTeX. Preserve the provided template structure, preamble, commands, and layout. "
        "Change only the letter content so it fits the job and candidate profile."
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
            cleaned = _normalize_latex_output(raw)
            if "\\begin{document}" in cleaned and "\\end{document}" in cleaned:
                return cleaned
        except Exception:
            continue

    raise RuntimeError("LLM LaTeX cover letter generation failed")
