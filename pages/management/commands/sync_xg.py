import time
from datetime import datetime, timedelta

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone

from pages import views as v
from pages.models import MatchXG

BASE = "https://v3.football.api-sports.io"
DONE = ("FT", "AET", "PEN")
CODES = ["PL", "PD", "SA", "BL1", "FL1"]
PAUSE = 0.4                 # ثوانٍ بين الطلبات (حماية من حد الطلبات بالدقيقة)
MAX_FAILS_IN_ROW = 3        # بعدها نتوقف (غالبًا انتهت الحصة)


class ApiFailure(Exception):
    pass


def api(path, **params):
    """يرجع قائمة النتائج، أو يرفع ApiFailure عند أي فشل.
    هكذا لا نحفظ الفشل على أنه 'لا يوجد xG'."""
    try:
        r = v.safe_api_get(f"{BASE}/{path}", headers=v.headers, params=params, timeout=20)
    except Exception as e:
        raise ApiFailure(f"{path}: {e!r}")

    try:
        j = r.json()
    except ValueError:
        raise ApiFailure(f"{path}: invalid JSON (HTTP {r.status_code})")

    if j.get("errors"):
        raise ApiFailure(f"{path}: {j['errors']}")

    if r.status_code != 200:
        raise ApiFailure(f"{path}: HTTP {r.status_code}")

    data = j.get("response", [])
    return data if isinstance(data, list) else []


def parse_xg(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class Command(BaseCommand):
    help = "Store expected goals (xG) for finished matches"

    def add_arguments(self, parser):
        parser.add_argument("--league", help="PL / PD / SA / BL1 / FL1 (default: all)")
        parser.add_argument("--limit", type=int, default=60,
                            help="max statistics requests per league in one run")
        parser.add_argument("--force", action="store_true",
                            help="re-check old matches that had no xG")

    def handle(self, *args, **opts):
        codes = [opts["league"]] if opts["league"] else CODES
        recent = timezone.now() - timedelta(days=3)

        for code in codes:
            if code not in v.LEAGUES:
                self.stderr.write(f"{code}: unknown league")
                continue

            try:
                fixtures = api("fixtures", league=v.LEAGUES[code]["id"], season=v.SEASON)
            except ApiFailure as e:
                self.stderr.write(f"{code}: fixtures request FAILED -> {e}")
                self.stderr.write("Stopping: probably daily quota or rate limit.")
                return

            finished = [f for f in fixtures if f["fixture"]["status"]["short"] in DONE]
            known = {
                x.fixture_id: x
                for x in MatchXG.objects.filter(league_code=code, season=v.SEASON)
            }

            budget = opts["limit"]
            checked = with_xg = no_xg = failed = in_row = 0
            abort = False

            for f in finished:
                if budget <= 0:
                    break

                fid = f["fixture"]["id"]
                played = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00"))
                old = known.get(fid)

                # تخطَّ ما جلبنا xG له، أو ما مرّت عليه أيام بلا xG (إلا مع --force)
                if old and (old.home_xg is not None or (played < recent and not opts["force"])):
                    continue

                try:
                    team_stats = api("fixtures/statistics", fixture=fid)
                except ApiFailure as e:
                    failed += 1
                    in_row += 1
                    self.stderr.write(f"  fixture {fid}: FAILED -> {e}")
                    if in_row >= MAX_FAILS_IN_ROW:
                        abort = True
                        break
                    continue

                in_row = 0
                budget -= 1
                time.sleep(PAUSE)

                by = {}
                for t in team_stats:
                    for s in t.get("statistics", []):
                        if s.get("type") == "expected_goals":
                            by[t["team"]["id"]] = parse_xg(s.get("value"))

                hid, aid = f["teams"]["home"]["id"], f["teams"]["away"]["id"]
                home_xg, away_xg = by.get(hid), by.get(aid)

                MatchXG.objects.update_or_create(
                    fixture_id=fid,
                    defaults={
                        "league_code": code,
                        "season": v.SEASON,
                        "played_at": played,
                        "home_id": hid,
                        "away_id": aid,
                        "home_xg": home_xg,
                        "away_xg": away_xg,
                    },
                )

                checked += 1
                if home_xg is not None and away_xg is not None:
                    with_xg += 1
                else:
                    no_xg += 1

            cache.delete(f"xg_table_v2_{code}_{v.SEASON}")

            self.stdout.write(
                f"{code}: finished={len(finished)} checked={checked} "
                f"with_xG={with_xg} no_xG={no_xg} failed={failed}"
            )

            if checked and not with_xg:
                self.stdout.write(self.style.WARNING(
                    f"{code}: the API returned NO xG for any checked match. "
                    f"This league/season/plan may not provide xG."
                ))

            if abort:
                self.stderr.write("Stopped early: repeated API failures (quota / rate limit?).")
                return