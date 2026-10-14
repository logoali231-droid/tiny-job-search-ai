import requests
from typing import List, Dict
from .base import BaseScraper


class RemotiveScraper(BaseScraper):
    id, name = "remotive", "Remotive"

    def search(self, query, skills, min_period=0):
        try:
            r = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": query, "limit": 10}, timeout=12,
                headers={"User-Agent": "TinyJobSearchAI/1.0"},
            )
            r.raise_for_status()
            return [{
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location", "Remote"),
                "salary": j.get("salary", ""),
                "url": j.get("url", ""),
                "source": "Remotive",
                "tags": j.get("tags", [])[:5],
            } for j in r.json().get("jobs", [])]
        except Exception as e:
            print(f"[Remotive] {e}")
            return []


class JobicyScraper(BaseScraper):
    id, name = "jobicy", "Jobicy"

    def search(self, query, skills, min_period=0):
        try:
            r = requests.get(
                "https://jobicy.com/api/v2/remote-jobs",
                params={"count": 10, "tag": query}, timeout=12,
                headers={"User-Agent": "TinyJobSearchAI/1.0"},
            )
            r.raise_for_status()
            out = []
            for j in r.json().get("jobs", []):
                out.append({
                    "title": j.get("jobTitle", ""),
                    "company": j.get("companyName", ""),
                    "location": j.get("jobGeo", "Remote"),
                    "salary": "",
                    "url": j.get("url", ""),
                    "source": "Jobicy",
                    "tags": j.get("jobIndustry", [])[:5] if isinstance(j.get("jobIndustry"), list) else [],
                })
            return out
        except Exception as e:
            print(f"[Jobicy] {e}")
            return []