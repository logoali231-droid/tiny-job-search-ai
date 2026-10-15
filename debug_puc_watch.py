"""
Opens PUC, navigates to the JOBS listing page, and logs EVERY /api/v2/
call the app makes — URLs, params, status, and the 'total' field from
each JSON response. This tells us exactly what endpoint returns jobs.
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright
from scrapers.puc_carreiras import PucCarreirasScraper

scraper = PucCarreirasScraper()

hits = []

def on_response(resp):
    try:
        url = resp.url
        if "/api/v2/" not in url and "/api/v3/" not in url:
            return
        ct = resp.headers.get("content-type", "")
        if "json" not in ct:
            return
        body = resp.text()
        total = None
        try:
            d = json.loads(body)
            if isinstance(d, dict):
                total = d.get("total")
                # jobs/discovery returns {'models': {'jobs': [...]}}
                if total is None and "models" in d and isinstance(d["models"], dict):
                    jobs_field = d["models"].get("jobs")
                    if isinstance(jobs_field, list):
                        total = len(jobs_field)
        except Exception:
            pass
        hits.append({
            "method": resp.request.method,
            "url": url,
            "status": resp.status,
            "len": len(body),
            "total": total,
        })
    except Exception:
        pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)   # visible
    ctx = browser.new_context(locale="pt-BR")
    cached = scraper._load_cookies()
    if cached:
        try: ctx.add_cookies(cached)
        except Exception: pass

    page = ctx.new_page()
    page.on("response", on_response)

    print("→ 1/3 opening /students/app/home …")
    page.goto("https://pucpr-csm.symplicity.com/students/app/home",
              timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    print("→ 2/3 navigating to /students/app/jobs/discover …")
    page.goto("https://pucpr-csm.symplicity.com/students/app/jobs/discover",
              timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(6000)

    print("→ 3/3 clicking on a job card if present (to trigger detail calls)…")
    try:
        # try clicking the first job card
        for sel in ("text=Estágio", "a[href*='detail']", ".job-listing a"):
            try:
                page.click(sel, timeout=2000)
                page.wait_for_timeout(3500)
                break
            except Exception:
                continue
    except Exception:
        pass

    print("\n→ Waiting 10s so you can look at the page…")
    page.wait_for_timeout(10000)
    browser.close()

print(f"\n===== captured {len(hits)} API responses =====\n")
print(f"{'METHOD':<6} {'STATUS':<6} {'TOTAL':<6} {'LEN':<8} URL")
print("-" * 120)
for h in hits:
    t = "" if h["total"] is None else str(h["total"])
    print(f"{h['method']:<6} {h['status']:<6} {t:<6} {h['len']:<8} {h['url'][:100]}")

print("\n>>> Look for the line with a POSITIVE total and /api/v2/jobs or /api/v2/search.")
print(">>> That's the URL we need to reproduce.")