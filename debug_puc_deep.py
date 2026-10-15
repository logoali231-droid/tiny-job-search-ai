"""
Deep probe: opens PUC logged in, calls several /api/v2/jobs variants
via page.evaluate(fetch), and dumps the RAW response text for each.
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright
from scrapers.puc_carreiras import PucCarreirasScraper

scraper = PucCarreirasScraper()

VARIANTS = [
    ("v1_exact",     "/api/v2/jobs?json_mode=read_only&enable_translation=false"),
    ("v2_perPage",   "/api/v2/jobs?json_mode=read_only&enable_translation=false&perPage=50&page=1"),
    ("v3_pageOnly",  "/api/v2/jobs?page=1"),
    ("v4_noQuery",   "/api/v2/jobs"),
    ("v5_discovery", "/api/v2/jobs/discovery?json_mode=read_only"),
    ("v6_search",    "/api/v2/search?format=long&keyword=estagio&json_mode=read_only"),
]

with sync_playwright() as p:
    session = scraper._open_session(p)
    if session is None:
        raise SystemExit("❌ no session")
    browser, _ctx, page = session

    # sanity: are we logged in?
    me = page.evaluate("""
        async () => {
            const r = await fetch('/api/v2/auth/current-user', {credentials:'include'});
            const t = await r.text();
            return {status: r.status, body: t.slice(0, 400)};
        }
    """)
    print(f"\n──── /api/v2/auth/current-user ────")
    print(f"  status={me['status']}")
    print(f"  body={me['body']}\n")

    for name, path in VARIANTS:
        print("=" * 70)
        print(f"{name}: {path}")
        print("=" * 70)
        result = page.evaluate("""
            async (path) => {
                const r = await fetch(path, {credentials:'include'});
                const text = await r.text();
                return {
                    status: r.status,
                    contentType: r.headers.get('content-type'),
                    body: text.slice(0, 1500),
                    length: text.length,
                };
            }
        """, path)

        print(f"  status      = {result['status']}")
        print(f"  content-type= {result['contentType']}")
        print(f"  body length = {result['length']}")
        print(f"  body preview:\n{result['body']}\n")

    browser.close()