import os
import hashlib
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

out_dir = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "rwl_manual_hr_cwc_998_2021_2025.csv")

url = "https://nwdp.nwic.gov.in/dataset/d951a09c-6cf8-470e-be77-e80116f13d34/resource/dd3b9bba-6ba2-4954-93cf-e3ee84b5d9af/download/rwl_manual_hr_cwc_998_2021_2025.csv"

if not os.path.exists(out_file) or os.path.getsize(out_file) == 0:
    print(f"Downloading {url} to {out_file}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        content = resp.read()
    with open(out_file, "wb") as f:
        f.write(content)
    print("Download complete.")
else:
    print(f"File already exists: {out_file}")

with open(out_file, "rb") as f:
    data = f.read()
sha256 = hashlib.sha256(data).hexdigest()
size = len(data)
lines = data.count(b"\n")
print(f"Size: {size} bytes | Lines: {lines} | SHA-256: {sha256}")
