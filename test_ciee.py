import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from dotenv import load_dotenv
load_dotenv()
from scrapers.ciee_pr import CieePrScraper

s = CieePrScraper()
print("→ primeira execução: browser VISÍVEL, faça login manual…")
t0 = time.time()
jobs = s.search("estagio", skills=["python", "dados"], min_period=2)
t1 = time.time()
print(f"\n⏱️  {t1-t0:.1f}s, {len(jobs)} vagas\n")
for j in jobs[:10]:
    print(f"  • {j['title'][:60]:60s} @ {j['company'][:35]}")