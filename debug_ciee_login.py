"""
Debug CIEE-PR — login com browser visível + rastreamento completo.

Objetivo: entender (a) por que redireciona para pré-registro, e
(b) qual endpoint devolve a lista de vagas para interceptarmos.
"""
import os, sys, json, time
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
CPF   = os.getenv("CIEE_PR_CPF", "").strip()
SENHA = os.getenv("CIEE_PR_SENHA", "").strip()
if not CPF or not SENHA:
    raise SystemExit("❌ Preencha CIEE_PR_CPF e CIEE_PR_SENHA no .env")

BASE       = "https://autoweb.cieepr.org.br"
LOGIN_URL  = f"{BASE}/Estudante/home"
VAGAS_URL  = f"{BASE}/Estudante/vagas-estagio"

hits       = []          # every XHR response
navigs     = []          # every top-level navigation

def on_navigation(frame):
    if frame == frame.page.main_frame:
        navigs.append(frame.url)
        print(f"  🧭 NAV → {frame.url[:120]}")

def on_response(resp):
    try:
        url = resp.url
        if "cieepr.org.br" not in url:
            return
        ct = resp.headers.get("content-type", "")
        if "json" not in ct:
            return
        body = ""
        try: body = resp.text()[:2500]
        except Exception: pass
        hits.append({
            "url": url, "method": resp.request.method,
            "status": resp.status, "len": len(body), "body": body,
        })
    except Exception:
        pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context(locale="pt-BR")
    page = ctx.new_page()
    page.on("framenavigated", on_navigation)
    page.on("response", on_response)

    print("→ 1. Abrindo página de login…")
    page.goto(LOGIN_URL, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(3500)
    print(f"   URL atual: {page.url}")
    page.screenshot(path="ciee_01_login.png", full_page=True)

    # Preenche CPF
    for sel in ('input[name="cpf"]','input#cpf','input[formcontrolname="cpf"]',
                'input[placeholder*="CPF" i]','input[type="text"]'):
        try:
            page.fill(sel, CPF, timeout=2000)
            print(f"   ✓ CPF via {sel}")
            break
        except Exception: pass

    # Preenche senha
    for sel in ('input[type="password"]','input[name="senha"]',
                'input[formcontrolname="senha"]'):
        try:
            page.fill(sel, SENHA, timeout=2000)
            print(f"   ✓ senha via {sel}")
            break
        except Exception: pass

    # Submete
    try:
        page.get_by_role("button", name=lambda n: n and "entrar" in n.lower()).first.click(timeout=3000)
        print("   ✓ clicou 'Entrar'")
    except Exception:
        page.keyboard.press("Enter")
        print("   ✓ pressionou Enter")

    page.wait_for_timeout(6000)
    print(f"\n→ 2. Após login, URL = {page.url}")
    page.screenshot(path="ciee_02_after_login.png", full_page=True)

    # Se caiu em pré-registro, tenta navegar direto para as vagas
    if "vagas" not in page.url.lower() and "home" not in page.url.lower():
        print("   ⚠️  Parece que caiu em pré-registro. Tentando ir direto para /vagas-estagio…")
    page.goto(VAGAS_URL, timeout=40000, wait_until="domcontentloaded")
    page.wait_for_timeout(6000)
    print(f"\n→ 3. URL depois de tentar /vagas-estagio = {page.url}")
    page.screenshot(path="ciee_03_vagas.png", full_page=True)

    # Rola a página pra disparar mais XHRs (a app pode paginar)
    print("→ 4. Rolando a página para disparar carregamentos…")
    for i in range(5):
        page.mouse.wheel(0, 8000)
        page.wait_for_timeout(1500)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        page.wait_for_timeout(1000)

    print("\n→ 5. Esperando 10s para você olhar a tela…")
    page.wait_for_timeout(10000)
    browser.close()

# ── Dump ──────────────────────────────────────────────────────────────
out = {
    "navigations": navigs,
    "xhr": hits,
}
with open("ciee_debug_full.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print(f"\n✅ {len(navigs)} navegações, {len(hits)} respostas JSON")
print("📁 Arquivos gerados:")
print("   - ciee_01_login.png")
print("   - ciee_02_after_login.png")
print("   - ciee_03_vagas.png")
print("   - ciee_debug_full.json")
print("\n>>> Cola aqui a seção 'navigations' do JSON e as URLs da seção 'xhr'.\n")