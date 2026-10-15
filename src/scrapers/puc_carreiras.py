"""
PUC Carreiras (Symplicity) scraper — response interception.

Discovery: the Angular app fires /api/v2/jobs on page load and receives
~257 jobs. Trying to reproduce that request from outside fails because
of session-scoped state we can't replicate. So we simply let the app
make its own call and grab the response as it flies by.

Flow:
  1. Playwright logs in (Playwright caches cookies to skip next time).
  2. Navigate to /students/app/jobs/discover.
  3. Listen for /api/v2/jobs responses and collect them.
  4. Filter client-side by skills + period.
"""

import os
import json
import time
from typing import List, Dict, Optional

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

    BASE = "https://pucpr-csm.symplicity.com"
    LOGIN_URL = f"{BASE}/students/app/home"
    JOBS_URL = f"{BASE}/students/app/jobs/discover"

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

    # ── Playwright: login if needed, return page ───────────────────────
    def _open_page(self, playwright):
        browser = playwright.chromium.launch(headless=True)
        ctx = browser.new_context(locale="pt-BR")

        cached = self._load_cookies()
        if cached:
            try:
                ctx.add_cookies(cached)
            except Exception:
                pass

        page = ctx.new_page()

        # Test whether cookies restore a session
        page.goto(self.JOBS_URL, timeout=40000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        probe = page.evaluate("""
            async () => {
                const r = await fetch('/api/v2/auth/current-user', {credentials:'include'});
                if (r.status !== 200) return false;
                const j = await r.json();
                return !!(j && j.login);
            }
        """)

        if not probe:
            print("[PUC] cookies stale → logging in")
            cpf = os.getenv("PUC_CPF", "").strip()
            senha = os.getenv("PUC_SENHA", "").strip()
            if not (cpf and senha):
                print("[PUC] Missing PUC_CPF / PUC_SENHA in .env")
                browser.close()
                return None

            page.goto(self.LOGIN_URL, timeout=40000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)

            for sel in (
                'input[name="username"]',
                "input#username",
                'input[name="cpf"]',
                'input[type="text"]',
                'input[autocomplete="username"]',
            ):
                try:
                    page.fill(sel, cpf, timeout=2000)
                    break
                except Exception:
                    pass
            for sel in (
                'input[type="password"]',
                'input[name="password"]',
                'input[name="senha"]',
                'input[autocomplete="current-password"]',
            ):
                try:
                    page.fill(sel, senha, timeout=2000)
                    break
                except Exception:
                    pass
            try:
                page.click(
                    'button[type="submit"], input[type="submit"], #loginButton',
                    timeout=3000,
                )
            except Exception:
                page.keyboard.press("Enter")

            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass
            page.wait_for_timeout(2500)

            self._save_cookies(ctx.cookies())
            print(f"[PUC] login OK, saved {len(ctx.cookies())} cookies")
        else:
            print("[PUC] session restored from cookies")

        return browser, ctx, page

    # ── Public search: intercept app's own /api/v2/jobs responses ─────
     # ── Public search: type in filter box, intercept server response ──
    def search(self, query: str, skills: List[str],
               min_period: int = 0) -> List[Dict]:
        if not PLAYWRIGHT_OK:
            print("[PUC] Playwright not installed")
            return []

        # Build keyword: first skill if any, else first word of query
        keyword = (skills[0] if skills else
                   (query.split()[0] if query else "estagio")).strip()
        print(f"[PUC] searching server-side for: {keyword!r}")

        captured_models: List[dict] = []
        captured_seen: set = set()
        pages_seen: set = set()

        def on_response(resp):
            try:
                url = resp.url
                # We want /api/v2/jobs (filtered OR unfiltered).
                # Skip discovery & qualified-status sub-resources.
                if "/api/v2/jobs" not in url:
                    return
                if "discovery" in url or "qualified-status" in url:
                    return
                if "filters/students" in url:
                    return
                ct = resp.headers.get("content-type", "")
                if "json" not in ct:
                    return
                if url in pages_seen:
                    return
                pages_seen.add(url)

                data = resp.json()
                models = (data or {}).get("models") or []
                total  = (data or {}).get("total", 0)
                if not models:
                    return
                print(f"[PUC] intercepted {len(models)} jobs (total={total})")
                for m in models:
                    jid = m.get("job_id") or m.get("visual_id") or m.get("id")
                    if jid and jid in captured_seen:
                        continue
                    if jid:
                        captured_seen.add(jid)
                    captured_models.append(m)
            except Exception:
                pass

        try:
            with sync_playwright() as p:
                session = self._open_page(p)
                if session is None:
                    return []
                browser, _ctx, page = session
                page.on("response", on_response)

                print("[PUC] navigating to jobs listing…")
                page.goto(self.JOBS_URL, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)

                # ── Type keyword into the filter input, click Pesquisar ──
                try:
                    page.fill("input#jobs-keyword-input", keyword, timeout=4000)
                    print(f"[PUC] filled #jobs-keyword-input with {keyword!r}")
                except Exception as e:
                    print(f"[PUC] could not fill filter input: {e}")
                    # Fallback: try Enter to submit whatever we typed
                    try:
                        page.keyboard.press("Enter")
                    except Exception:
                        pass

                # Click the Pesquisar button
                try:
                    page.click("button:has-text('Pesquisar')", timeout=4000)
                    print("[PUC] clicked 'Pesquisar'")
                except Exception as e:
                    print(f"[PUC] Pesquisar click failed, pressing Enter: {e}")
                    try:
                        page.keyboard.press("Enter")
                    except Exception:
                        pass

                # Let server respond, then optionally load more pages via "Próxima"
                page.wait_for_timeout(4500)

                # Try to load additional pages of results (up to 4 more)
                for i in range(4):
                    before = len(captured_models)
                    next_clicked = False
                    for sel in (
                        "button:has-text('Próxima')",
                        "button:has-text('Próximo')",
                        "a:has-text('Próxima')",
                        "button[aria-label='Next']",
                        "button[aria-label='Próxima página']",
                    ):
                        try:
                            page.click(sel, timeout=1200)
                            next_clicked = True
                            page.wait_for_timeout(2500)
                            break
                        except Exception:
                            continue
                    if not next_clicked:
                        break
                    if len(captured_models) == before:
                        break

                print(f"[PUC] captured {len(captured_models)} jobs from server")
                browser.close()

        except Exception as e:
            print(f"[PUC] error: {e}")
            return []

        if not captured_models:
            print("[PUC] ❌ no jobs captured")
            return []

        # The server already filtered by keyword, so `_filter` mainly
        # normalizes + applies the period gate.
        return self._filter(captured_models, query, skills, min_period)
    # ── Client-side filter + normalize ────────────────────────────────
    def _filter(
        self, jobs: List[dict], query: str, skills: List[str], min_period: int
    ) -> List[Dict]:
        tokens = []
        if query:
            tokens.extend(query.lower().split())
        tokens.extend(s.lower() for s in skills)
        stop = {
            "de",
            "da",
            "do",
            "e",
            "em",
            "para",
            "com",
            "a",
            "o",
            "os",
            "as",
            "estagio",
            "estágio",
            "vaga",
            "remoto",
            "junior",
            "senior",
            "mid",
        }
        tokens = [t for t in tokens if len(t) > 2 and t not in stop]
        print(f"[PUC] filter tokens: {tokens}")

        only_entry = bool(min_period and min_period <= 2)

        results: List[Dict] = []
        for j in jobs:
            title = (j.get("job_title") or "").lower()
            desc = (j.get("job_desc") or "").lower()
            blob = title + " " + desc

            if tokens and not any(t in blob for t in tokens):
                continue

            job_type_raw = j.get("job_type")
            if isinstance(job_type_raw, list):
                job_type = job_type_raw[0] if job_type_raw else ""
            else:
                job_type = job_type_raw or ""

            if only_entry:
                jt = str(job_type).lower()
                if not (
                    "aprendiz" in jt
                    or "estágio" in jt
                    or "estagio" in jt
                    or "trainee" in jt
                ):
                    continue

            jid = j.get("job_id") or j.get("visual_id") or ""
            url = (
                (f"{self.BASE}/students/index.php?s=jobs&ss=jobs&mode=detail&id={jid}")
                if jid
                else self.JOBS_URL
            )

            tag_list = []
            if job_type:
                tag_list.append(str(job_type))
            remote = (j.get("symp_remote_onsite") or {}).get("label")
            if remote:
                tag_list.append(str(remote))
            tag_list.extend(skills[:3])

            results.append(
                {
                    "title": j.get("job_title") or "(sem título)",
                    "company": j.get("name") or "",
                    "location": j.get("job_location") or "Brasil",
                    "salary": "",
                    "url": url,
                    "source": "PUC Carreiras",
                    "tags": tag_list[:5],
                }
            )

        return results
