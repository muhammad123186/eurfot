import os
import requests

key = os.environ.get("PITCHAPI_API_KEY", "")

for path in ("/v1/date/2025-11-09", "/v1/leagues"):
    r = requests.get(
        "https://api.pitchapi.dev" + path,
        headers={"X-API-KEY": key},
        timeout=20,
    )
    print(path)
    print("  status:", r.status_code)
    print("  body  :", r.text[:300].replace("\n", " "))