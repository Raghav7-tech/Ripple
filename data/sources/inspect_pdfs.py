import urllib.request
import ssl
import io
import PyPDF2

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_pdf_reader(url):
    print(f"\n--- Fetching: {url} ---")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        data = resp.read()
    print(f"Downloaded {len(data)} bytes")
    return PyPDF2.PdfReader(io.BytesIO(data))

# 1. DJB Summer Bulletin 26.07.2024
try:
    reader = get_pdf_reader("https://delhijalboard.delhi.gov.in/sites/default/files/Jalboard/universal-tab/summer_bulletin_26.07.2024_1.pdf")
    print(f"Num pages: {len(reader.pages)}")
    for i, p in enumerate(reader.pages[:3]):
        text = p.extract_text() or ""
        print(f"Page {i+1} sample (len {len(text)}):\n{text[:500]}\n")
except Exception as e:
    print("Error:", e)

# 2. DJB Summer Bulletin 05.05.2024
try:
    reader = get_pdf_reader("https://delhijalboard.delhi.gov.in/sites/default/files/Jalboard/universal-tab/summer_bulletin_05.05.2024.pdf")
    print(f"Num pages: {len(reader.pages)}")
    for i, p in enumerate(reader.pages[:3]):
        text = p.extract_text() or ""
        print(f"Page {i+1} sample (len {len(text)}):\n{text[:500]}\n")
except Exception as e:
    print("Error:", e)

# 3. MoHFW IPHS Guidelines (108.pdf)
try:
    reader = get_pdf_reader("https://clinicalestablishments.mohfw.gov.in/sites/default/files/2021-12/108.pdf")
    print(f"Num pages: {len(reader.pages)}")
    # Search for water / litres / bed / requirement
    for i, p in enumerate(reader.pages):
        text = p.extract_text() or ""
        if "water" in text.lower() and ("bed" in text.lower() or "litre" in text.lower() or "liter" in text.lower() or "lpcd" in text.lower()):
            print(f"Found water norm on Page {i+1}:\n{text[:600]}\n")
            break
except Exception as e:
    print("Error:", e)

# 4. CWC Delhi Floods 2023 Case Study
try:
    reader = get_pdf_reader("https://cwc.gov.in/sites/default/files/delhi-floods-2023-case-study.pdf")
    print(f"Num pages: {len(reader.pages)}")
    for i in range(min(5, len(reader.pages))):
        text = reader.pages[i].extract_text() or ""
        if "wazirabad" in text.lower() or "208." in text or "flood" in text.lower():
            print(f"CWC Delhi Floods Page {i+1}:\n{text[:500]}\n")
except Exception as e:
    print("Error:", e)
