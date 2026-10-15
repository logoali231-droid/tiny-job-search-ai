"""
Gupy scraper — public zero-auth REST API.

Endpoint: https://portal.gupy.io/api/job-search/jobs
Docs (informal): Response shape { data: [...], pagination: { total, offset, limit } }
Auth: none required (zero-auth)
Filters: jobName (keyword), type (vacancy_type_internship for internships),
         workplaceType, state, offset, limit (max 100).

For internships we pass type=vacancy_type_internship server-side.
The feed is ordered publishedDate-descending and a short page is the only
end-of-feed signal (pagination.total reports page size, not result count).
"""
import time
from typing import List, Dict

import requests

from .base import BaseScraper

# API config
API_BASE = "https://portal.gupy.io/api/job-search/jobs"
PER_PAGE = 100          # server-side maximum
DEFAULT_MAX_PAGES = 5   # × 100 = 500 jobs per keyword
MAX_PAGES_CAP = 100     # API serves no offset >= 10000
INTER_REQUEST_DELAY = 0.2   # seconds between requests
CONFIDENTIAL_EMPLOYER = {"confidencial", "empresa confidencial"}


class GupyScraper(BaseScraper):
    id, name = "gupy", "Gupy"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"),
            "Accept": "application/json",
        })

    # ── Public search ─────────────────────────────────────────────────
    def search(self, query: str, skills: List[str],
               min_period: int = 0) -> List[Dict]:
        # Build keyword list: query tokens + first few skills
        keywords = []
        if query:
            keywords.extend(query.split())
        keywords.extend(skills[:3])
        # dedupe + strip
        seen_kw = set()
        keywords = [k for k in keywords
                    if k.lower() not in seen_kw and not seen_kw.add(k.lower())]
        if not keywords:
            keywords = ["estagio"]

        all_jobs: List[dict] = []
        seen_urls: set = set()

        for keyword in keywords[:3]:   # cap at 3 keywords
            jobs = self._sweep_keyword(keyword)
            for j in jobs:
                if j["url"] in seen_urls:
                    continue
                seen_urls.add(j["url"])
                all_jobs.append(j)
            time.sleep(INTER_REQUEST_DELAY)

        print(f"[Gupy] fetched {len(all_jobs)} unique internship jobs")
        return all_jobs

    # ── One keyword sweep (paginated) ─────────────────────────────────
    def _sweep_keyword(self, keyword: str) -> List[Dict]:
        jobs: List[dict] = []
        for page in range(DEFAULT_MAX_PAGES):
            params = {
                "jobName": keyword,
                "offset": page * PER_PAGE,
                "limit": PER_PAGE,
                "type": "vacancy_type_internship",   # server-side filter
            }
            try:
                r = self.session.get(API_BASE, params=params, timeout=20)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"[Gupy] {keyword!r} page {page} failed: {e}")
                break

            rows = data.get("data") or []
            if not rows:
                break

            for raw in rows:
                j = self._normalize(raw)
                if j:
                    jobs.append(j)

            print(f"[Gupy] {keyword!r} page {page}: {len(rows)} rows")

            # Short page = end of feed
            if len(rows) < PER_PAGE:
                break
            # API ceiling
            if page + 1 >= MAX_PAGES_CAP:
                break
            time.sleep(INTER_REQUEST_DELAY)

        return jobs

    # ── Normalize one raw posting ─────────────────────────────────────
    def _normalize(self, raw: dict) -> dict | None:
        if not isinstance(raw, dict):
            return None

        title = (raw.get("name") or "").strip()
        if not title:
            return None

        url = (raw.get("jobUrl") or "").strip()
        if not url.startswith("https://"):
            return None

        company = (raw.get("careerPageName") or "").strip()
        if not company or company.lower() in CONFIDENTIAL_EMPLOYER:
            return None

        # Build location: workplaceType + city/state/country
        parts = []
        wt = (raw.get("workplaceType") or "").strip()
        if wt:
            parts.append({
                "remote": "Remoto",
                "hybrid": "Híbrido",
                "on-site": "Presencial",
            }.get(wt, wt))
        elif raw.get("isRemoteWork") is True:
            parts.append("Remoto")
        for field in ("city", "state", "country"):
            v = raw.get(field)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
        location = ", ".join(parts) or "Brasil"

        # Tags: type + workplace + skills (will be added by caller)
        tags = []
        raw_type = raw.get("type") or ""
        if raw_type:
            label = raw_type.replace("vacancy_type_", "").replace("_", " ").title()
            tags.append(label)

        return {
            "title": title,
            "company": company,
            "location": location,
            "salary": "",
            "url": url,
            "source": "Gupy",
            "tags": tags,
        }