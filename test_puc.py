"""
Test PUC Carreiras end-to-end:
  1. Playwright logs in (if cookies expired) → captures cookies.
  2. Scraper fetches ALL jobs from /api/v2/jobs (paginated).
  3. Filters client-side by skills.
  4. Second call reuses cached cookies (proves caching works).

Run:  ./.venv/bin/python test_puc.py
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()

from scrapers.puc_carreiras import PucCarreirasScraper

scraper = PucCarreirasScraper()

print("🔐 First call — may trigger Playwright login…")
t0 = time.time()
jobs = scraper.search("python", skills=["python", "sql"], min_period=2)
t1 = time.time()
print(f"\n⏱️  First call took {t1-t0:.1f}s, returned {len(jobs)} jobs\n")

for j in jobs[:10]:
    print(f"  • {j['title'][:60]:60s} @ {j['company'][:35]}")

print("\n♻️  Second call — should reuse cached cookies (fast)…")
t0 = time.time()
jobs2 = scraper.search("dados", skills=["python", "dados"], min_period=2)
t1 = time.time()
print(f"\n⏱️  Second call took {t1-t0:.1f}s, returned {len(jobs2)} jobs\n")

for j in jobs2[:10]:
    print(f"  • {j['title'][:60]:60s} @ {j['company'][:35]}")

print("\n✅ done")