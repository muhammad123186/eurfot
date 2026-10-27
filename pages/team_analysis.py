"""
معاينات مباريات مبنية على البيانات: مقالة لكل مباراة، من منظور أهم فريق فيها.
"""
from datetime import date, datetime, timedelta

import requests
from django.core.cache import cache
from django.utils.text import slugify

from .models import AnalysisArticle
from .views import (
    LEAGUES, SEASON, TEAM_TROPHIES, headers,
    _get_api_standings, _ordinal, clean_team_name, get_standings,
    get_today_matches, ranked_today_matches, safe_api_get, team_tier,
)

DOMESTIC = ["PL", "PD", "SA", "BL1", "FL1"]
EUROPE = ["UCL", "UEL", "UECL"]
DONE = ("FT", "AET", "PEN")
MAX_PER_DAY = 8          # لا ترفعه كثيرًا (حصة API وجودة المحتوى)
MIN_BODY_PARAGRAPHS = 5  # أقل من هذا = مقالة رقيقة فلا تُنشر


# ---------------------------------------------------------------- مساعدات
def _the(name):
    return f"the {name}" if name.startswith(("Premier", "FA ", "EFL", "UEFA")) else name


def _join(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _rec(rs):
    w = sum(1 for r in rs if r["res"] == "W")
    d = sum(1 for r in rs if r["res"] == "D")
    l = sum(1 for r in rs if r["res"] == "L")
    return w, d, l, sum(r["gf"] for r in rs), sum(r["ga"] for r in rs)


def _streak(rs, test):
    n = 0
    for r in reversed(rs):
        if test(r):
            n += 1
        else:
            break
    return n


def _fmt(r):
    where = "at home to" if r["home"] else "away at"
    return f"{r['res']} {r['gf']}-{r['ga']} {where} {r['opp']}"


# ---------------------------------------------------------------- جلب البيانات
def _league_fixtures(code):
    """كل مباريات الدوري (طلب واحد لكل دوري، كاش 5 دقائق)"""
    key = f"an_fixtures_v1_{code}_{SEASON}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        r = safe_api_get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={"league": LEAGUES[code]["id"], "season": SEASON},
            timeout=20,
        )
        data = r.json().get("response", [])
    except (requests.RequestException, ValueError):
        return []

    out = []
    for f in data if isinstance(data, list) else []:
        if not (f["league"].get("round") or "").startswith("Regular Season"):
            continue
        ht = (f.get("score") or {}).get("halftime") or {}
        out.append({
            "id": f["fixture"]["id"],
            "date": f["fixture"]["date"],
            "status": f["fixture"]["status"]["short"],
            "home_id": f["teams"]["home"]["id"],
            "home": clean_team_name(f["teams"]["home"]["name"]),
            "away_id": f["teams"]["away"]["id"],
            "away": clean_team_name(f["teams"]["away"]["name"]),
            "hg": f["goals"]["home"], "ag": f["goals"]["away"],
            "hht": ht.get("home"), "aht": ht.get("away"),
        })

    cache.set(key, out, 300 if out else 30)
    return out


def _h2h(home_id, away_id):
    a, b = sorted((home_id, away_id))
    key = f"an_h2h_v1_{a}_{b}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        r = safe_api_get(
            "https://v3.football.api-sports.io/fixtures/headtohead",
            headers=headers,
            params={"h2h": f"{a}-{b}", "last": 10},
            timeout=20,
        )
        data = r.json().get("response", [])
    except (requests.RequestException, ValueError):
        return []

    out = []
    for f in data if isinstance(data, list) else []:
        if f["fixture"]["status"]["short"] not in DONE:
            continue
        hg, ag = f["goals"]["home"], f["goals"]["away"]
        if hg is None or ag is None:
            continue
        out.append({
            "date": f["fixture"]["date"][:10],
            "comp": f["league"]["name"],
            "home_id": f["teams"]["home"]["id"],
            "home": clean_team_name(f["teams"]["home"]["name"]),
            "away_id": f["teams"]["away"]["id"],
            "away": clean_team_name(f["teams"]["away"]["name"]),
            "hg": hg, "ag": ag,
        })

    out.sort(key=lambda x: x["date"], reverse=True)
    cache.set(key, out, 60 * 60 * 12)
    return out


def _league_leaders(code):
    key = f"an_leaders_v1_{code}_{SEASON}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    out = {"scorers": [], "assists": []}

    for endpoint, field in (("topscorers", "scorers"), ("topassists", "assists")):
        try:
            r = requests.get(
                f"https://v3.football.api-sports.io/players/{endpoint}",
                headers=headers,
                params={"league": LEAGUES[code]["id"], "season": SEASON},
                timeout=15,
            )
            entries = r.json().get("response", [])
        except (requests.RequestException, ValueError):
            entries = []

        for e in entries:
            stats = (e.get("statistics") or [{}])[0]
            goals = stats.get("goals") or {}
            out[field].append({
                "name": (e.get("player") or {}).get("name"),
                "team_id": (stats.get("team") or {}).get("id"),
                "goals": goals.get("total") or 0,
                "assists": goals.get("assists") or 0,
                "rank": len(out[field]) + 1,
            })

    ok = out["scorers"] or out["assists"]
    cache.set(key, out, 60 * 60 * 3 if ok else 60)
    return out


def _build_team_index():
    """{team_id: (league_code, standings_row, table)} للدوريات الخمسة"""
    index = {}
    for code in DOMESTIC:
        table = get_standings(code) or []
        for row in table:
            index[row["team"]["id"]] = (code, row, table)
    return index


def _team_profile(team_id, team_index):
    entry = team_index.get(team_id)
    if not entry:
        return None

    code, row, table = entry
    played, upcoming = [], []

    for f in _league_fixtures(code):
        if team_id not in (f["home_id"], f["away_id"]):
            continue
        if f["status"] in DONE and f["hg"] is not None and f["ag"] is not None:
            played.append(f)
        elif f["status"] in ("NS", "TBD"):
            upcoming.append(f)

    played.sort(key=lambda f: f["date"])
    upcoming.sort(key=lambda f: f["date"])

    results = []
    for f in played:
        home = f["home_id"] == team_id
        gf, ga = (f["hg"], f["ag"]) if home else (f["ag"], f["hg"])
        hf, ha = (f["hht"], f["aht"]) if home else (f["aht"], f["hht"])
        results.append({
            "home": home,
            "opp": f["away"] if home else f["home"],
            "gf": gf, "ga": ga,
            "res": "W" if gf > ga else "D" if gf == ga else "L",
            "ht_for": hf, "ht_against": ha,
        })

    return {
        "team_id": team_id, "code": code, "row": row, "table": table,
        "results": results, "upcoming": upcoming,
    }


# ---------------------------------------------------------------- الفقرات
def _form_para(name, prof):
    rs = prof["results"]
    if len(rs) < 3:
        return None

    last = rs[-5:]
    w, d, l, _, _ = _rec(last)
    recent = "; ".join(_fmt(r) for r in reversed(last))
    text = (
        f"In their last {len(last)} league games {name} have won {w}, drawn {d} and lost {l}. "
        f"Most recent first: {recent}."
    )

    wins = _streak(rs, lambda r: r["res"] == "W")
    unbeaten = _streak(rs, lambda r: r["res"] != "L")
    losses = _streak(rs, lambda r: r["res"] == "L")
    winless = _streak(rs, lambda r: r["res"] != "W")

    if wins >= 2:
        text += f" They have won their last {wins} league games."
    elif unbeaten >= 3:
        text += f" They are unbeaten in {unbeaten} league games."
    elif losses >= 2:
        text += f" They have lost their last {losses} league games."
    elif winless >= 3:
        text += f" They are winless in {winless} league games."
    return text


def _position_para(name, prof):
    row, table = prof["row"], prof["table"]
    a = row["all"]
    played = a["played"]
    if not played:
        return None

    league = LEAGUES[prof["code"]]["name"]
    pts = row["points"]
    gf, ga = a["goals"]["for"], a["goals"]["against"]
    gd = row.get("goalsDiff")
    if gd is None:
        gd = gf - ga

    text = (
        f"{name} sit {_ordinal(row['rank'])} in {_the(league)} with {pts} points from {played} games "
        f"({a['win']}W {a['draw']}D {a['lose']}L), scoring {gf} and conceding {ga} "
        f"for a goal difference of {gd:+d}. That is {pts / played:.2f} points per game."
    )

    leader = table[0]
    if row["rank"] == 1 and len(table) > 1:
        text += f" They lead the table, {pts - table[1]['points']} points ahead of {table[1]['team']['name']}."
    elif row["rank"] != 1:
        text += f" They are {leader['points'] - pts} points behind leaders {leader['team']['name']}."

    fourth = next((r for r in table if r.get("rank") == 4), None)
    if fourth and row["rank"] != 4:
        diff = pts - fourth["points"]
        if diff > 0:
            text += f" They are {diff} points above fourth place."
        elif diff < 0:
            text += f" They are {-diff} points below fourth place."
        else:
            text += " They are level on points with fourth place."

    last = table[-1]
    if row["rank"] > len(table) / 2 and last is not row:
        text += f" They are {pts - last['points']} points clear of bottom-placed {last['team']['name']}."
    return text


def _split_para(name, prof, home_today):
    rs = prof["results"]
    h = [r for r in rs if r["home"]]
    a = [r for r in rs if not r["home"]]
    if len(h) < 2 and len(a) < 2:
        return None

    parts = []
    for label, grp in (("At home", h), ("Away from home", a)):
        if grp:
            w, d, l, gf, ga = _rec(grp)
            parts.append(
                f"{label} they have {w} wins, {d} draws and {l} defeats from {len(grp)} games "
                f"({gf} scored, {ga} conceded)"
            )

    text = ". ".join(parts) + "."
    side = h if home_today else a
    if len(side) >= 2:
        w, d, _, _, _ = _rec(side)
        text += (
            f" Today's game is {'at home' if home_today else 'away'}, "
            f"where they have taken {w * 3 + d} points from {len(side)} league games."
        )
    return text


def _goals_para(name, prof):
    rs = prof["results"]
    n = len(rs)
    if n < 4:
        return None

    gf = sum(r["gf"] for r in rs)
    ga = sum(r["ga"] for r in rs)
    clean = sum(1 for r in rs if r["ga"] == 0)
    blank = sum(1 for r in rs if r["gf"] == 0)
    both = sum(1 for r in rs if r["gf"] > 0 and r["ga"] > 0)
    high = sum(1 for r in rs if r["gf"] + r["ga"] >= 3)

    text = (
        f"Across {n} league games {name} average {gf / n:.2f} goals scored and {ga / n:.2f} conceded. "
        f"They have kept {clean} clean {'sheet' if clean == 1 else 'sheets'} and failed to score in {blank}. "
        f"Both teams scored in {both} of their games, and {high} produced three or more goals in total."
    )

    wins = [r for r in rs if r["res"] == "W"]
    losses = [r for r in rs if r["res"] == "L"]
    if wins:
        bw = max(wins, key=lambda r: r["gf"] - r["ga"])
        text += f" Their biggest league win was {bw['gf']}-{bw['ga']} {'at home to' if bw['home'] else 'away at'} {bw['opp']}."
    if losses:
        bl = max(losses, key=lambda r: r["ga"] - r["gf"])
        text += f" Their heaviest defeat was {bl['gf']}-{bl['ga']} {'at home to' if bl['home'] else 'away at'} {bl['opp']}."
    return text


def _halftime_para(name, prof):
    rs = [r for r in prof["results"]
          if r["ht_for"] is not None and r["ht_against"] is not None]
    if len(rs) < 5:
        return None

    lead = [r for r in rs if r["ht_for"] > r["ht_against"]]
    trail = [r for r in rs if r["ht_for"] < r["ht_against"]]
    if not lead and not trail:
        return None

    parts = []
    if lead:
        won = sum(1 for r in lead if r["res"] == "W")
        parts.append(f"{name} have led at half-time in {len(lead)} of {len(rs)} league games and won {won} of them.")
    if trail:
        pts = sum(1 for r in trail if r["res"] != "L")
        parts.append(f"They have trailed at the break {len(trail)} times, taking at least a point from {pts}.")
    return " ".join(parts)


def _players_para(name, prof):
    code, tid = prof["code"], prof["team_id"]
    league = LEAGUES[code]["name"]
    data = _league_leaders(code)

    scorers = [p for p in data["scorers"] if p["team_id"] == tid]
    assisters = [p for p in data["assists"] if p["team_id"] == tid]

    parts = []
    if scorers:
        s = scorers[0]
        extra = f" (plus {s['assists']} assists)" if s["assists"] else ""
        parts.append(
            f"{s['name']} is {name}'s leading scorer with {s['goals']} league goals{extra}, "
            f"{_ordinal(s['rank'])} in {_the(league)} scoring charts"
        )
    if assisters and (not scorers or assisters[0]["name"] != scorers[0]["name"]):
        a = assisters[0]
        parts.append(
            f"{a['name']} leads their creative output with {a['assists']} assists, "
            f"{_ordinal(a['rank'])} in the league"
        )
    if len(scorers) > 1:
        parts.append(f"{scorers[1]['name']} adds {scorers[1]['goals']} goals")

    return (". ".join(parts) + ".") if parts else None


def _opponent_para(name, prof, away_today):
    row = prof["row"]
    a = row["all"]
    league = LEAGUES[prof["code"]]["name"]

    text = (
        f"{name} are {_ordinal(row['rank'])} in {_the(league)} on {row['points']} points "
        f"({a['win']}W {a['draw']}D {a['lose']}L, {a['goals']['for']} scored, {a['goals']['against']} conceded)."
    )

    rs = prof["results"]
    if len(rs) >= 3:
        last = rs[-5:]
        text += f" Their last {len(last)} league results, oldest to newest, read {'-'.join(r['res'] for r in last)}."

    venue = [r for r in rs if r["home"] == (not away_today)]
    if len(venue) >= 2:
        w, d, l, gf, ga = _rec(venue)
        text += (
            f" {'Away' if away_today else 'At home'} they have {w} wins, {d} draws and {l} defeats "
            f"from {len(venue)} games ({gf} scored, {ga} conceded)."
        )

    players = _players_para(name, prof)
    if players:
        text += " " + players
    return text


def _h2h_para(home, away, home_id, rows):
    if len(rows) < 2:
        return None

    hw = aw = dr = goals = 0
    for r in rows:
        goals += r["hg"] + r["ag"]
        if r["hg"] == r["ag"]:
            dr += 1
        else:
            winner = r["home_id"] if r["hg"] > r["ag"] else r["away_id"]
            if winner == home_id:
                hw += 1
            else:
                aw += 1

    n = len(rows)
    text = (
        f"In their last {n} meetings {home} have won {hw}, {away} have won {aw} and {dr} ended level, "
        f"averaging {goals / n:.1f} goals per game."
    )

    recent = []
    for r in rows[:5]:
        dt = _parse_dt(r["date"])
        when = f"{dt.day} {dt.strftime('%B %Y')}" if dt else r["date"]
        recent.append(f"{when}: {r['home']} {r['hg']}-{r['ag']} {r['away']} ({r['comp']})")

    return text + " Most recent first: " + "; ".join(recent) + "."


def _context_para(feat, feat_id, prof_f, code, comp):
    if code in DOMESTIC and prof_f:
        pts = prof_f["row"]["points"]
        return (
            f"This is a league fixture, so the result goes straight into the league table: "
            f"a win would take {feat} to {pts + 3} points and a draw to {pts + 1}."
        )

    if code in EUROPE:
        table = _get_api_standings(code) or []
        row = next((r for r in table if r["team"]["id"] == feat_id), None)
        if row:
            return (
                f"In the {comp} league phase {feat} are {_ordinal(row['rank'])} with {row['points']} points "
                f"from {row['all']['played']} games. Domestic league numbers above are context rather than "
                f"a direct predictor of this result."
            )

    return (
        f"{comp} is a different competition from the league, so the league statistics above are "
        f"context rather than a direct predictor of the result."
    )


def _honours_para(feat_id, feat, opp_id, opp):
    out = []
    for tid, nm in ((feat_id, feat), (opp_id, opp)):
        t = TEAM_TROPHIES.get(tid) or {}
        items = sorted(((k, v) for k, v in t.items() if v), key=lambda kv: -kv[1])[:4]
        if items:
            out.append(f"{nm}'s honours on record include " + _join([f"{k} ({v})" for k, v in items]) + ".")
    return " ".join(out) or None


def _next_para(name, prof, fixture_id):
    ups = [f for f in prof["upcoming"] if f["id"] != fixture_id][:3]
    if not ups:
        return None

    items = []
    for f in ups:
        home = f["home_id"] == prof["team_id"]
        opp = f["away"] if home else f["home"]
        dt = _parse_dt(f["date"])
        when = f", {dt.day} {dt.strftime('%B')}" if dt else ""
        items.append(f"{opp} ({'home' if home else 'away'}{when})")

    return f"After this match, {name}'s next league fixtures are {_join(items)}."


# ---------------------------------------------------------------- بناء المقالة
def _build_article(m, group, team_index):
    home_id, away_id = m["homeTeam"]["id"], m["awayTeam"]["id"]
    home, away = m["homeTeam"]["name"], m["awayTeam"]["name"]
    code, comp = group["code"], group["name"]

    kick = _parse_dt(m.get("utcDate")) or datetime.now()
    date_text = f"{kick.day} {kick.strftime('%B %Y')}"

    def rank_of(tid):
        entry = team_index.get(tid)
        return entry[1]["rank"] if entry else 99

    feat_home = (team_tier(home_id, code), rank_of(home_id)) <= (team_tier(away_id, code), rank_of(away_id))

    if feat_home:
        feat_id, feat, opp_id, opp = home_id, home, away_id, away
        logo = m["homeTeam"]["crest"]
    else:
        feat_id, feat, opp_id, opp = away_id, away, home_id, home
        logo = m["awayTeam"]["crest"]

    prof_f = _team_profile(feat_id, team_index)
    prof_o = _team_profile(opp_id, team_index)
    h2h_rows = _h2h(home_id, away_id)

    paras = [
        f"{home} face {away} in {_the(comp)} on {date_text}. This preview gathers the form, league position, "
        f"home and away records, goals, key players and head-to-head history of both sides, "
        f"using the data available before kick-off."
    ]

    def section(heading, *texts):
        texts = [t for t in texts if t]
        if texts:
            paras.append(f"## {heading}")
            paras.extend(texts)

    if prof_f:
        league_f = LEAGUES[prof_f["code"]]["name"]
        section(f"{feat}: recent form", _form_para(feat, prof_f))
        section(f"{feat} in {_the(league_f)}", _position_para(feat, prof_f))
        section(f"{feat}: home and away record", _split_para(feat, prof_f, feat_home))
        section(f"{feat}: goals and scoring trends", _goals_para(feat, prof_f), _halftime_para(feat, prof_f))
        section(f"{feat}: players to watch", _players_para(feat, prof_f))

    if prof_o:
        section(f"Opposition watch: {opp}", _opponent_para(opp, prof_o, away_today=feat_home))

    section(f"Head-to-head: {home} vs {away}", _h2h_para(home, away, home_id, h2h_rows))
    section("What is at stake", _context_para(feat, feat_id, prof_f, code, comp))
    section("Club pedigree", _honours_para(feat_id, feat, opp_id, opp))

    if prof_f:
        section(f"Fixtures ahead for {feat}", _next_para(feat, prof_f, m["id"]))

    body = [p for p in paras if not p.startswith("## ")]
    if len(body) < MIN_BODY_PARAGRAPHS:
        return None

    paras.append(
        f"The match page on Eurfot carries the lineups, live events, team statistics and the full "
        f"head-to-head record for {home} vs {away}."
    )

    summary = f"{home} vs {away} in {_the(comp)} on {date_text}."
    if prof_f:
        r = prof_f["row"]
        summary += (
            f" {feat} sit {_ordinal(r['rank'])} in {_the(LEAGUES[prof_f['code']]['name'])} "
            f"on {r['points']} points. Form guide, head-to-head and key stats inside."
        )
    else:
        summary += " Form guide, head-to-head record and key stats inside."

    slug = slugify(f"{home} vs {away} {comp} preview")[:120] + f"-{m['id']}"

    return {
        "kind": "match",
        "title": f"{home} vs {away}: {comp} Preview, Form and Key Stats"[:200],
        "summary": summary,
        "paragraphs": paras,
        "image_url": logo,
        "league_code": code,
        "slug": slug,
    }


def run_team_articles(days=1, force=False):
    """يولّد معاينات أهم مباريات اليوم (وما بعده إن days > 1). يعيد القائمة المنشأة/المحدّثة."""
    done = []
    team_index = _build_team_index()

    for offset in range(days):
        target = date.today() + timedelta(days=offset)
        ranked = ranked_today_matches(get_today_matches(target))

        todo = [(m, g) for _, m, g in ranked if m["status"] in ("NS", "TBD")][:MAX_PER_DAY]

        for m, group in todo:
            key = f"tp-{m['id']}"
            existing = AnalysisArticle.objects.filter(key=key).first()

            if existing and not force:
                continue

            data = _build_article(m, group, team_index)
            if not data:
                continue

            if existing:
                data.pop("slug")
                for field, value in data.items():
                    setattr(existing, field, value)
                existing.save()
                done.append(existing)
            else:
                done.append(AnalysisArticle.objects.create(key=key, **data))

    return done