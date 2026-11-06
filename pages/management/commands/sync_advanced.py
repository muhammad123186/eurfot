
import re
import time
import unicodedata
import json
import os

from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone as dt_tz
from difflib import SequenceMatcher
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from pitchapi import PitchAPI, PitchAPIError, NotFoundError

from pages import views as v
from pages.models import MatchAdvanced


BASE = "https://v3.football.api-sports.io"

DONE = ("FT", "AET", "PEN")

PITCH_SEASON = "2026/2027"

PAUSE = 0.4

MAX_FAILS_IN_ROW = 3


PITCH_LEAGUES = {
    "PL": "l_4WFCIZ",
    "PD": "l_0ErfuF",
    "SA": "l_0ALvwF",
    "BL1": "l_1Isor4",
    "FL1": "l_3FJFUl",
    "UCL": "l_0bfbkO",
    "UEL": "l_38d9HA",
    "UECL": "l_2WZ2tt",
}

DEFAULT_CODES = [
    "PL", "PD", "SA", "BL1",
    "FL1", "UCL", "UEL", "UECL"
]


ALIASES = {
    "wolverhampton wanderers": "wolves",
}


STOP = {
    "fc", "afc", "cf", "ac", "as", "sc", "ssc", "us",
    "ud", "cd", "rc", "rcd", "fk", "sv", "vfb", "vfl",
    "1", "the", "calcio", "club"
}


def norm(name):
    s = unicodedata.normalize(
        "NFKD",
        name or ""
    ).encode("ascii", "ignore").decode().lower()

    s = re.sub(r"[^a-z0-9 ]+", " ", s)

    s = " ".join(
        t for t in s.split()
        if t not in STOP
    )

    return ALIASES.get(s, s)


def sim(a, b):
    if not a or not b:
        return 0

    if a in b or b in a:
        return 0.9

    return SequenceMatcher(None, a, b).ratio()


def parse_dt(value):
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_tz.utc)

    return dt


def to_dict(value):
    """
    تحويل dataclass أو dict إلى dict عادي.
    """

    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if is_dataclass(value):
        return asdict(value)

    return {}



def extract_big_chances(stats_data):
    """
    استخراج Big Chances و Big Chances Missed
    من فترة All.
    """

    result = {
        "home": {
            "big_chances": None,
            "big_chances_missed": None,
        },
        "away": {
            "big_chances": None,
            "big_chances_missed": None,
        },
    }

    periods = stats_data.get("periods", [])

    all_period = next(
        (
            p for p in periods
            if p.get("period") == "All"
        ),
        None
    )

    if not all_period:
        return result

    wanted = {
        "big_chance": "big_chances",
        "big_chance_missed_title": "big_chances_missed",
    }

    for group in all_period.get("groups", []):
        for item in group.get("items", []):

            key = item.get("key")

            if key not in wanted:
                continue

            target = wanted[key]

            result["home"][target] = item.get("home")
            result["away"][target] = item.get("away")

    return result



def empty_big_chances():
    return {
        "home": {
            "big_chances": None,
            "big_chances_missed": None,
        },
        "away": {
            "big_chances": None,
            "big_chances_missed": None,
        },
    }


def load_fixtures(league_id):

    r = v.safe_api_get(
        f"{BASE}/fixtures",
        headers=v.headers,
        params={
            "league": league_id,
            "season": v.SEASON
        },
        timeout=20
    )

    j = r.json()

    if r.status_code != 200 or j.get("errors"):
        raise CommandError(
            f"API-Football failed: {j.get('errors')}"
        )

    out = []

    for f in j.get("response", []):

        if f["fixture"]["status"]["short"] not in DONE:
            continue

        dt = parse_dt(f["fixture"]["date"])

        if not dt:
            continue

        f["_dt"] = dt
        f["_h"] = norm(f["teams"]["home"]["name"])
        f["_a"] = norm(f["teams"]["away"]["name"])

        out.append(f)

    return out


def find_fixture(pm, fixtures, taken):

    pdt = parse_dt(pm.time_utc)

    if not pdt:
        return None

    ph = norm(pm.home_team.name)
    pa = norm(pm.away_team.name)

    best = None
    best_score = 0

    for f in fixtures:

        if f["fixture"]["id"] in taken:
            continue

        if abs(
            (f["_dt"] - pdt).total_seconds()
        ) > 36 * 3600:
            continue

        if (
            f["goals"]["home"] != pm.score_home
            or f["goals"]["away"] != pm.score_away
        ):
            continue

        s = (
            sim(ph, f["_h"]) +
            sim(pa, f["_a"])
        ) / 2

        if s > best_score:
            best = f
            best_score = s

    return best if best_score >= 0.5 else None


class Command(BaseCommand):

    help = "Store advanced analytics and team stats from PitchAPI"

    def add_arguments(self, parser):

        parser.add_argument(
            "--league",
            help="PL / PD / SA / BL1 / FL1 / UCL / UEL / UECL (default: all)",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=40,
            help="max PitchAPI match requests per league (0 = no limit)",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="re-check old matches, including matches with saved analytics",
        )

    def handle(self, *args, **opts):

        codes = (
            [opts["league"]]
            if opts["league"]
            else DEFAULT_CODES
        )

        recent = timezone.now() - timedelta(days=3)

        key = pitch_api_key()

        if not key:
            raise CommandError(
                "PitchAPI key not found. Put PITCHAPI_API_KEY=... "
                "in the .env file next to manage.py"
            )

        with PitchAPI(api_key=key) as client:

            for code in codes:

                if (
                    code not in PITCH_LEAGUES
                    or code not in v.LEAGUES
                ):
                    self.stderr.write(
                        f"{code}: unknown league"
                    )
                    continue

                self.stdout.write(
                    f"\n========== START {code} ==========\n"
                )

                fixtures = load_fixtures(
                    v.LEAGUES[code]["id"]
                )

                known = {
                    x.pitch_id: x
                    for x in MatchAdvanced.objects.filter(
                        league_code=code,
                        season=v.SEASON
                    )
                }

                taken = {
                    x.fixture_id
                    for x in known.values()
                }

                try:

                    listing = client.leagues.matches(
                        PITCH_LEAGUES[code],
                        season=PITCH_SEASON
                    )

                except PitchAPIError as e:

                    self.stderr.write(
                        f"{code}: PitchAPI list FAILED -> {e}"
                    )

                    return

                budget = opts["limit"] or 10**9

                saved = 0
                advanced_unavailable = 0
                stats_unavailable = 0
                failed = 0
                in_row = 0

                unmatched = []

                for pm in listing.matches:

                    if budget <= 0:
                        break

                    old = known.get(pm.id)

                    # تخطي المباريات المحفوظة عند عدم استخدام force
                    if old and not opts["force"]:

                        if (
                            old.data is not None
                            or (
                                old.played_at
                                and old.played_at < recent
                            )
                        ):
                            continue

                    # السماح بإعادة مطابقة المباراة عند force
                    if old and opts["force"]:
                        taken.discard(old.fixture_id)

                    fx = find_fixture(
                        pm,
                        fixtures,
                        taken
                    )

                    if not fx:

                        unmatched.append(
                            f"{pm.home_team.name} "
                            f"{pm.score_home}-{pm.score_away} "
                            f"{pm.away_team.name}"
                        )

                        if old:
                            taken.add(old.fixture_id)

                        continue

                    fid = fx["fixture"]["id"]

                    base = {
                        "pitch_id": pm.id,
                        "league_code": code,
                        "season": v.SEASON,
                        "played_at": fx["_dt"],
                        "home_id": fx["teams"]["home"]["id"],
                        "away_id": fx["teams"]["away"]["id"],
                    }

                    # الاحتفاظ بالبيانات القديمة عند عدم توفر مصدر جديد
                    existing_data = (
                        dict(old.data)
                        if old and isinstance(old.data, dict)
                        else {}
                    )

                    # ==========================================
                    # 1. جلب Advanced Analytics
                    # ==========================================

                    home_data = existing_data.get("home")
                    away_data = existing_data.get("away")

                    advanced_ok = False

                    try:

                        adv = client.matches.advanced(pm.id)

                        by = {
                            t.team.id: t
                            for t in adv.teams
                        }

                        home = by.get(pm.home_team.id)
                        away = by.get(pm.away_team.id)

                        if home and away:

                            home_data = asdict(home)
                            away_data = asdict(away)

                            advanced_ok = True

                        else:

                            self.stderr.write(
                                f"  {pm.id}: advanced home/away data missing"
                            )

                    except NotFoundError:

                        advanced_unavailable += 1

                        self.stderr.write(
                            f"  {pm.id}: advanced analytics unavailable"
                        )

                    except PitchAPIError as e:

                        failed += 1
                        in_row += 1

                        self.stderr.write(
                            f"  {pm.id}: ADVANCED FAILED -> {e}"
                        )

                    # ==========================================
                    # 2. جلب Team Stats
                    # ==========================================

                    stats_data = existing_data.get(
                        "team_stats",
                        {}
                    )

                    big_chances = existing_data.get(
                        "big_chances",
                        empty_big_chances()
                    )

                    stats_ok = False

                    try:

                        match_stats = client.matches.stats(pm.id)

                        stats_data = to_dict(match_stats)

                        big_chances = extract_big_chances(
                            stats_data
                        )

                        stats_ok = True

                    except NotFoundError:

                        stats_unavailable += 1

                        self.stderr.write(
                            f"  {pm.id}: team stats unavailable"
                        )

                    except PitchAPIError as e:

                        failed += 1
                        in_row += 1

                        self.stderr.write(
                            f"  {pm.id}: TEAM STATS FAILED -> {e}"
                        )

                    # ==========================================
                    # 3. طباعة Big Chances للفحص
                    # ==========================================

                    self.stdout.write(
                        "\n========== MATCH DATA =========="
                    )

                    self.stdout.write(
                        f"MATCH: {pm.home_team.name} "
                        f"vs {pm.away_team.name}"
                    )

                    self.stdout.write(
                        f"PITCH MATCH ID: {pm.id}"
                    )

                    self.stdout.write(
                        f"ADVANCED OK: {advanced_ok}"
                    )

                    self.stdout.write(
                        f"TEAM STATS OK: {stats_ok}"
                    )

                    self.stdout.write(
                        "\nBIG CHANCES:"
                    )

                    self.stdout.write(
                        json.dumps(
                            big_chances,
                            ensure_ascii=False,
                            indent=2,
                            default=str
                        )
                    )

                    if stats_ok:

                        self.stdout.write(
                            "\nTEAM STATS PERIODS:"
                        )

                        self.stdout.write(
                            json.dumps(
                                stats_data.get("periods", []),
                                ensure_ascii=False,
                                indent=2,
                                default=str
                            )
                        )

                    self.stdout.write(
                        "\n================================\n"
                    )

                    # ==========================================
                    # 4. حفظ البيانات
                    # ==========================================

                    final_data = {
                        **existing_data,
                    }

                    if advanced_ok:

                        final_data["home"] = home_data
                        final_data["away"] = away_data

                    if stats_ok:

                        final_data["team_stats"] = stats_data
                        final_data["big_chances"] = big_chances

                    # لا ننشئ سجلًا فارغًا إذا لم يرجع أي مصدر بيانات
                    if advanced_ok or stats_ok:

                        MatchAdvanced.objects.update_or_create(
                            fixture_id=fid,
                            defaults={
                                **base,
                                "data": final_data
                            }
                        )

                        saved += 1

                    elif not old:

                        MatchAdvanced.objects.update_or_create(
                            fixture_id=fid,
                            defaults={
                                **base,
                                "data": None
                            }
                        )

                    taken.add(fid)

                    budget -= 1

                    if in_row >= MAX_FAILS_IN_ROW:

                        self.stderr.write(
                            "Stopped: repeated API failures."
                        )

                        return

                    if advanced_ok or stats_ok:
                        in_row = 0

                    time.sleep(PAUSE)

                self.stdout.write(
                    f"\n{code}: "
                    f"saved={saved} "
                    f"advanced_unavailable={advanced_unavailable} "
                    f"stats_unavailable={stats_unavailable} "
                    f"failed={failed} "
                    f"unmatched={len(unmatched)}"
                )

                for line in unmatched[:10]:

                    self.stdout.write(
                        f"   unmatched: {line}"
                    )

                self.stdout.write(
                    f"\n========== END {code} ==========\n"
                )


def pitch_api_key():
    """
    المفتاح من:
    1. متغير البيئة
    2. Django settings
    3. ملف .env بجانب manage.py
    """

    key = (
        os.environ.get("PITCHAPI_API_KEY")
        or getattr(settings, "PITCHAPI_API_KEY", "")
    )

    if key:
        return key.strip()

    env_file = Path(settings.BASE_DIR) / ".env"

    if env_file.exists():

        for line in env_file.read_text(
            encoding="utf-8"
        ).splitlines():

            line = line.strip()

            if line.startswith("PITCHAPI_API_KEY="):

                return (
                    line.split("=", 1)[1]
                    .strip()
                    .strip('"')
                    .strip("'")
                )

    return ""
