"""Minimal post-deployment smoke test. Usage: python scripts/smoke_test.py http://127.0.0.1:8000"""
import json
import sys
import urllib.request

base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")

checks = [
    ("health", f"{base}/core/healthz/"),
    ("login", f"{base}/login/"),
]

for name, url in checks:
    with urllib.request.urlopen(url, timeout=10) as response:
        body = response.read().decode("utf-8", errors="replace")
        if response.status != 200:
            raise SystemExit(f"{name} failed: HTTP {response.status}")
        if name == "health":
            payload = json.loads(body)
            if not payload.get("ok"):
                raise SystemExit(f"health failed: {payload}")
    print(f"PASS {name}: {url}")

print("Smoke test passed.")
