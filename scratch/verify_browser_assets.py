import re
import requests

with open("d:/7even repica 2/frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Extract script src
scripts = re.findall(r'<script\s+[^>]*src=["\']([^"\']+)["\']', html)
# Extract link href
links = re.findall(r'<link\s+[^>]*href=["\']([^"\']+)["\']', html)

base_url = "http://localhost:8000"

print("=== CHECKING FRONTEND STATIC ASSETS ===")
failed = []
checked = 0

for s in scripts:
    if s.startswith("http"):
        url = s
    else:
        url = f"{base_url}/{s.lstrip('/')}"
    try:
        r = requests.get(url, timeout=5)
        status = r.status_code
        if status == 200:
            print(f"[200 OK] Script: {s}")
        else:
            print(f"[{status} FAIL] Script: {s}")
            failed.append((s, status))
    except Exception as e:
        print(f"[ERR] Script: {s} -> {e}")
        failed.append((s, str(e)))
    checked += 1

for l in links:
    if "boxicons" in l or "fonts.googleapis" in l or "fonts.gstatic" in l:
        continue # external CDN
    if l.startswith("http"):
        url = l
    else:
        url = f"{base_url}/{l.lstrip('/')}"
    try:
        r = requests.get(url, timeout=5)
        status = r.status_code
        if status == 200:
            print(f"[200 OK] Stylesheet: {l}")
        else:
            print(f"[{status} FAIL] Stylesheet: {l}")
            failed.append((l, status))
    except Exception as e:
        print(f"[ERR] Stylesheet: {l} -> {e}")
        failed.append((l, str(e)))
    checked += 1

print(f"\nTotal assets checked: {checked}")
print(f"Total failed: {len(failed)}")
if failed:
    for f in failed:
        print(f"  FAILED: {f}")
else:
    print("[PASS] ALL FRONTEND ASSETS LOADED WITH HTTP 200 OK!")
