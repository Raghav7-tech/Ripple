import urllib.request
import ssl
import io
import PyPDF2

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request("https://nidm.gov.in/PDF/pubs/Yamuna_2025.pdf", headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=40) as resp:
    data = resp.read()

reader = PyPDF2.PdfReader(io.BytesIO(data))
print(f"NIDM Yamuna report pages: {len(reader.pages)}")

# Search for Wazirabad, Chandrawal, Okhla, WTP, drinking water, hospital
hits = []
for pno, page in enumerate(reader.pages):
    txt = page.extract_text() or ""
    lower = txt.lower()
    if any(k in lower for k in ["wazirabad wtp", "chandrawal wtp", "water treatment plant", "submerged", "inundated", "pumping station", "djb", "jal board"]):
        for line in txt.split("\n"):
            if any(term in line.lower() for term in ["wtp", "treatment plant", "chandrawal", "wazirabad", "okhla", "water supply", "inundat", "shutdown", "closure", "pumping"]):
                print(f"P.{pno+1}: {line}")
                hits.append((pno+1, line))
            if len(hits) > 30:
                break
    if len(hits) > 30:
        break
