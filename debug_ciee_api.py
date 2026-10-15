"""
Dump completo do que a API do CIEE devolve quando você abre /vagas-estagio.
Precisamos ver a estrutura exata do endpoint 'Listar' para o scraper funcionar.
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright
from scrapers.ciee_pr import CieePrScraper, PROFILE_DIR

scraper = CieePrScraper()
captured = []

def on_response(resp):
    try:
        url = resp.url
        if "cieepr.org.br" not in url:
            return
        ct = resp.headers.get("content-type", "")
        if "json" not in ct:
            return
        body = resp.text()
        captured.append({
            "url": url,
            "method": resp.request.method,
            "status": resp.status,
            "length": len(body),
            "body_preview": body[:3000],
        })
    except Exception:
        pass

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        locale="pt-BR",
        viewport={"width": 1280, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.on("response", on_response)

    print("→ Navegando para Vagas de Estágio…")
    page.goto("https://autoweb.cieepr.org.br/Estudante/vagas-estagio",
              timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(6000)

    print("→ Rolkando para disparar carregamentos…")
    for i in range(3):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(2000)

    print("→ 10s para você olhar a tela…")
    page.wait_for_timeout(10000)
    ctx.close()

# ── Dump ────────────────────────────────────────────────────────
with open("ciee_api_dump.json", "w", encoding="utf-8") as f:
    json.dump(captured, f, indent=2, ensure_ascii=False)

print(f"\n✅ {len(captured)} respostas JSON capturadas → ciee_api_dump.json\n")
print(f"{'STATUS':<6} {'LEN':<8} URL")
print("-" * 100)
for h in captured:
    print(f"{h['status']:<6} {h['length']:<8} {h['url'][:100]}")

print("\n>>> Procure a resposta com URL contendo 'Listar'.")
print(">>> Cola o 'body_preview' dela aqui.")