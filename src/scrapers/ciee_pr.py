"""
CIEE-PR scraper — persistent-context + response interception.

Estratégia:
  1. Primeira execução: abre browser VISÍVEL, você loga manualmente UMA VEZ.
     A sessão fica salva em ~/.tiny-job-search-ai/ciee_profile/.
  2. Próximas execuções: o browser abre já logado, sem formulário.
  3. Navegamos para /vagas-estagio e INTERCEPTAMOS as respostas JSON da
     própria aplicação (mesmo truque que destravou a PUC Carreiras).

Sem adivinhar headers, sem reproduzir requests, sem JWT.
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

# Persistent profile location (não vai pro git)
PROFILE_DIR = os.path.expanduser("~/.tiny-job-search-ai/ciee_profile")


class CieePrScraper(BaseScraper):
    id, name = "ciee_pr", "CIEE-PR"

    BASE = "https://autoweb.cieepr.org.br"
    HOME_URL = f"{BASE}/Estudante/home"
    VAGAS_URL = f"{BASE}/Estudante/vagas-estagio"

    # ── Sessão persistente ────────────────────────────────────────────
    def _open_persistent(self, playwright, headless: bool):
        os.makedirs(PROFILE_DIR, exist_ok=True)
        ctx = playwright.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=headless,
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        return ctx, page

    def _ensure_logged_in(self, ctx, page) -> bool:
        """Verifica se a sessão persistente está logada. Se não, pede login manual."""
        # URL CORRETA de login do CIEE-PR
        LOGIN_PAGE = f"{self.BASE}/Autenticacao/login"

        # Vai direto para a página de login
        page.goto(LOGIN_PAGE, timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)

        url = page.url.lower()
        # Se já estiver logado, a página de login pode redirecionar para a home
        if "pre-cadastro" not in url and "login" not in url:
            print(f"[CIEE-PR] ✅ sessão já ativa ({page.url[:70]})")
            return True

        # Se estiver na tela de login, pede para o usuário logar manualmente
        print()
        print("=" * 65)
        print("⚠️  SESSÃO EXPIRADA — LOGIN MANUAL NECESSÁRIO")
        print("=" * 65)
        print("  1. Faça login normalmente na janela que abriu.")
        print("  2. Espere chegar na home do Estudante.")
        print("  3. Volte aqui e pressione ENTER para continuar.")
        print("  (Só precisa fazer isso UMA VEZ — a sessão fica salva.)")
        print("=" * 65)
        input("  → Pressione ENTER quando estiver logado: ")

        # Após o ENTER, verifica se chegou na home
        page.wait_for_timeout(2000)
        if "pre-cadastro" in page.url.lower():
            print("[CIEE-PR] ❌ ainda em pré-cadastro — login não completou")
            return False
        print(f"[CIEE-PR] ✅ login OK ({page.url[:70]})")
        return True

    # ── Search principal ──────────────────────────────────────────────
    def search(self, query: str, skills: List[str], min_period: int = 0) -> List[Dict]:
        if not PLAYWRIGHT_OK:
            print("[CIEE-PR] Playwright não instalado")
            return []

        captured_models: List[dict] = []
        seen_keys: set = set()

        def on_response(resp):
            """Intercepta QUALQUER resposta JSON que pareça vagas."""
            try:
                url = resp.url
                if "cieepr.org.br" not in url:
                    return
                ct = resp.headers.get("content-type", "")
                if "json" not in ct:
                    return
                data = resp.json()
                # Procura recursivamente por objetos que pareçam vagas
                self._walk_for_jobs(data, captured_models, seen_keys, url)
            except Exception:
                pass

        try:
            with sync_playwright() as p:
                # Primeira vez: headless=False pra permitir login manual.
                # Depois que o profile estiver salvo, pode trocar para True.
                ctx, page = self._open_persistent(p, headless=False)

                if not self._ensure_logged_in(ctx, page):
                    ctx.close()
                    return []

                page.on("response", on_response)

                print("[CIEE-PR] navegando para vagas de estágio…")
                page.goto(self.VAGAS_URL, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)

                # Rola e clica em filtros pra disparar mais chamadas
                for i in range(4):
                    page.mouse.wheel(0, 6000)
                    page.wait_for_timeout(1500)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    page.wait_for_timeout(1200)

                print(f"[CIEE-PR] interceptados {len(captured_models)} objetos de vaga")
                time.sleep(1)
                ctx.close()

        except Exception as e:
            print(f"[CIEE-PR] erro: {e}")
            return []

        if not captured_models:
            print(
                "[CIEE-PR] ⚠️ nenhuma vaga capturada — verifique se apareceu lista na tela"
            )
            return []

        # Filtra client-side por skill
        return self._filter(captured_models, query, skills, min_period)

    # ── Detecção genérica de objetos "vaga" ───────────────────────────
    def _walk_for_jobs(self, node, out: list, seen: set, url_hint: str, depth=0):
        """Percorre recursivamente o JSON procurando objetos que pareçam vagas."""
        if depth > 10:
            return
        if isinstance(node, list):
            for item in node:
                self._walk_for_jobs(item, out, seen, url_hint, depth + 1)
        elif isinstance(node, dict):
            if self._looks_like_job(node):
                key = self._job_key(node)
                if key and key not in seen:
                    seen.add(key)
                    out.append(node)
            for v in node.values():
                self._walk_for_jobs(v, out, seen, url_hint, depth + 1)

    @staticmethod
    def _looks_like_job(d: dict) -> bool:
        keys = {k.lower() for k in d.keys()}
        title_keys = {
            "titulo",
            "title",
            "nomevaga",
            "vagatitulo",
            "funcao",
            "cargo",
            "ds_titulo",
            "dsvaga",
            "nmvaga",
            "titulovaga",
        }
        other = {
            "empresa",
            "company",
            "cnpj",
            "codigo",
            "codvaga",
            "codigovaga",
            "local",
            "cidade",
            "municipio",
            "uf",
            "salario",
            "bolsa",
            "valorbolsa",
            "nmempresa",
            "dsempresa",
        }
        return bool(keys & title_keys) and bool(keys & other)

    @staticmethod
    def _job_key(d: dict) -> str:
        for k in ("codigo", "codVaga", "codigoVaga", "id", "vagaId", "jobId"):
            for dk in d.keys():
                if dk.lower() == k.lower():
                    return f"{k}:{d[dk]}"
        # fallback: título+empresa
        title = next(
            (d[k] for k in d if k.lower() in ("titulo", "nomevaga", "dsvaga")), ""
        )
        comp = next(
            (d[k] for k in d if k.lower() in ("empresa", "nmempresa", "dsempresa")), ""
        )
        return f"{title}|{comp}"

    # ── Normalização + filtro ─────────────────────────────────────────
    def _first(self, d: dict, *names):
        for n in names:
            for k in d.keys():
                if k.lower() == n.lower():
                    v = d[k]
                    if v not in (None, "", []):
                        return v
        return ""

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
        tokens = list(dict.fromkeys(t for t in tokens if len(t) > 2 and t not in stop))
        print(f"[CIEE-PR] filter tokens: {tokens}")

        only_entry = bool(min_period and min_period <= 2)

        results: List[Dict] = []
        for d in jobs:
            title = str(
                self._first(
                    d,
                    "titulo",
                    "title",
                    "nomeVaga",
                    "dsVaga",
                    "funcao",
                    "cargo",
                    "dsTitulo",
                    "nmVaga",
                )
            )
            company = str(
                self._first(
                    d, "empresa", "company", "nmEmpresa", "razaoSocial", "dsEmpresa"
                )
            )
            code = str(
                self._first(d, "codigo", "codVaga", "codigoVaga", "id", "vagaId")
            )
            city = str(self._first(d, "cidade", "municipio", "local", "cidadeVaga"))
            uf = str(self._first(d, "uf", "estado", "sgUf", "siglaUf"))
            salary = str(self._first(d, "salario", "bolsa", "valorBolsa", "valor"))
            url = str(self._first(d, "url", "link", "linkVaga"))

            if not title:
                continue
            blob = (title + " " + company).lower()
            if tokens and not any(t in blob for t in tokens):
                continue

            if only_entry:
                # Se min_period for 1-2, mantém apenas aprendiz/estágio/trainee
                low = blob
                if not any(
                    k in low for k in ("aprendiz", "estágio", "estagio", "trainee")
                ):
                    continue

            if not url and code:
                url = f"{self.BASE}/Estudante/vagas-estagio/{code}"

            loc = ", ".join(x for x in (city, uf) if x) or "Brasil"

            results.append(
                {
                    "title": title,
                    "company": company,
                    "location": loc,
                    "salary": salary,
                    "url": url,
                    "source": "CIEE-PR",
                    "tags": skills[:5],
                }
            )

        return results
