import json
import re
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from app.models.source_agent_message import SourceAgentMessage


def _extract_first_url(text: str) -> str:
    match = re.search(r"https?://[^\s]+", str(text or ""))
    return match.group(0).strip() if match else ""


def _default_source_name(base_url: str) -> str:
    host = urlparse(base_url).netloc.strip().lower()
    return host or "Nouvelle source"


def _detect_strategy(base_url: str, findings: dict) -> str:
    host = urlparse(base_url).netloc.lower()
    if "doctorat.gouv.fr" in host:
        return "public_api"
    if "offres-et-candidatures-cifre.anrt.asso.fr" in host:
        return "authenticated_json"
    if findings.get("has_login_form") and findings.get("ajax_endpoints"):
        return "authenticated_json"
    if findings.get("has_login_form"):
        return "authenticated_html"
    if findings.get("ajax_endpoints"):
        return "public_api"
    return "public_html"


def inspect_source_url(base_url: str) -> dict:
    response = requests.get(base_url, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    forms = soup.find_all("form")
    has_password = bool(soup.find("input", {"type": "password"}))
    candidate_links = []
    for link in soup.find_all("a", href=True):
        href = urljoin(base_url, link["href"])
        text = " ".join(link.get_text(" ", strip=True).split())
        label = f"{text} -> {href}" if text else href
        lower = label.lower()
        if any(token in lower for token in ["login", "offre", "job", "search", "api", "cifre", "thèse", "these"]):
            candidate_links.append(label)
        if len(candidate_links) >= 8:
            break

    ajax_endpoints = sorted(set(re.findall(r'/(?:api|espace-membre|search)[^"\']+', response.text, flags=re.I)))[:10]
    script_hints = []
    for script in soup.find_all("script", src=True):
        src = urljoin(base_url, script["src"])
        if any(token in src.lower() for token in ["offre", "search", "api", "job", "source"]):
            script_hints.append(src)
        if len(script_hints) >= 8:
            break

    findings = {
        "final_url": response.url,
        "page_title": soup.title.get_text(" ", strip=True) if soup.title else "",
        "status_code": response.status_code,
        "forms_count": len(forms),
        "has_login_form": has_password,
        "candidate_links": candidate_links,
        "ajax_endpoints": ajax_endpoints,
        "script_hints": script_hints,
    }
    findings["strategy"] = _detect_strategy(base_url, findings)
    findings["requires_auth"] = findings["strategy"].startswith("authenticated")
    return findings


def assistant_welcome_message(source_name: str) -> str:
    return (
        f"Session ouverte pour `{source_name}`.\n"
        "Donne-moi une URL ou ecris `inspecte` pour lancer l'inspection de la source."
    )


def summarize_findings(findings: dict) -> str:
    parts = [
        f"Inspection terminee sur {findings.get('final_url', '')}.",
        f"Titre detecte: {findings.get('page_title', '') or 'inconnu'}.",
        f"Strategie recommandee: {findings.get('strategy', 'unknown')}.",
        f"Authentification requise: {'oui' if findings.get('requires_auth') else 'non'}.",
    ]
    if findings.get("candidate_links"):
        parts.append(f"Liens utiles: {', '.join(findings['candidate_links'][:3])}.")
    if findings.get("ajax_endpoints"):
        parts.append(f"Endpoints detectes: {', '.join(findings['ajax_endpoints'][:3])}.")
    parts.append("Ecris `activer` pour enregistrer cette strategie, ou envoie une nouvelle URL.")
    return "\n".join(parts)


def persist_message(db, session_id: int, role: str, content: str) -> SourceAgentMessage:
    message = SourceAgentMessage(session_id=session_id, role=role, content=content)
    db.add(message)
    db.flush()
    return message


def handle_source_agent_message(db, source, session, content: str) -> tuple[dict, str]:
    text = str(content or "").strip()
    lower = text.lower()

    detected_url = _extract_first_url(text)
    if detected_url:
        source.base_url = detected_url
        if not source.name:
            source.name = _default_source_name(detected_url)

    if "inspect" in lower or detected_url:
        if not source.base_url:
            return {}, "Aucune URL enregistree. Envoie une URL complete pour commencer."
        findings = inspect_source_url(source.base_url)
        source.strategy = findings["strategy"]
        source.requires_auth = bool(findings["requires_auth"])
        source.status = "inspected"
        config = {
            "strategy": findings["strategy"],
            "requires_auth": findings["requires_auth"],
            "ajax_endpoints": findings.get("ajax_endpoints", []),
            "candidate_links": findings.get("candidate_links", []),
            "script_hints": findings.get("script_hints", []),
        }
        source.config_json = json.dumps(config, ensure_ascii=False)
        session.draft_config_json = source.config_json
        return findings, summarize_findings(findings)

    if lower == "activer" or "active" in lower:
        source.status = "ready"
        session.status = "ready"
        strategy = source.strategy or "unknown"
        return {}, f"Source activee avec la strategie `{strategy}`."

    if lower == "resume":
        return {}, (
            f"Source: {source.name}\n"
            f"URL: {source.base_url or 'non definie'}\n"
            f"Statut: {source.status}\n"
            f"Strategie: {source.strategy}"
        )

    return {}, (
        "Je peux inspecter une source et proposer une strategie.\n"
        "Actions utiles: envoie une URL, ecris `inspecte`, `resume`, ou `activer`."
    )
