"""
PUC Carreiras (Symplicity) scraper — cookie-session approach.

  1. Playwright logs in once with PUC_CPF / PUC_SENHA.
  2. We capture the browser cookies.
  3. Cookies are cached (data/puc_session.json) and reused with `requests`.
  4. On 401/403 we transparently re-login.

Search API (verified from live traffic):
    GET /api/v2/search?format=long&keyword=<query>&json_mode=read_only
Returns up to ~180+ jobs per call in clean JSON.
"""
import os
import json
import time
from typing import List, Dict, Optional

import requests

from .base import BaseScraper

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

from config import DATA_DIR

SESSION_PATH = os.path.join(DATA_DIR, "puc_session.json")


class PucCarreirasScraper(BaseScraper):
    id, name = "puc_car", "PUC Carreiras"

    BASE       = "https://pucpr-csm.symplicity.com"
    LOGIN_URL  = f"{BASE}/students/app/home"
    JOBS_URL   = f"{BASE}/students/app/jobs/discover"
    SEARCH_API = f"{BASE}/api/v2/search"

    # ── Cookie cache ───────────────────────────────────────────────────
    def _load_cookies(self) -> Optional[list]:
        if not os.path.exists(SESSION_PATH):
            return None
        try:
            with open(SESSION_PATH) as f:
                d = json.load(f)
            if d.get("expires_at", 0) > time.time() + 60:
                return d.get("cookies")
        except Exception:
            pass
        return None

    def _save_cookies(self, cookies: list, ttl: int = 6 * 3600):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(SESSION_PATH, "w") as f:
                json.dump({"cookies": cookies, "expires_at": time.time() + ttl}, f)
            os.chmod(SESSION_PATH, 0o600)
        except Exception as e:
            print(f"[PUC] cookie save failed: {e}")

    # ── Playwright login ───────────────────────────────────────────────
    def _playwright_login(self) -> Optional[list]:
        cpf   = os.getenv("PUC_CPF", "").strip()
        senha = os.getenv("PUC_SENHA", "").strip()
        if not (cpf and senha):
            print("[PUC] Missing PUC_CPF / PUC_SENHA in .env")
            return None
        if not PLAYWRIGHT_OK:
            print("[PUC] Playwright not installed")
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx = browser.new_context(locale="pt-BR")
                page = ctx.new_page()

                page.goto(self.LOGIN_URL, timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)

                for sel in ('input[name="username"]', 'input#username',
                            'input[name="cpf"]', 'input[type="text"]',
                            'input[autocomplete="username"]'):
                    try:
                        page.fill(sel, cpf, timeout=2000); break
                    except Exception: pass

                for sel in ('input[type="password"]', 'input[name="password"]',
                            'input[name="senha"]', 'input[autocomplete="current-password"]'):
                    try:
                        page.fill(sel, senha, timeout=2000); break
                    except Exception: pass

                try:
                    page.click('button[type="submit"], input[type="submit"], #loginButton', timeout=3000)
                except Exception:
                    page.keyboard.press("Enter")

                try:
                    page.wait_for_load_state("networkidle", timeout=30000)
                except Exception:
                    pass
                page.wait_for_timeout(2500)

                # Confirm we actually got in
                page.goto(self.JOBS_URL, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)

                cookies = ctx.cookies()
                browser.close()

                if not cookies:
                    print("[PUC] No cookies captured — login may have failed")
                    return None

                print(f"[PUC] login OK, captured {len(cookies)} cookies")
                return cookies

        except Exception as e:
            print(f"[PUC] login error: {e}")
            return None

    # ── Session helper ─────────────────────────────────────────────────
    def _session_with_cookies(self, cookies: list) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": self.JOBS_URL,
            "X-Requested-With": "XMLHttpRequest",
        })
        for c in cookies:
            try:
                s.cookies.set(
                    c["name"], c["value"],
                    domain=c.get("domain", ".symplicity.com"),
                    path=c.get("path", "/"),
                )
            except Exception:
                pass
        return s

    def _get_session(self) -> Optional[requests.Session]:
        cookies = self._load_cookies() or self._playwright_login()
        if not cookies:
            return None
        if not self._load_cookies():
            self._save_cookies(cookies)
        return self._session_with_cookies(cookies)

    # ── Public search ──────────────────────────────────────────────────
    def search(self, query: str, skills: List[str],
               min_period: int = 0) -> List[Dict]:
        sess = self._get_session()
        if sess is None:
            return []

        params = {"format": "long", "keyword": query, "json_mode": "read_only"}
        try:
            r = sess.get(self.SEARCH_API, params=params, timeout=20)

            # Stale session → re-login once and retry
            if r.status_code in (401, 403) or r.history and any(h.status_code in (301,302) for h in r.history):
                print(f"[PUC] session rejected ({r.status_code}) — re-login")
                cookies = self._playwright_login()
                if not cookies:
                    return []
                self._save_cookies(cookies)
                sess = self._session_with_cookies(cookies)
                r = sess.get(self.SEARCH_API, params=params, timeout=20)

            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[PUC] request failed: {e}")
            return []

        return self._parse(data, skills, min_period)

    # ── Parsing ────────────────────────────────────────────────────────
    def _parse(self, data: dict, skills: List[str], min_period: int) -> List[Dict]:
        jobs: List[Dict] = []
        types = data.get("types", {}) or {}
        job_block = types.get("Job", {}) or {}
        models = job_block.get("models", []) or []

        for m in models:
            jid = m.get("id") or ""
            title = m.get("label") or "(sem título)"
            meta = m.get("meta") or {}

            employer = (meta.get("employer") or {}).get("field") or ""
            location = (meta.get("location") or {}).get("field") or ""
            jtype_block = (meta.get("job_type") or {}).get("field") or []
            type_labels = [
                t.get("_label", "") for t in jtype_block if isinstance(t, dict)
            ]

            url = (f"{self.BASE}/students/index.php"
                   f"?s=jobs&ss=jobs&mode=detail&id={jid}") if jid else self.JOBS_URL

            jobs.append({
                "title":    title,
                "company":  employer,
                "location": location or "Brasil",
                "salary":   "",
                "url":      url,
                "source":   "PUC Carreiras",
                "tags":     (type_labels + skills)[:5],
            })

        return jobs