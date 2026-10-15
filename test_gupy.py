"""
Test the Gupy scraper end-to-end.
Run: ./.venv/bin/python test_gupy.py
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from scrapers.gupy import GupyScraper

scraper = GupyScraper()

print("🔍 Searching Gupy for 'python' internships…")
t0 = time.time()
jobs = scraper.search("python", skills=["python", "dados"], min_period=2)
t1 = time.time()

print(f"\n⏱️  Took {t1-t0:.1f}s, returned {len(jobs)} jobs\n")
for j in jobs[:10]:
    print(f"  • {j['title'][:60]:60s} @ {j['company'][:35]}")
    print(f"    {j['location']}")