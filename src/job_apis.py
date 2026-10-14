from urllib.parse import quote_plus

import requests


class FreeJobAPIClient:
    """
    Zero-auth, keyless job API client.
    Sources: Remotive (remote) + Jobicy (remote).
    """

    def __init__(self, timeout: int = 12):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "TinyJobSearchAI/1.0 (+local educational app)"}
        )

    # ── Sources ────────────────────────────────────────────────────────────
    def search_remotive(self, query: str, limit: int = 10):
        url = "https://remotive.com/api/remote-jobs"
        try:
            r = self.session.get(
                url, params={"search": query, "limit": limit}, timeout=self.timeout
            )
            r.raise_for_status()
            jobs = r.json().get("jobs", [])
            return [
                {
                    "title": j.get("title", ""),
                    "company": j.get("company_name", ""),
                    "location": j.get("candidate_required_location", "Remote"),
                    "tags": j.get("tags", [])[:5],
                    "salary": j.get("salary", ""),
                    "url": j.get("url", ""),
                    "source": "Remotive",
                }
                for j in jobs
            ]
        except Exception as e:
            print(f"[Remotive] {e}")
            return []

    def search_jobicy(self, query: str, limit: int = 10):
        url = "https://jobicy.com/api/v2/remote-jobs"
        try:
            r = self.session.get(
                url, params={"count": limit, "tag": query}, timeout=self.timeout
            )
            r.raise_for_status()
            jobs = r.json().get("jobs", [])
            out = []
            for j in jobs:
                out.append(
                    {
                        "title": j.get("jobTitle", ""),
                        "company": j.get("companyName", ""),
                        "location": j.get("jobGeo", "Remote"),
                        "tags": j.get("jobIndustry", [])[:5] if isinstance(j.get("jobIndustry"), list) else [],
                        "salary": (
                            f"{j.get('annualSalaryMin','')}-{j.get('annualSalaryMax','')} {j.get('salaryCurrency','')}".strip("- ")
                            if j.get("annualSalaryMin") or j.get("annualSalaryMax")
                            else ""
                        ),
                        "url": j.get("url", ""),
                        "source": "Jobicy",
                    }
                )
            return out
        except Exception as e:
            print(f"[Jobicy] {e}")
            return []

    # ── Aggregate ──────────────────────────────────────────────────────────
    def search_all(self, query: str, limit_per_source: int = 10):
        results = []
        results.extend(self.search_remotive(query, limit=limit_per_source))
        results.extend(self.search_jobicy(query, limit=limit_per_source))

        # Deduplicate by URL and by (title, company)
        seen_urls, seen_pairs, unique = set(), set(), []
        for r in results:
            key_url = r.get("url", "").strip()
            key_pair = (r.get("title", "").lower(), r.get("company", "").lower())
            if key_url and key_url in seen_urls:
                continue
            if key_pair in seen_pairs:
                continue
            if key_url:
                seen_urls.add(key_url)
            seen_pairs.add(key_pair)
            unique.append(r)
        return unique