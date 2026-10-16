"""
Registry of job sources. Each source is a class implementing BaseScraper.
Users can add custom API sources from the UI (stored in data/sources.json).
"""

import json
import os
from typing import Dict, List  # noqa: UP035

from config import DATA_DIR

SOURCES_PATH = os.path.join(DATA_DIR, "sources.json")


def builtin_sources() -> List[dict]:
    return [
        {
            "id": "remotive",
            "name": "Remotive",
            "kind": "api",
            "enabled": True,
            "class": "scrapers.remotive.RemotiveScraper",
        },
        {
            "id": "jobicy",
            "name": "Jobicy",
            "kind": "api",
            "enabled": True,
            "class": "scrapers.remotive.JobicyScraper",
        },
        {
            "id": "gupy",
            "name": "Gupy",
            "kind": "api",
            "enabled": True,
            "class": "scrapers.gupy.GupyScraper",
            "note": "API pública, sem login. Estágios Brasil.",
        },  # ← ADICIONE
        {
            "id": "ciee_pr",
            "name": "CIEE-PR",
            "kind": "scrape",
            "enabled": False,
            "class": "scrapers.ciee_pr.CieePrScraper",
            "note": "Requer CIEE_PR_CPF e CIEE_PR_SENHA no .env",
        },
        {
            "id": "puc_car",
            "name": "PUC Carreiras",
            "kind": "scrape",
            "enabled": False,
            "class": "scrapers.puc_carreiras.PucCarreirasScraper",
            "note": "Requer PUC_CPF e PUC_SENHA no .env",
        },
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
    """Persist enabled state for builtin overrides and custom sources."""
    user = load_user_sources()

    # Built-in source settings are stored as _override records.
    override = next(
        (
            source for source in user
            if source.get("kind") == "_override" and source.get("id") == source_id
        ),
        None,
    )
    if override is not None:
        override["enabled"] = enabled
        save_user_sources(user)
        return

    # Custom API sources store their enabled flag on the source itself.
    custom = next(
        (
            source for source in user
            if source.get("kind") != "_override" and source.get("id") == source_id
        ),
        None,
    )
    if custom is not None:
        custom["enabled"] = enabled
    else:
        # No custom source exists, so this must be a built-in source.
        user.append({"id": source_id, "kind": "_override", "enabled": enabled})

    save_user_sources(user)


def add_api_source(
    name: str,
    url_template: str,
    json_path_title: str,
    json_path_company: str,
    json_path_url: str,
    json_path_location: str = "",
) -> dict:
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
