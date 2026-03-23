import os
import re
from html import unescape
from typing import Any

import requests


ANRT_CIFRE_SOURCE = "anrt_cifre"
ANRT_CIFRE_BASE_URL = "https://offres-et-candidatures-cifre.anrt.asso.fr"
LOGIN_PATH = "/login"
DT_LIST_PATH = "/espace-membre/offre/dtList"
DETAIL_PATH = "/espace-membre/offre/detail"


def _strip_html(text: str) -> str:
    cleaned = re.sub(r"<br\s*/?>", "\n", str(text or ""), flags=re.I)
    cleaned = re.sub(r"</p\s*>", "\n\n", cleaned, flags=re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _login_session() -> requests.Session:
    email = os.getenv("ANRT_CIFRE_EMAIL", "").strip()
    password = os.getenv("ANRT_CIFRE_PASSWORD", "").strip()
    if not email or not password:
        raise RuntimeError("ANRT_CIFRE_EMAIL / ANRT_CIFRE_PASSWORD are not set")

    session = requests.Session()
    login_url = f"{ANRT_CIFRE_BASE_URL}{LOGIN_PATH}"
    login_page = session.get(login_url, timeout=30)
    login_page.raise_for_status()

    match = re.search(r'name="authToken"[^>]*value="([^"]+)"', login_page.text)
    auth_token = match.group(1).strip() if match else ""
    if not auth_token:
        raise RuntimeError("ANRT login token not found")

    response = session.post(
        login_url,
        data={
            "authToken": auth_token,
            "email": email,
            "password": password,
        },
        headers={"Referer": login_url},
        allow_redirects=True,
        timeout=30,
    )
    response.raise_for_status()
    if "/espace-membre/dashboard" not in response.url:
        raise RuntimeError("ANRT authentication failed")
    return session


def _fetch_offer_batch(
    session: requests.Session,
    offre_type: str,
    start: int,
    length: int,
) -> list[dict[str, Any]]:
    response = session.post(
        f"{ANRT_CIFRE_BASE_URL}{DT_LIST_PATH}",
        data={
            "draw": 1,
            "start": start,
            "length": length,
            "offreType": offre_type,
            "filter_ouverte": "",
            "filter_enseigne": "",
            "filter_secteur": "",
            "filter_discipline": "",
            "filter_categorie": "",
        },
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{ANRT_CIFRE_BASE_URL}/espace-membre/offre-list/{offre_type}",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", []) or []


def _normalize_anrt_offer(raw_offer: dict[str, Any], offre_type: str) -> dict[str, Any]:
    crypt = str(raw_offer.get("crypt", "")).strip()
    detail_url = f"{ANRT_CIFRE_BASE_URL}{DETAIL_PATH}/{crypt}" if crypt else ""
    description = _strip_html(str(raw_offer.get("these", "")))
    entite = "" if raw_offer.get("entite") is None else str(raw_offer.get("entite", "")).strip()
    entreprise = "" if raw_offer.get("rs") is None else str(raw_offer.get("rs", "")).strip()
    lab_name = entite or entreprise
    if entite and entreprise and entreprise.lower() not in entite.lower():
        lab_name = f"{entreprise} - {entite}"

    return {
        "id": f"{offre_type}:{raw_offer.get('id', '')}",
        "_source": ANRT_CIFRE_SOURCE,
        "_detail_url": detail_url,
        "_application_url": detail_url,
        "theseTitre": str(raw_offer.get("titre", "")).strip(),
        "specialite": str(raw_offer.get("discipline", "")).strip(),
        "thematiqueRecherche": str(raw_offer.get("secteur", "")).strip(),
        "resume": description,
        "profilRecherche": description[:900],
        "uniteRechercheLibelle": lab_name,
        "uniteRechercheVille": str(raw_offer.get("ville", "")).strip(),
        "typeFinancement": "CIFRE",
        "contactNom": "",
        "motsCles": {
            "discipline": str(raw_offer.get("discipline", "")).strip(),
            "secteur": str(raw_offer.get("secteur", "")).strip(),
            "entreprise": entreprise,
            "type": offre_type,
        },
        "motsClesAnglais": {},
        "raw_payload": raw_offer,
    }


def fetch_anrt_cifre_offers(
    page_limit: int,
    page_size: int,
    discipline: str = "",
    localisation: str = "",
) -> list[dict[str, Any]]:
    session = _login_session()
    normalized: list[dict[str, Any]] = []
    discipline_filter = discipline.strip().lower()
    localisation_filter = localisation.strip().lower()

    for offre_type in ["entreprise", "laboratoire"]:
        for page in range(page_limit):
            batch = _fetch_offer_batch(
                session=session,
                offre_type=offre_type,
                start=page * page_size,
                length=page_size,
            )
            for raw_offer in batch:
                item = _normalize_anrt_offer(raw_offer, offre_type)
                haystack = " ".join(
                    [
                        item.get("theseTitre", ""),
                        item.get("specialite", ""),
                        item.get("thematiqueRecherche", ""),
                        item.get("resume", ""),
                        item.get("uniteRechercheVille", ""),
                    ]
                ).lower()
                if discipline_filter and discipline_filter not in haystack:
                    continue
                if localisation_filter and localisation_filter not in haystack:
                    continue
                normalized.append(item)

    return normalized
