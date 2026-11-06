import os
import requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("PITCHAPI_API_KEY")

print("Prefix:", key[:8] if key else "MISSING")
print("Length:", len(key) if key else 0)

r = requests.get(
    "https://api.pitchapi.dev/v1/leagues",
    headers={"X-API-KEY": key},
    timeout=20
)

print("Status:", r.status_code)
print("Response:", r.text[:1000])