import urllib.request
import ssl
import io
import PyPDF2

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request("https://nidm.gov.in/PDF/pubs/Yamuna_2025.pdf", headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=40) as resp:
    reader = PyPDF2.PdfReader(io.BytesIO(resp.read()))

for pno in range(70, 95):
    txt = reader.pages[pno].extract_text() or ""
    lower = txt.lower()
    if any(w in lower for w in ['hospital', 'trauma', 'sushruta', 'evacuat']):
        print(f"=== Page {pno+1} ===")
        for line in txt.split("\n"):
            if any(w in line.lower() for w in ['hospital', 'trauma', 'sushruta', 'evacuat', 'water supply', 'relief']):
                print("  ", line)
