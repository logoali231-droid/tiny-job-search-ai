"""
One-shot test: logs in to PUC Carreiras via Playwright, caches cookies,
then runs a real job search using plain requests.

Run:  ./.venv/bin/python test_puc.py
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()

from scrapers.puc_carreiras import PucCarreirasScraper

scraper = PucCarreirasScraper()

print("🔐 First call — will trigger Playwright login…")
t0 = time.time()
jobs = scraper.search("estagio python", skills=["python", "sql"], min_period=2)
t1 = time.time()
print(f"⏱️  First call took {t1-t0:.1f}s, returned {len(jobs)} jobs")

for j in jobs[:5]:
    print(f"  • {j['title'][:60]:60s}  @ {j['company'][:30]}")

print("\n♻️  Second call — should reuse cached cookies (fast)…")
t0 = time.time()
jobs2 = scraper.search("estagio dados", skills=["python"], min_period=2)
t1 = time.time()
print(f"⏱️  Second call took {t1-t0:.1f}s, returned {len(jobs2)} jobs")