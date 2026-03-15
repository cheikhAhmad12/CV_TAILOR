import json
import math
import os
import ast
from typing import Any

import requests
from huggingface_hub import InferenceClient

from app.schemas.github import GithubProject

HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _project_text(p: GithubProject) -> str:
    return " ".join(
        [
            p.name or "",
            p.description or "",
            (p.readme_summary or "")[:1500],
            " ".join(p.languages or []),
            " ".join(p.topics or []),
        ]
    ).strip()


def _job_text(parsed_job: dict[str, Any]) -> str:
    return " ".join(
        [
            str(parsed_job.get("title", "")),
            " ".join(parsed_job.get("required_skills", []) or []),
            " ".join(parsed_job.get("preferred_skills", []) or []),
            " ".join(parsed_job.get("responsibilities", []) or []),
            " ".join(parsed_job.get("keywords", []) or []),
        ]
    ).strip()


def _parse_json_content(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except Exception:
        obj = ast.literal_eval(text)
        if isinstance(obj, dict):
            return obj
        raise


def _post_hf_chat(
    hf_token: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: int = 60,
) -> str:
    resp = requests.post(
        HF_CHAT_URL,
        headers={
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0.1,
            "messages": messages,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _vector_scores(
    client: InferenceClient,
    tei_model: str,
    projects: list[GithubProject],
    parsed_job: dict[str, Any],
) -> list[tuple[GithubProject, float]]:
    jt = _job_text(parsed_job)
    project_texts = [_project_text(p) for p in projects]
    embeddings = client.feature_extraction([jt] + project_texts, model=tei_model)

    vectors: list[list[float]] = []
    for emb in embeddings:
        if hasattr(emb, "tolist"):
            emb = emb.tolist()
        # If token-level vectors are returned, mean-pool them.
        if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], list):
            dim = len(emb[0])
            pooled = [0.0] * dim
            for token_vec in emb:
                for i, v in enumerate(token_vec):
                    pooled[i] += float(v)
            count = max(len(emb), 1)
            vectors.append([v / count for v in pooled])
        else:
            vectors.append([float(v) for v in list(emb)])

    job_vec = vectors[0]
    scored: list[tuple[GithubProject, float]] = []
    for i, project in enumerate(projects):
        sim = _cosine(job_vec, vectors[i + 1])
        scored.append((project, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def rerank_projects_with_llm(
    projects: list[GithubProject],
    parsed_job: dict[str, Any],
    top_k: int = 3,
) -> list[dict[str, Any]]:
    if not projects:
        return []

    hf_token = os.getenv("HF_TOKEN", "").strip()
    if not hf_token:
        raise RuntimeError("HF_TOKEN is not set")

    gen_model = os.getenv("GEN_MODEL", "google/gemma-2-2b-it").strip()
    tei_model = os.getenv("TEI_MODEL", "sentence-transformers/all-MiniLM-L6-v2").strip()

    client = InferenceClient(api_key=hf_token)
    scored = _vector_scores(client, tei_model, projects, parsed_job)

    # No heuristic prefilter: keep all projects for LLM decision.
    candidate_payload = []
    for project, sim in scored:
        candidate_payload.append(
            {
                "name": project.name,
                "semantic_score": round(float(sim), 6),
                "description": project.description or "",
                "readme_summary": (project.readme_summary or "")[:1200],
                "languages": project.languages or [],
                "topics": project.topics or [],
                "html_url": project.html_url or "",
            }
        )

    def vector_only_output(reason_label: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for project, sim in scored[:top_k]:
            out.append(
                {
                    "name": project.name,
                    "score": round(max(0.0, min(100.0, sim * 100.0)), 2),
                    "reason": f"{reason_label} (similarity={sim:.3f})",
                    "description": project.description or "",
                    "readme_summary": project.readme_summary or "",
                    "languages": project.languages or [],
                    "topics": project.topics or [],
                    "html_url": project.html_url or "",
                }
            )
        return out

    prompt = {
        "job": {
            "title": parsed_job.get("title", ""),
            "required_skills": parsed_job.get("required_skills", []),
            "preferred_skills": parsed_job.get("preferred_skills", []),
            "responsibilities": parsed_job.get("responsibilities", []),
            "keywords": parsed_job.get("keywords", []),
        },
        "projects": candidate_payload,
        "instructions": (
            "Rank the projects by relevance to the job. "
            f"Return at most {top_k} items. "
            "Use the semantic_score as one signal, but decide with full context. "
            "Output JSON only with this exact shape: "
            '{"selected_projects":[{"name":"...","score":88.5,"reason":"..."}]}'
        ),
    }

    model_fallback = os.getenv("GEN_FALLBACK_MODEL", "meta-llama/Llama-3.1-8B-Instruct").strip()
    models = [m for m in [gen_model, model_fallback] if m]

    parsed = {}
    raw_output = ""
    for model in models:
        try:
            raw_output = _post_hf_chat(
                hf_token=hf_token,
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict JSON ranking engine. "
                            "Always return only valid JSON with key selected_projects."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
            )
            parsed = _parse_json_content(raw_output)
            if parsed:
                break
        except Exception:
            continue

    if not parsed and raw_output:
        for model in models:
            try:
                repaired = _post_hf_chat(
                    hf_token=hf_token,
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Convert input text into strict JSON only. "
                                "Output exactly: {\"selected_projects\":[{\"name\":\"...\",\"score\":0,\"reason\":\"...\"}]}"
                            ),
                        },
                        {"role": "user", "content": raw_output},
                    ],
                )
                parsed = _parse_json_content(repaired)
                if parsed:
                    break
            except Exception:
                continue

    if not parsed:
        return vector_only_output("Vector similarity ranking")

    selected = parsed.get("selected_projects", [])

    projects_by_name = {p.name: p for p in projects}
    ranked: list[dict[str, Any]] = []
    seen = set()

    for item in selected:
        name = str(item.get("name", "")).strip()
        if not name or name in seen or name not in projects_by_name:
            continue
        seen.add(name)
        p = projects_by_name[name]
        score = float(item.get("score", 0.0))
        score = max(0.0, min(100.0, score))
        ranked.append(
            {
                "name": p.name,
                "score": round(score, 2),
                "reason": str(item.get("reason", "HF LLM relevance ranking")).strip(),
                "description": p.description or "",
                "readme_summary": p.readme_summary or "",
                "languages": p.languages or [],
                "topics": p.topics or [],
                "html_url": p.html_url or "",
            }
        )
        if len(ranked) >= top_k:
            break

    if ranked:
        return ranked

    return vector_only_output("Vector similarity ranking (LLM empty output)")
