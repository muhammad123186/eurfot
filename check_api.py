import os, requests
from datetime import datetime, timezone

KEY = 'bb8a30c3bfe6ea8d30849cbf9ea8cb8f' # أو os.environ["API_SPORTS_KEY"]
H = {"x-apisports-key": KEY}
BASE = "https://v3.football.api-sports.io"

# 1) الترتيب مباشرة من API بدون كاش
r = requests.get(f"{BASE}/standings", headers=H,
                 params={"league": 39, "season": 2026}, timeout=15)
rows = r.json()["response"][0]["league"]["standings"][0]
now = datetime.now(timezone.utc)

print("الآن (UTC):", now.strftime("%H:%M:%S"))
for row in rows[:6]:
    print(row["rank"], row["team"]["name"], "pts", row["points"],
          "played", row["all"]["played"], "| update:", row["update"])

# 2) المباريات المنتهية اليوم مباشرة من API
today = now.strftime("%Y-%m-%d")
f = requests.get(f"{BASE}/fixtures", headers=H,
                 params={"league": 39, "season": 2026, "date": today}, timeout=15)
for m in f.json()["response"]:
    s = m["fixture"]["status"]
    print(m["teams"]["home"]["name"], m["goals"]["home"], "-",
          m["goals"]["away"], m["teams"]["away"]["name"], "|", s["short"], s["elapsed"])