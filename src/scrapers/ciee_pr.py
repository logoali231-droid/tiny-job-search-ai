"""
CIEE-PR scraper using Playwright + XHR interception.
Angular SPA → the JSON behind the UI is far more stable than the DOM.

Credentials from .env:
    CIEE_PR_CPF=...
    CIEE_PR_SENHA=...
"""
import os
import json
import time
from typing import List, Dict

from .base import BaseScraper

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False


class CieePrScraper(BaseScraper):
    id, name = "ciee_pr", "CIEE-PR"

    BASE = "https://autoweb.cieepr.org.br"
    LOGIN_URL = f"{BASE}/Estudante/home"
    VAGAS_ESTAGIO_URL = f"{BASE}/Estudante/vagas-estagio"   # adjust if needed

    def search(self, query: str, skills: List[str], min_period: int = 0) -> List[Dict]:
        if not PLAYWRIGHT_OK:
            print("[CIEE-PR] Playwright not installed.")
            return []

        cpf = os.getenv("CIEE_PR_CPF", "").strip()
        senha = os.getenv("CIEE_PR_SENHA", "").strip()
        if not cpf or not senha:
            print("[CIEE-PR] Missing CIEE_PR_CPF / CIEE_PR_SENHA in .env")
            return []

        captured: List[dict] = []   # will collect every JSON payload we see

        def on_response(response):
            """Playwright fires this for every network response."""
            try:
                url = response.url.lower()
                ctype = response.headers.get("content-type", "")
                # Only care about JSON APIs related to vagas
                if "json" not in ctype and "application/json" not in ctype:
                    return
                if not any(k in url for k in ("vaga", "estagio", "candidat", "oportunidade", "api")):
                    return
                payload = response.json()
                captured.append({"url": response.url, "json": payload})
                print(f"[CIEE-PR] captured JSON from {response.url}")
            except Exception:
                pass

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(locale="pt-BR")
                page = context.new_page()
                page.on("response", on_response)

                # 1. Login (Angular form — wait for inputs to appear)
                page.goto(self.LOGIN_URL, timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)  # let Angular boot

                # Try several common input selectors
                for sel in [
                    'input[name="cpf"]', 'input#cpf', 'input[formcontrolname="cpf"]',
                    'input[placeholder*="CPF" i]', 'input[type="text"]'
                ]:
                    try:
                        page.fill(sel, cpf, timeout=2000)
                        print(f"[CIEE-PR] filled CPF via {sel}")
                        break
                    except Exception:
                        continue

                for sel in [
                    'input[type="password"]', 'input[name="senha"]',
                    'input[formcontrolname="senha"]'
                ]:
                    try:
                        page.fill(sel, senha, timeout=2000)
                        print(f"[CIEE-PR] filled password via {sel}")
                        break
                    except Exception:
                        continue

                # Click any button whose text looks like "Entrar"
                try:
                    page.get_by_role("button", name=lambda n: n and "entrar" in n.lower()).first.click(timeout=3000)
                except Exception:
                    page.keyboard.press("Enter")

                page.wait_for_load_state("networkidle", timeout=30000)
                page.wait_for_timeout(2000)

                # 2. Navigate to the Vagas de Estágio listing
                page.goto(self.VAGAS_ESTAGIO_URL, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle", timeout=30000)
                page.wait_for_timeout(2000)

                # 3. If there's a search box, use it. Otherwise just page through.
                for sel in [
                    'input[type="search"]',
                    'input[placeholder*="pesquis" i]',
                    'input[placeholder*="vaga" i]',
                ]:
                    try:
                        page.fill(sel, query, timeout=2000)
                        page.keyboard.press("Enter")
                        page.wait_for_load_state("networkidle", timeout=15000)
                        page.wait_for_timeout(1500)
                        print(f"[CIEE-PR] searched via {sel}")
                        break
                    except Exception:
                        continue

                browser.close()

        except Exception as e:
            print(f"[CIEE-PR] {e}")
            return []

        # 4. Parse whatever we captured
        jobs = self._extract_jobs_from_captured(captured, skills)
        print(f"[CIEE-PR] extracted {len(jobs)} jobs from {len(captured)} JSON responses")
        return jobs

    # ── JSON extraction: try several likely shapes ────────────────────────
    def _extract_jobs_from_captured(self, captured, skills):
        jobs: List[Dict] = []

        def walk(node, depth=0):
            """Recursively look for arrays of objects that look like job listings."""
            if depth > 8:
                return
            if isinstance(node, list):
                for item in node:
                    if isinstance(item, dict) and self._looks_like_job(item):
                        jobs.append(self._to_job(item, skills))
                    else:
                        walk(item, depth + 1)
            elif isinstance(node, dict):
                for v in node.values():
                    walk(v, depth + 1)

        for entry in captured:
            walk(entry["json"])

        # Dedup by url/codigo
        seen, uniq = set(), []
        for j in jobs:
            k = j.get("url") or j.get("title") + "|" + j.get("company", "")
            if k in seen:
                continue
            seen.add(k)
            uniq.append(j)
        return uniq

    @staticmethod
    def _looks_like_job(d: dict) -> bool:
        keys = {k.lower() for k in d.keys()}
        # Any dict that has a title-ish key AND a company/code/location key
        title_keys = {"titulo", "title", "nomevaga", "vagatitulo", "ds_titulo", "funcao", "cargo"}
        other_keys = {"empresa", "company", "razaoSocial", "cnpj", "codigo", "codvaga",
                      "local", "cidade", "municipio", "uf", "salario", "bolsa"}
        return bool(keys & title_keys) and bool(keys & other_keys)

    @staticmethod
    def _first(d: dict, *names):
        for n in names:
            for k in d.keys():
                if k.lower() == n.lower():
                    v = d[k]
                    if v not in (None, "", []):
                        return v
        return ""

    def _to_job(self, d, skills):
        title = self._first(d, "titulo", "title", "nomeVaga", "funcao", "cargo", "ds_titulo")
        company = self._first(d, "empresa", "company", "razaoSocial", "nomeEmpresa")
        code = self._first(d, "codigo", "codVaga", "codigoVaga", "id")
        city = self._first(d, "cidade", "municipio", "local", "cidadeVaga")
        uf = self._first(d, "uf", "estado", "siglaUf")
        salary = self._first(d, "salario", "bolsa", "valorBolsa", "valor")
        url = self._first(d, "url", "link", "linkVaga")

        location = ", ".join(str(x) for x in (city, uf) if x)
        if not url and code:
            url = f"{self.BASE}/Estudante/vagas-estagio/{code}"

        return {
            "title": str(title),
            "company": str(company),
            "location": location or "Brasil",
            "salary": str(salary),
            "url": str(url),
            "source": "CIEE-PR",
            "tags": skills[:5],
        }