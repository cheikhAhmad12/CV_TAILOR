import ast
import json
import math
import os
import re
from typing import Any

import requests
from huggingface_hub import InferenceClient


API_BASE = "https://app.doctorat.gouv.fr/api"
SEARCH_ENDPOINT = f"{API_BASE}/propositions-these"
DETAIL_ENDPOINT = f"{SEARCH_ENDPOINT}/proposition"
SOURCE_NAME = "doctorat_gouv"
USER_AGENT = "CV-Tailor/0.3 (+https://app.doctorat.gouv.fr)"
HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "as",
    "at",
    "au",
    "aux",
    "avec",
    "by",
    "ce",
    "ces",
    "cette",
    "dans",
    "data",
    "de",
    "des",
    "du",
    "en",
    "engineering",
    "engineer",
    "et",
    "experience",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "la",
    "le",
    "les",
    "model",
    "models",
    "of",
    "on",
    "ou",
    "par",
    "pour",
    "project",
    "projects",
    "research",
    "skills",
    "software",
    "sur",
    "technical",
    "that",
    "the",
    "their",
    "these",
    "this",
    "to",
    "using",
    "we",
    "with",
}
PREFERRED_SHORT_TOKENS = {
    "ai",
    "cv",
    "ml",
    "nlp",
    "llm",
    "rag",
    "sql",
    "api",
    "cv",
}
RESEARCH_SIGNAL_PATTERNS = [
    (re.compile(r"\b(llm|large language models?)\b", re.I), "large language models"),
    (re.compile(r"\brag\b", re.I), "retrieval augmented generation"),
    (re.compile(r"\b(nlp|natural language processing)\b", re.I), "natural language processing"),
    (re.compile(r"\b(machine learning|ml)\b", re.I), "machine learning"),
    (re.compile(r"\bdeep learning\b", re.I), "deep learning"),
    (re.compile(r"\bcomputer vision\b", re.I), "computer vision"),
    (re.compile(r"\bmultimodal\b", re.I), "multimodal AI"),
    (re.compile(r"\b(pytorch|tensorflow|keras)\b", re.I), "deep learning frameworks"),
    (re.compile(r"\bfastapi\b", re.I), "ML systems and APIs"),
    (re.compile(r"\bdocker\b", re.I), "containerized ML systems"),
    (re.compile(r"\bdrug discovery\b", re.I), "AI for drug discovery"),
    (re.compile(r"\bhealth|medical|biomedical\b", re.I), "AI for health"),
    (re.compile(r"\barchitecture|urban|building\b", re.I), "AI for architecture and cities"),
    (re.compile(r"\bgraph\b", re.I), "graph learning"),
    (re.compile(r"\btime series\b", re.I), "time series modeling"),
]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


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
        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return parsed
        raise


def _post_hf_chat(
    hf_token: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: int = 75,
) -> str:
    response = requests.post(
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
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def fetch_thesis_offers(
    page: int,
    size: int,
    discipline: str = "",
    localisation: str = "",
) -> dict[str, Any]:
    params = {"page": page, "size": size}
    if discipline:
        params["discipline"] = discipline
    if localisation:
        params["localisation"] = localisation

    response = requests.get(
        SEARCH_ENDPOINT,
        params=params,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=25,
    )
    response.raise_for_status()
    return response.json()


def fetch_thesis_offer_detail(source_id: str) -> dict[str, Any]:
    response = requests.get(
        DETAIL_ENDPOINT,
        params={"id": source_id},
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=25,
    )
    response.raise_for_status()
    return response.json()


def _normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", token.lower())


def _is_useful_keyword(keyword: str) -> bool:
    text = str(keyword or "").strip()
    if not text:
        return False
    normalized = _normalize_token(text)
    if not normalized:
        return False
    if normalized in STOPWORDS:
        return False
    if len(normalized) < 4 and normalized not in PREFERRED_SHORT_TOKENS:
        return False
    if normalized.isdigit():
        return False
    return True


def _extract_research_signals(parsed_cv: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    text_parts = [
        str(parsed_cv.get("summary", "")),
        " ".join(parsed_cv.get("skills", []) or []),
        " ".join(str(item) for item in (parsed_cv.get("projects", []) or [])),
    ]
    for experience in parsed_cv.get("experiences", [])[:6]:
        text_parts.append(str(experience.get("title", "")))
        text_parts.append(str(experience.get("description", "")))

    corpus = " \n ".join(part for part in text_parts if part).strip()
    seen = set()
    for pattern, label in RESEARCH_SIGNAL_PATTERNS:
        if pattern.search(corpus):
            normalized = _normalize_token(label)
            if normalized not in seen:
                seen.add(normalized)
                signals.append(label)
    return signals[:10]


def _collect_focus_keywords(parsed_cv: dict[str, Any], limit: int = 12) -> list[str]:
    focus: list[str] = []
    for skill in parsed_cv.get("skills", [])[:20]:
        if _is_useful_keyword(skill):
            focus.append(str(skill).strip())

    for project in parsed_cv.get("projects", [])[:6]:
        for token in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\-\+]{2,}", str(project)):
            if _is_useful_keyword(token):
                focus.append(token)

    for experience in parsed_cv.get("experiences", [])[:4]:
        for token in re.findall(
            r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\-\+]{2,}",
            " ".join(
                [
                    str(experience.get("title", "")),
                    str(experience.get("description", "")),
                ]
            ),
        ):
            if _is_useful_keyword(token):
                focus.append(token)

    deduped: list[str] = []
    seen = set()
    for item in focus:
        normalized = _normalize_token(item)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(str(item).strip())
        if len(deduped) >= limit:
            break
    return deduped


def build_profile_search_intent(parsed_cv: dict[str, Any]) -> dict[str, Any]:
    summary = str(parsed_cv.get("summary", "")).strip()
    keywords = _collect_focus_keywords(parsed_cv, limit=16)
    research_signals = _extract_research_signals(parsed_cv)

    experience_titles: list[str] = []
    for experience in parsed_cv.get("experiences", [])[:3]:
        title = str(experience.get("title", "")).strip()
        if title:
            experience_titles.append(title)

    return {
        "keywords": keywords,
        "summary": summary[:500],
        "research_signals": research_signals,
        "experience_titles": experience_titles,
        "projects": [str(item).strip() for item in (parsed_cv.get("projects", []) or [])[:4] if str(item).strip()],
    }


def _intent_text(intent: dict[str, Any]) -> str:
    parts = [
        f"Candidate summary: {str(intent.get('summary', '')).strip()}",
        f"Research interests: {', '.join(intent.get('research_signals', []) or [])}",
        f"Core skills: {', '.join(intent.get('keywords', []) or [])}",
        f"Recent roles: {', '.join(intent.get('experience_titles', []) or [])}",
        f"Relevant projects: {', '.join(intent.get('projects', []) or [])}",
    ]
    return "\n".join(part for part in parts if not part.endswith(": ")).strip()


def _offer_text(offer: dict[str, Any]) -> str:
    return " ".join(
        [
            str(offer.get("theseTitre", "")).strip(),
            str(offer.get("specialite", "")).strip(),
            str(offer.get("thematiqueRecherche", "")).strip(),
            str(offer.get("resume", "")).strip(),
            str(offer.get("profilRecherche", "")).strip(),
            str(offer.get("uniteRechercheLibelle", "")).strip(),
            " ".join(str(v) for v in (offer.get("motsCles") or {}).values()),
            " ".join(str(v) for v in (offer.get("motsClesAnglais") or {}).values()),
        ]
    ).strip()


def _pool_embedding(raw_embedding: Any) -> list[float]:
    if hasattr(raw_embedding, "tolist"):
        raw_embedding = raw_embedding.tolist()
    if not isinstance(raw_embedding, list):
        return []
    if raw_embedding and isinstance(raw_embedding[0], list):
        dim = len(raw_embedding[0])
        pooled = [0.0] * dim
        for token_vec in raw_embedding:
            for i, value in enumerate(token_vec):
                pooled[i] += float(value)
        token_count = max(len(raw_embedding), 1)
        return [value / token_count for value in pooled]
    return [float(value) for value in raw_embedding]


def _lexical_score(offer: dict[str, Any], intent: dict[str, Any]) -> tuple[float, list[str]]:
    keywords = [keyword for keyword in intent.get("keywords", []) if _is_useful_keyword(keyword)]
    haystack = _offer_text(offer).lower()

    hits: list[str] = []
    score = 0.0
    for keyword in keywords:
        key = keyword.strip().lower()
        if not key:
            continue
        if len(key) >= 4 and " " not in key and "-" not in key and "+" not in key:
            matched = bool(re.search(rf"\b{re.escape(key)}\b", haystack))
        else:
            matched = key in haystack
        if matched:
            hits.append(keyword)
            score += 8.0 if len(_normalize_token(key)) > 4 else 4.0

    if any(term in haystack for term in ["phd", "doctorat", "thèse", "these", "cifre"]):
        score += 10.0

    return min(score, 100.0), hits


def score_thesis_offer(
    offer: dict[str, Any],
    intent: dict[str, Any],
    semantic_similarity: float | None = None,
) -> tuple[float, str]:
    lexical_score, hits = _lexical_score(offer, intent)
    semantic_score = 0.0
    if semantic_similarity is not None:
        semantic_score = max(0.0, min(100.0, semantic_similarity * 100.0))

    if semantic_similarity is None:
        final_score = lexical_score
    else:
        final_score = (semantic_score * 0.75) + (lexical_score * 0.25)

    final_score = round(min(final_score, 100.0), 2)
    if hits and semantic_similarity is not None:
        return final_score, (
            f"Semantic match {semantic_similarity:.3f}; lexical hits: {', '.join(hits[:5])}"
        )
    if semantic_similarity is not None:
        return final_score, f"Semantic match {semantic_similarity:.3f} based on thesis topic similarity"
    if hits:
        return final_score, f"Matched profile keywords: {', '.join(hits[:5])}"

    return final_score, "Weak direct overlap; retained as potentially relevant doctoral offer"


def _rerank_top_thesis_offers_with_llm(
    ranked_items: list[tuple[dict[str, Any], float, str]],
    intent: dict[str, Any],
    eligible_source_ids: set[str],
) -> list[tuple[dict[str, Any], float, str]]:
    hf_token = os.getenv("HF_TOKEN", "").strip()
    if not hf_token or len(ranked_items) < 2:
        return ranked_items

    top_k = min(len(ranked_items), 10)
    candidates = [
        item for item in ranked_items[:top_k]
        if str(
            item[0].get("id")
            or item[0].get("propositionId")
            or item[0].get("theseId")
            or item[0].get("theseTitre")
        ).strip() in eligible_source_ids
    ]
    if len(candidates) < 2:
        return ranked_items

    rerank_count = min(len(candidates), 5)
    fallback_by_id: dict[str, tuple[dict[str, Any], float, str]] = {}
    candidate_payload: list[dict[str, Any]] = []
    for item in candidates:
        offer, score, reason = item
        source_id = str(
            offer.get("id")
            or offer.get("propositionId")
            or offer.get("theseId")
            or offer.get("theseTitre")
        ).strip()
        fallback_by_id[source_id] = item
        candidate_payload.append(
            {
                "source_id": source_id,
                "title": str(offer.get("theseTitre", "")).strip(),
                "speciality": str(offer.get("specialite", "")).strip(),
                "research_theme": str(offer.get("thematiqueRecherche", "")).strip(),
                "candidate_profile": str(offer.get("profilRecherche", "")).strip()[:500],
                "summary": str(offer.get("resume", "")).strip()[:700],
                "lab_name": str(offer.get("uniteRechercheLibelle", "")).strip(),
                "city": str(offer.get("uniteRechercheVille", "")).strip(),
                "embedding_score": round(score, 2),
                "baseline_reason": reason,
            }
        )

    prompt = {
        "candidate_profile": {
            "summary": intent.get("summary", ""),
            "research_interests": intent.get("research_signals", []),
            "core_skills": intent.get("keywords", []),
            "recent_roles": intent.get("experience_titles", []),
            "relevant_projects": intent.get("projects", []),
        },
        "thesis_offers": candidate_payload,
        "instructions": (
            "Rank the most relevant doctoral thesis offers for this candidate. "
            f"Return exactly {rerank_count} offers or fewer if clearly irrelevant. "
            "Prioritize research-topic alignment, methodological alignment, and plausible continuity with the candidate profile. "
            "Use embedding_score as one signal only. "
            "Do not infer any missing background, domain, degree, or laboratory experience. "
            "Use only the candidate facts provided in candidate_profile. "
            "Output strict JSON only with this exact shape: "
            '{"selected_offers":[{"source_id":"...","score":88.0}]}'
        ),
    }

    primary_model = os.getenv("GEN_MODEL", "google/gemma-2-2b-it").strip()
    fallback_model = os.getenv("GEN_FALLBACK_MODEL", "meta-llama/Llama-3.1-8B-Instruct").strip()
    models = [model for model in [primary_model, fallback_model] if model]

    parsed: dict[str, Any] = {}
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
                            "You are a strict JSON ranking engine for doctoral offers. "
                            "Never invent profile facts. Always return valid JSON with key selected_offers."
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
                                "Convert the input into strict JSON only. "
                                'Output exactly {"selected_offers":[{"source_id":"...","score":0}]}.'
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

    selected = parsed.get("selected_offers", []) if parsed else []
    if not isinstance(selected, list) or not selected:
        return ranked_items

    reranked: list[tuple[dict[str, Any], float, str]] = []
    seen = set()
    profile_focus = intent.get("research_signals", []) or intent.get("keywords", []) or []
    profile_focus_text = ", ".join(str(item).strip() for item in profile_focus[:4] if str(item).strip())
    for item in selected:
        source_id = str(item.get("source_id", "")).strip()
        if not source_id or source_id in seen or source_id not in fallback_by_id:
            continue
        seen.add(source_id)
        offer, baseline_score, baseline_reason = fallback_by_id[source_id]
        llm_score = float(item.get("score", baseline_score) or baseline_score)
        llm_score = max(0.0, min(100.0, llm_score))
        if profile_focus_text:
            reason = f"LLM rerank guided by profile focus: {profile_focus_text}. Baseline: {baseline_reason}"
        else:
            reason = f"LLM rerank. Baseline: {baseline_reason}"
        reranked.append((offer, round(llm_score, 2), reason))

    if not reranked:
        return ranked_items

    remaining = [item for item in ranked_items if str(
        item[0].get("id") or item[0].get("propositionId") or item[0].get("theseId") or item[0].get("theseTitre")
    ).strip() not in seen]
    return reranked + remaining


def score_thesis_offers(offers: list[dict[str, Any]], intent: dict[str, Any]) -> list[tuple[dict[str, Any], float, str]]:
    if not offers:
        return []

    semantic_similarities: list[float | None] = [None] * len(offers)
    hf_token = os.getenv("HF_TOKEN", "").strip()
    tei_model = os.getenv("TEI_MODEL", "sentence-transformers/all-MiniLM-L6-v2").strip()
    intent_text = _intent_text(intent)

    if hf_token and intent_text:
        try:
            client = InferenceClient(api_key=hf_token)
            embeddings = client.feature_extraction(
                [intent_text] + [_offer_text(offer) for offer in offers],
                model=tei_model,
            )
            vectors = [_pool_embedding(item) for item in embeddings]
            if vectors and vectors[0]:
                query_vector = vectors[0]
                semantic_similarities = [
                    _cosine(query_vector, vector) if vector else 0.0 for vector in vectors[1:]
                ]
        except Exception:
            semantic_similarities = [None] * len(offers)

    scored: list[tuple[dict[str, Any], float, str]] = []
    eligible_source_ids: set[str] = set()
    for index, offer in enumerate(offers):
        lexical_score, hits = _lexical_score(offer, intent)
        semantic_similarity = semantic_similarities[index]
        score, reason = score_thesis_offer(
            offer=offer,
            intent=intent,
            semantic_similarity=semantic_similarity,
        )
        scored.append((offer, score, reason))

        source_id = str(
            offer.get("id")
            or offer.get("propositionId")
            or offer.get("theseId")
            or offer.get("theseTitre")
        ).strip()
        semantic_ok = semantic_similarity is not None and semantic_similarity >= 0.10
        mixed_ok = semantic_similarity is not None and semantic_similarity >= 0.05 and len(hits) >= 1
        lexical_ok = lexical_score >= 16.0 and len(hits) >= 2
        if source_id and (semantic_ok or mixed_ok or lexical_ok):
            eligible_source_ids.add(source_id)

    scored.sort(key=lambda item: item[1], reverse=True)
    return _rerank_top_thesis_offers_with_llm(scored, intent, eligible_source_ids)


def normalize_thesis_offer(offer: dict[str, Any], score: float, reason: str) -> dict[str, Any]:
    source_id = str(
        offer.get("id")
        or offer.get("propositionId")
        or offer.get("theseId")
        or offer.get("theseTitre")
    ).strip()
    detail_url = str(offer.get("_detail_url", "")).strip()
    if not detail_url and source_id:
        detail_url = f"https://app.doctorat.gouv.fr/proposition?id={source_id}"
    return {
        "source": str(offer.get("_source", SOURCE_NAME)).strip() or SOURCE_NAME,
        "source_id": source_id,
        "title": str(offer.get("theseTitre", "")).strip(),
        "lab_name": str(offer.get("uniteRechercheLibelle", "")).strip(),
        "city": str(offer.get("uniteRechercheVille", "")).strip(),
        "speciality": str(offer.get("specialite", "")).strip(),
        "research_theme": str(offer.get("thematiqueRecherche", "")).strip(),
        "summary": str(offer.get("resume", "")).strip(),
        "candidate_profile": str(offer.get("profilRecherche", "")).strip(),
        "application_url": str(offer.get("_application_url") or offer.get("urlCandidature", "")).strip(),
        "detail_url": detail_url,
        "funding_type": str(offer.get("typeFinancement", "")).strip(),
        "contact_name": str(offer.get("contactNom", "")).strip(),
        "match_score": score,
        "match_reason": reason,
        "raw_payload": offer,
    }


def thesis_offer_to_raw_text(offer: dict[str, Any]) -> str:
    parts = [
        f"Title: {offer.get('title', '')}",
        f"Lab: {offer.get('lab_name', '')}",
        f"City: {offer.get('city', '')}",
        f"Speciality: {offer.get('speciality', '')}",
        f"Research Theme: {offer.get('research_theme', '')}",
        f"Funding Type: {offer.get('funding_type', '')}",
        f"Candidate Profile: {offer.get('candidate_profile', '')}",
        f"Summary: {offer.get('summary', '')}",
        f"Application URL: {offer.get('application_url', '')}",
        f"Detail URL: {offer.get('detail_url', '')}",
        f"Match Reason: {offer.get('match_reason', '')}",
    ]
    return "\n\n".join(part for part in parts if part and not part.endswith(": "))
