"""Find the search input on the PUC jobs page + test if typing filters jobs."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright
from scrapers.puc_carreiras import PucCarreirasScraper

scraper = PucCarreirasScraper()
captured = []

def on_response(resp):
    try:
        u = resp.url
        if "/api/v2/jobs" in u and "qualified" not in u and "discovery" not in u:
            ct = resp.headers.get("content-type", "")
            if "json" not in ct: return
            d = resp.json()
            models = d.get("models") or []
            total  = d.get("total", 0)
            captured.append({"url": u, "total": total, "n": len(models)})
            print(f"  ↳ /api/v2/jobs returned {len(models)} jobs (total={total})  url={u[:110]}")
    except Exception: pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context(locale="pt-BR")
    c = scraper._load_cookies()
    if c:
        try: ctx.add_cookies(c)
        except Exception: pass
    page = ctx.new_page()
    page.on("response", on_response)

    print("→ loading jobs page…")
    page.goto("https://pucpr-csm.symplicity.com/students/app/jobs/discover",
              timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)

    print("\n→ enumerating input elements…")
    inputs = page.evaluate("""
        () => Array.from(document.querySelectorAll('input, textarea')).map(el => ({
            tag: el.tagName,
            type: el.type || '',
            name: el.name || '',
            id: el.id || '',
            placeholder: el.placeholder || '',
            ariaLabel: el.getAttribute('aria-label') || '',
            cls: (el.className || '').toString().slice(0, 80),
            visible: el.offsetParent !== null
        }))
    """)
    for i, el in enumerate(inputs):
        print(f"  [{i}] <{el['tag']} type={el['type']!r} name={el['name']!r} "
              f"id={el['id']!r} placeholder={el['placeholder']!r} visible={el['visible']}>")

    print("\n→ enumerating button elements…")
    buttons = page.evaluate("""
        () => Array.from(document.querySelectorAll('button, [role=button]')).map(el => ({
            text: (el.textContent || '').trim().slice(0, 40),
            ariaLabel: el.getAttribute('aria-label') || '',
            cls: (el.className || '').toString().slice(0, 60),
            visible: el.offsetParent !== null
        })).filter(b => b.visible)
    """)
    for i, el in enumerate(buttons[:15]):
        print(f"  [{i}] text={el['text']!r} aria={el['ariaLabel']!r}")

    # Try typing into the most search-like input
    print("\n→ attempting to type 'python' into candidate search input…")
    candidates = [
        'input[type="search"]',
        'input[placeholder*="pesquis" i]',
        'input[placeholder*="search" i]',
        'input[placeholder*="palavra" i]',
        'input[name="keyword"]',
        'input[name="keywords"]',
        'input[formcontrolname*="keyword" i]',
        'input[formcontrolname*="search" i]',
    ]
    typed = False
    for sel in candidates:
        try:
            page.fill(sel, "python", timeout=1500)
            print(f"  ✓ filled {sel}")
            typed = True
            page.keyboard.press("Enter")
            page.wait_for_timeout(4000)
            break
        except Exception:
            continue

    if not typed:
        print("  ⚠️ no search input matched — check enumeration above")

    print("\n→ summary of /api/v2/jobs calls during test:")
    for c in captured:
        print(f"  n={c['n']:>3} total={c['total']:>4}  {c['url'][:110]}")

    print("\n→ 15s so you can look…")
    page.wait_for_timeout(15000)
    browser.close()