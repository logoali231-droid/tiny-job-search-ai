"""
Diagnose /api/v2/jobs: compare several request variants and print
cookies + response shapes side-by-side.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()
from scrapers.puc_carreiras import PucCarreirasScraper

scraper = PucCarreirasScraper()
sess = scraper._get_session()
if sess is None:
    raise SystemExit("❌ no session")

print("\n──── Cookies in session ────")
for c in sess.cookies:
    print(f"  {c.name:30s}  domain={c.domain:35s}  path={c.path}")
print()

BASE = scraper.BASE
URL  = f"{BASE}/api/v2/jobs"

variants = [
    {
        "name": "A: exact browser URL (no perPage/page)",
        "params": {"json_mode": "read_only", "enable_translation": "false"},
        "headers": {},
    },
    {
        "name": "B: with perPage + page",
        "params": {"json_mode": "read_only", "enable_translation": "false",
                   "perPage": 20, "page": 1},
        "headers": {},
    },
    {
        "name": "C: without X-Requested-With",
        "params": {"json_mode": "read_only", "enable_translation": "false"},
        "headers": {"X-Requested-With": None},   # None = remove
    },
]

for v in variants:
    print("=" * 60)
    print(v["name"])
    print("=" * 60)

    # build a fresh session with modified headers
    s = scraper._session_with_cookies(list(sess.cookies))
    for h, val in v["headers"].items():
        if val is None:
            s.headers.pop(h, None)
        else:
            s.headers[h] = val

    try:
        r = s.get(URL, params=v["params"], timeout=20, allow_redirects=True)
        print(f"HTTP {r.status_code}")
        print(f"Final URL: {r.url}")
        print(f"History redirects: {[h.status_code for h in r.history]}")
        body = r.text[:800]
        print(f"Body (first 800 chars):\n{body}\n")

        # try to parse
        try:
            d = r.json()
            print(f"Top keys: {list(d.keys())}")
            print(f"total: {d.get('total')}")
            print(f"models count: {len(d.get('models') or [])}")
            if d.get("models"):
                print(f"First model keys: {list(d['models'][0].keys())[:10]}")
                print("✅ THIS VARIANT WORKS\n")
                break
        except Exception as e:
            print(f"not JSON: {e}")
    except Exception as e:
        print(f"❌ request error: {e}")
    print()