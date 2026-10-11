import urllib.request
import ssl
import io
import PyPDF2

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_pdf_reader(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        data = resp.read()
    return PyPDF2.PdfReader(io.BytesIO(data))

# CWC Delhi Floods 2023
reader = get_pdf_reader("https://cwc.gov.in/sites/default/files/delhi-floods-2023-case-study.pdf")
print("=== CWC DELHI FLOODS 2023 CASE STUDY (Pages 6-12) ===")
for pno in range(5, 14):
    text = reader.pages[pno].extract_text() or ""
    print(f"\n--- PAGE {pno+1} ---")
    for line in text.split("\n"):
        if any(w in line.lower() for w in ["wazirabad", "chandrawal", "railway", "208.", "205.", "207.", "peak", "hathnikund", "warning", "danger", "highest", "intake"]):
            print("  ", line)

# MoHFW IPHS hospital guidelines water requirements
print("\n=== MoHFW IPHS WATER NORMS SEARCH ===")
iphs_reader = get_pdf_reader("https://clinicalestablishments.mohfw.gov.in/sites/default/files/2021-12/108.pdf")
for pno, p in enumerate(iphs_reader.pages):
    txt = p.extract_text() or ""
    if "litres per bed" in txt.lower() or "liters per bed" in txt.lower() or "lpcd" in txt.lower() or "water supply" in txt.lower() and "bed" in txt.lower():
        for line in txt.split("\n"):
            if any(term in line.lower() for term in ["litre", "liter", "gallon", "lpcd", "per bed", "storage"]):
                print(f"P.{pno+1}: {line}")
