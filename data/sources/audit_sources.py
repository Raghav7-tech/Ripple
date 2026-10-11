import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(u):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='replace')

print("=== DJB PRODUCTION REPORT PAGE ===")
try:
    prod_html = fetch("https://delhijalboard.delhi.gov.in/daily-water-production-report")
    links = re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', prod_html, re.I | re.DOTALL)
    pdf_links = [l for l in links if ".pdf" in l[0].lower()]
    print("Total pdf links on production page:", len(pdf_links))
    for url, title in pdf_links[:10]:
        clean_txt = " ".join(re.sub(r"<[^>]+>", " ", title).split())
        print(f"PDF: {url} | Title: {clean_txt}")
except Exception as e:
    print("Error fetching prod page:", e)

print("\n=== DJB PRESS RELEASES ===")
try:
    press_html = fetch("https://delhijalboard.delhi.gov.in/jalboard/press-release")
    plinks = re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', press_html, re.I | re.DOTALL)
    ppdfs = [l for l in plinks if ".pdf" in l[0].lower()]
    print("Total press release pdf links:", len(ppdfs))
    for url, title in ppdfs[:10]:
        clean_txt = " ".join(re.sub(r"<[^>]+>", " ", title).split())
        print(f"PR PDF: {url} | Title: {clean_txt}")
except Exception as e:
    print("Error fetching press page:", e)
