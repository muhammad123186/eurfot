import random
from django.utils.text import slugify
from .models import AnalysisArticle
from . import views as v

DONE = {"FT", "AET", "PEN"}
LEAGUE_CODES = ["PL", "PD", "SA", "BL1", "FL1"]


def _save(kind, key, title, paragraphs, image="", code=""):
    if AnalysisArticle.objects.filter(key=key).exists():
        return None
    return AnalysisArticle.objects.create(
        kind=kind,
        key=key,
        slug=f"{slugify(title)[:120]}-{slugify(key)[:40]}",
        title=title,
        summary=paragraphs[0][:220],
        paragraphs=paragraphs,
        image_url=image or "",
        league_code=code,
    )


def _form_points(form):
    return sum({"W": 3, "D": 1}.get(c, 0) for c in (form or ""))


def _edge(n1, n2, v1, v2, what, lower_better=False):
    if v1 == v2:
        return f"{n1} and {n2} are level on {what} ({v1})."
    first_better = (v1 < v2) if lower_better else (v1 > v2)
    best, worst = (n1, n2) if first_better else (n2, n1)
    hi, lo = (v1, v2) if first_better else (v2, v1)
    return f"{best} have the edge in {what}: {hi} against {lo} for {worst}."


# ---------------- تحليل جولة ----------------
def round_analysis(code):
    league = v.LEAGUES[code]["name"]
    md = v.get_current_matchday(code)
    games = []

    for m in (md, md - 1):
        if m < 1:
            continue
        _, g = v.get_matches(code, m)
        fin = [x for x in g if x["status"] in DONE]
        if g and len(fin) >= 0.8 * len(g):
            md, games = m, fin
            break

    sc = [
        (g, g["score"]["fullTime"]["home"], g["score"]["fullTime"]["away"])
        for g in games
    ]
    sc = [(g, h, a) for g, h, a in sc if h is not None and a is not None]
    if not sc:
        return None

    key = f"round_{code}_{md}"
    if AnalysisArticle.objects.filter(key=key).exists():
        return None

    total = sum(h + a for _, h, a in sc)
    avg = total / len(sc)
    home_w = sum(h > a for _, h, a in sc)
    away_w = sum(a > h for _, h, a in sc)
    draws = len(sc) - home_w - away_w
    clean = sum((h == 0) + (a == 0) for _, h, a in sc)
    big, bh, ba = max(sc, key=lambda t: abs(t[1] - t[2]))
    top, th, ta = max(sc, key=lambda t: t[1] + t[2])

    r = random.Random(key)
    p = [
        r.choice([
            f"Matchday {md} of the {league} produced {total} goals in {len(sc)} games, an average of {avg:.2f} per match.",
            f"{len(sc)} matches were completed in {league} Matchday {md}, delivering {total} goals ({avg:.2f} per game).",
        ]),
        f"Home sides won {home_w} games, away teams won {away_w}, and {draws} ended level. Goalkeepers kept {clean} clean sheets across the round.",
    ]

    if bh != ba:
        p.append(
            f"The widest margin was {big['homeTeam']['name']} {bh}-{ba} {big['awayTeam']['name']}."
        )
    if top["id"] != big["id"] or bh == ba:
        p.append(
            f"The highest-scoring game was {top['homeTeam']['name']} {th}-{ta} {top['awayTeam']['name']}."
        )

    table = v.get_standings(code)
    if len(table) >= 2:
        gap = table[0]["points"] - table[1]["points"]
        p.append(
            f"After the round, {table[0]['team']['name']} lead the table on {table[0]['points']} points, "
            + (f"{gap} clear of {table[1]['team']['name']}." if gap else f"level with {table[1]['team']['name']}.")
        )

    return _save(
        "round", key,
        f"{league} Matchday {md} Analysis: {total} Goals and {home_w} Home Wins",
        p, v.LEAGUES[code]["logo"], code,
    )


# ---------------- تحليل مباراة ----------------
def _h2h(home_id, away_id):
    try:
        resp = v.safe_api_get(
            "https://v3.football.api-sports.io/fixtures/headtohead",
            headers=v.headers,
            params={"h2h": f"{home_id}-{away_id}", "last": 10},
            timeout=15,
        )
        data = resp.json().get("response", [])
    except Exception:
        return None

    hw = aw = d = 0
    for m in data:
        h, a = m["goals"]["home"], m["goals"]["away"]
        if h is None or a is None:
            continue
        if h == a:
            d += 1
        elif (h > a) == (m["teams"]["home"]["id"] == home_id):
            hw += 1
        else:
            aw += 1
    total = hw + aw + d
    return (hw, aw, d, total) if total else None


def match_analysis(m):
    status = m["status"]
    if status == "NS":
        mode = "preview"
    elif status in DONE:
        mode = "report"
    else:
        return None

    key = f"match_{m['id']}_{mode}"
    if AnalysisArticle.objects.filter(key=key).exists():
        return None

    code = m["league"]["code"]
    league = m["league"]["name"]
    h, a = m["homeTeam"], m["awayTeam"]
    hn, an = h["name"], a["name"]

    hs = v.get_team_stats_full(h["id"])["stats"]
    as_ = v.get_team_stats_full(a["id"])["stats"]
    if not hs.get("played") or not as_.get("played"):
        return None

    p = []
    hg = m["score"]["fullTime"]["home"]
    ag = m["score"]["fullTime"]["away"]

    if mode == "preview":
        p.append(f"{hn} host {an} in the {league}, a game that pairs two sides with contrasting seasons so far.")
        title = f"{hn} vs {an}: {league} Preview and Key Stats"
    else:
        if hg > ag:
            res = f"{hn} beat {an} {hg}-{ag}"
        elif ag > hg:
            res = f"{an} won {ag}-{hg} away at {hn}"
        else:
            res = f"{hn} and {an} drew {hg}-{ag}"
        p.append(f"{res} in the {league}.")
        title = f"{hn} {hg}-{ag} {an}: Match Analysis"

    ranks = {r["team"]["id"]: r for r in v.get_standings(code) if r.get("team")}
    rh, ra = ranks.get(h["id"]), ranks.get(a["id"])
    if rh and ra:
        p.append(
            f"In the table, {hn} are {v._ordinal(rh['rank'])} with {rh['points']} points "
            f"and {an} are {v._ordinal(ra['rank'])} with {ra['points']}."
        )

    p.append(
        f"{hn} have won {hs['wins']} of {hs['played']} games this season, scoring {hs['goals_for']} and conceding {hs['goals_against']}. "
        f"{an} have won {as_['wins']} of {as_['played']}, scoring {as_['goals_for']} and conceding {as_['goals_against']}."
    )
    p.append(_edge(hn, an, hs["average_goals"], as_["average_goals"], "goals scored per game"))
    p.append(_edge(
        hn, an,
        round(hs["goals_against"] / hs["played"], 2),
        round(as_["goals_against"] / as_["played"], 2),
        "goals conceded per game", lower_better=True,
    ))

    h2h = _h2h(h["id"], a["id"])
    if h2h:
        hw, aw, d, tot = h2h
        p.append(f"In their last {tot} meetings, {hn} won {hw}, {an} won {aw} and {d} were drawn.")

    return _save("match", key, title, p, h["crest"], code)


# ---------------- تحليل فريق ----------------
def team_analysis(code, row):
    league = v.LEAGUES[code]["name"]
    t = row["team"]
    al = row.get("all") or {}
    played = al.get("played", 0)
    if played < 3:
        return None

    key = f"team_{t['id']}_{played}"
    if AnalysisArticle.objects.filter(key=key).exists():
        return None

    ho, aw = row.get("home") or {}, row.get("away") or {}
    gf = (al.get("goals") or {}).get("for", 0)
    ga = (al.get("goals") or {}).get("against", 0)
    form = row.get("form") or ""

    p = [
        f"{t['name']} are {v._ordinal(row['rank'])} in the {league} with {row['points']} points from {played} games "
        f"({al['win']}W {al['draw']}D {al['lose']}L) and a goal difference of {row.get('goalsDiff', 0):+d}.",
        f"They have scored {gf} and conceded {ga}, averaging {gf / played:.2f} goals for and {ga / played:.2f} against per game.",
    ]
    if ho.get("played") and aw.get("played"):
        p.append(
            f"At home the record is {ho['win']}W {ho['draw']}D {ho['lose']}L; away from home it is "
            f"{aw['win']}W {aw['draw']}D {aw['lose']}L."
        )
    if form:
        p.append(
            f"Their last {len(form)} league results read {' '.join(form)}, worth {_form_points(form)} points."
        )

    return _save(
        "team", key,
        f"{t['name']} {league} Analysis: {v._ordinal(row['rank'])} Place, {row['points']} Points After {played} Games",
        p, t["logo"], code,
    )


# ---------------- مقارنة فريقين ----------------
def compare_analysis(code, row1, row2):
    league = v.LEAGUES[code]["name"]
    id1, id2 = row1["team"]["id"], row2["team"]["id"]
    played = (row1.get("all") or {}).get("played", 0)
    key = f"compare_{id1}_{id2}_{played}"
    if played < 3 or AnalysisArticle.objects.filter(key=key).exists():
        return None

    t1, t2 = v.get_team_stats_full(id1), v.get_team_stats_full(id2)
    s1, s2 = t1["stats"], t2["stats"]
    if not s1.get("played") or not s2.get("played"):
        return None
    n1, n2 = t1["name"], t2["name"]

    p = [
        f"{n1} and {n2} sit first and second in the {league}, separated by "
        f"{row1['points'] - row2['points']} points. Here is how their seasons compare.",
        _edge(n1, n2, s1["win_rate"], s2["win_rate"], "win rate (%)"),
        _edge(n1, n2, s1["goals_for"], s2["goals_for"], "goals scored"),
        _edge(n1, n2, s1["goals_against"], s2["goals_against"], "goals conceded", lower_better=True),
        _edge(n1, n2, s1["clean_sheets"], s2["clean_sheets"], "clean sheets"),
    ]

    return _save(
        "compare", key,
        f"{n1} vs {n2}: {league} Title Race Compared",
        p, t1["logo"], code,
    )


# ---------------- التشغيل ----------------
def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        print("analysis error:", fn.__name__, e)
        return None


def run_all():
    made = []

    for code in LEAGUE_CODES:
        made.append(_safe(round_analysis, code))
        table = v.get_standings(code)
        if len(table) >= 2:
            made.append(_safe(team_analysis, code, table[0]))
            best = max(table, key=lambda r: _form_points(r.get("form")))
            if best is not table[0]:
                made.append(_safe(team_analysis, code, best))
            made.append(_safe(compare_analysis, code, table[0], table[1]))

    for m in v.get_featured_matches(v.get_today_matches())[:4]:
        made.append(_safe(match_analysis, m))

    return [x for x in made if x]