"""
Registry of job sources. Each source is a class implementing BaseScraper.
Users can add custom API sources from the UI (stored in data/sources.json).
"""
import json
import os
from typing import List, Dict

from config import DATA_DIR

SOURCES_PATH = os.path.join(DATA_DIR, "sources.json")


def builtin_sources() -> List[dict]:
    """Sources that ship with the app. All implement search(query, skills, min_period)."""
    return [
        {"id": "remotive", "name": "Remotive", "kind": "api", "enabled": True,
         "class": "scrapers.remotive.RemotiveScraper"},
        {"id": "jobicy",   "name": "Jobicy",   "kind": "api", "enabled": True,
         "class": "scrapers.remotive.JobicyScraper"},
        {"id": "ciee_pr",  "name": "CIEE-PR",  "kind": "scrape", "enabled": False,
         "class": "scrapers.ciee_pr.CieePrScraper",
         "note": "Requires CIEE_PR_CPF and CIEE_PR_SENHA in .env"},
        {"id": "puc_car",  "name": "PUC Carreiras", "kind": "scrape", "enabled": False,
         "class": "scrapers.puc_carreiras.PucCarreirasScraper",
         "note": "Requires PUC_CPF and PUC_SENHA in .env"},
    ]


def load_user_sources() -> List[dict]:
    if not os.path.exists(SOURCES_PATH):
        return []
    try:
        with open(SOURCES_PATH) as f:
            return json.load(f)
    except Exception:
        return []


def save_user_sources(sources: List[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SOURCES_PATH, "w") as f:
        json.dump(sources, f, indent=2)


def all_sources() -> List[dict]:
    """Builtins + user-added. Builtins can be toggled on/off but not deleted."""
    builtins = builtin_sources()
    user = load_user_sources()
    # Merge enabled flags persisted for builtins
    persisted = {s["id"]: s for s in user if s.get("kind") == "_override"}
    for b in builtins:
        if b["id"] in persisted:
            b["enabled"] = persisted[b["id"]].get("enabled", b["enabled"])
    # Real user sources (kind != _override)
    real_user = [s for s in user if s.get("kind") != "_override"]
    return builtins + real_user


def toggle_source(source_id: str, enabled: bool) -> None:
    """Persist the enabled flag for a builtin source."""
    user = load_user_sources()
    overrides = [s for s in user if s.get("kind") == "_override" and s["id"] == source_id]
    if overrides:
        overrides[0]["enabled"] = enabled
    else:
        user.append({"id": source_id, "kind": "_override", "enabled": enabled})
    save_user_sources(user)


def add_api_source(name: str, url_template: str, json_path_title: str,
                   json_path_company: str, json_path_url: str,
                   json_path_location: str = "") -> dict:
    """
    Add a JSON-API source. url_template uses {query} placeholder.
    JSON paths are dot-separated, e.g. 'jobs.0.title' or 'results.title'.
    This is best-effort: if the response shape differs, the source just returns [].
    """
    src = {
        "id": f"user_{name.lower().replace(' ', '_')}",
        "name": name,
        "kind": "api",
        "enabled": True,
        "url_template": url_template,
        "map": {
            "title": json_path_title,
            "company": json_path_company,
            "url": json_path_url,
            "location": json_path_location,
        },
    }
    user = load_user_sources()
    user.append(src)
    save_user_sources(user)
    return src