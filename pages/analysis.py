from datetime import date, timedelta

from django.utils.text import slugify

from . import views as v
from .models import AnalysisArticle

BASE = "https://v3.football.api-sports.io"
DONE = {"FT", "AET", "PEN"}
LEAGUE_CODES = ["PL", "PD", "SA", "BL1", "FL1"]
MATCH_CODES = LEAGUE_CODES + ["UCL", "UEL", "UECL"]
PRIORITY_IDS = (
    set(v.TOP_TEAM_ORDER) | set(v.AFTER_PL_TEAM_ORDER)
    | {50, 49, 85, 505, 496, 489, 530, 165, 47, 492}  # سيتي، تشيلسي، PSG، إنتر، يوفنتوس، ميلان، أتلتيكو، دورتموند، توتنهام، نابولي
)

ordn = v._ordinal
_FIX, _TABLE, _LEAD = {}, {}, {}


# ======================= DATA =======================
def _get(path, **params):
    try:
        r = v.safe_api_get(f"{BASE}/{path}", headers=v.headers, params=params, timeout=20)
        data = r.json().get("response", [])
        return data if isinstance(data, list) else []
    except Exception as e:
        print("api error:", path, repr(e))
        return []


def league_fixtures(code):
    if code not in _FIX:
        _FIX[code] = _get("fixtures", league=v.LEAGUES[code]["id"], season=v.SEASON)
    return _FIX[code]


def table(code):
    if code not in _TABLE:
        try:
            _TABLE[code] = v.get_standings(code) or []
        except Exception:
            _TABLE[code] = []
    return _TABLE[code]


def row_of(code, tid):
    return next((r for r in table(code) if r["team"]["id"] == tid), None)


def games_of(code, tid):
    out = []
    for f in league_fixtures(code):
        if f["fixture"]["status"]["short"] not in DONE:
            continue
        h, a = f["teams"]["home"], f["teams"]["away"]
        if tid not in (h["id"], a["id"]):
            continue
        hg, ag = f["goals"]["home"], f["goals"]["away"]
        if hg is None or ag is None:
            continue
        home = h["id"] == tid
        gf, ga = (hg, ag) if home else (ag, hg)
        opp = a if home else h
        out.append({
            "date": f["fixture"]["date"], "home": home, "gf": gf, "ga": ga,
            "opp": v.clean_team_name(opp["name"]), "opp_id": opp["id"],
            "res": "W" if gf > ga else ("D" if gf == ga else "L"),
        })
    out.sort(key=lambda g: g["date"])
    return out


def upcoming_of(code, tid, n=3):
    out = []
    for f in league_fixtures(code):
        if f["fixture"]["status"]["short"] not in ("NS", "TBD"):
            continue
        h, a = f["teams"]["home"], f["teams"]["away"]
        if tid not in (h["id"], a["id"]):
            continue
        home = h["id"] == tid
        opp = a if home else h
        out.append((f["fixture"]["date"], home, v.clean_team_name(opp["name"]), opp["id"]))
    out.sort(key=lambda x: x[0])
    return out[:n]


def league_avg(code):
    tot = n = 0
    for f in league_fixtures(code):
        g = f["goals"]
        if f["fixture"]["status"]["short"] in DONE and g["home"] is not None and g["away"] is not None:
            tot += g["home"] + g["away"]
            n += 1
    return (tot / n) if n else 0


def leaders(code):
    if code not in _LEAD:
        out = {"scorers": [], "assists": []}
        lid = v.LEAGUES[code]["id"]
        for key, ep in (("scorers", "topscorers"), ("assists", "topassists")):
            for i, e in enumerate(_get(f"players/{ep}", league=lid, season=v.SEASON), start=1):
                p = e.get("player") or {}
                s = (e.get("statistics") or [{}])[0]
                g = s.get("goals") or {}
                team = s.get("team") or {}
                out[key].append({
                    "rank": i, "name": p.get("name"), "team_id": team.get("id"),
                    "team": v.clean_team_name(team.get("name", "")),
                    "goals": g.get("total") or 0, "assists": g.get("assists") or 0,
                })
        _LEAD[code] = out
    return _LEAD[code]


def h2h_info(hid, aid):
    data = _get("fixtures/headtohead", h2h=f"{hid}-{aid}", last=10)
    hw = aw = d = goals = 0
    ms = []
    for m in sorted(data, key=lambda x: x["fixture"]["date"], reverse=True):
        hg, ag = m["goals"]["home"], m["goals"]["away"]
        if hg is None or ag is None:
            continue
        if hg == ag:
            d += 1
        elif (hg > ag) == (m["teams"]["home"]["id"] == hid):
            hw += 1
        else:
            aw += 1
        goals += hg + ag
        ms.append({
            "text": f"{v.clean_team_name(m['teams']['home']['name'])} {hg}-{ag} "
                    f"{v.clean_team_name(m['teams']['away']['name'])}",
            "year": m["fixture"]["date"][:4], "comp": m["league"]["name"],
        })
    if not ms:
        return None
    return {"n": len(ms), "hw": hw, "aw": aw, "d": d, "avg": round(goals / len(ms), 2), "last": ms[0]}


def events_of(fid, hid):
    ev = {"home": [], "away": [], "own": [], "cards": {"home": [0, 0], "away": [0, 0]}}
    for e in _get("fixtures/events", fixture=fid):
        t = e.get("time") or {}
        side = "home" if (e.get("team") or {}).get("id") == hid else "away"
        minute = f"{t.get('elapsed')}+{t['extra']}'" if t.get("extra") else f"{t.get('elapsed')}'"
        name = (e.get("player") or {}).get("name") or "Unknown"
        detail = e.get("detail") or ""
        if e.get("type") == "Goal":
            if detail == "Own Goal":
                ev["own"].append(f"{name} {minute}")
            elif detail != "Missed Penalty":
                ev[side].append(f"{name} {minute}" + (" (pen)" if detail == "Penalty" else ""))
        elif e.get("type") == "Card":
            if detail == "Yellow Card":
                ev["cards"][side][0] += 1
            elif "Red" in detail:
                ev["cards"][side][1] += 1
    return ev


def stats_of(fid, hid, aid):
    by = {
        t["team"]["id"]: {s["type"]: s["value"] for s in t.get("statistics", [])}
        for t in _get("fixtures/statistics", fixture=fid)
    }
    return (by[hid], by[aid]) if hid in by and aid in by else None


# ======================= HELPERS =======================
def fp(form):
    return sum({"W": 3, "D": 1}.get(c, 0) for c in (form or ""))


def num(x):
    if x is None:
        return 0
    if isinstance(x, str):
        try:
            return float(x.replace("%", ""))
        except ValueError:
            return 0
    return x


def fmt(x):
    return "0" if x is None else str(x).replace("%", "")


def plural(n, w):
    return f"{n} {w}" + ("" if n == 1 else "s")


def summ(gs):
    n = len(gs)
    if not n:
        return None
    s = {"n": n}
    s["w"] = sum(g["res"] == "W" for g in gs)
    s["d"] = sum(g["res"] == "D" for g in gs)
    s["l"] = n - s["w"] - s["d"]
    s["gf"] = sum(g["gf"] for g in gs)
    s["ga"] = sum(g["ga"] for g in gs)
    s["pts"] = s["w"] * 3 + s["d"]
    s["cs"] = sum(g["ga"] == 0 for g in gs)
    s["fts"] = sum(g["gf"] == 0 for g in gs)
    s["btts"] = sum(g["gf"] > 0 and g["ga"] > 0 for g in gs)
    s["o25"] = sum(g["gf"] + g["ga"] > 2 for g in gs)
    s["gfpg"] = round(s["gf"] / n, 2)
    s["gapg"] = round(s["ga"] / n, 2)
    s["ppg"] = round(s["pts"] / n, 2)
    s["form"] = "".join(g["res"] for g in gs[-5:])
    return s


def run(gs, fn):
    c = 0
    for g in reversed(gs):
        if not fn(g):
            break
        c += 1
    return c


def streak_line(name, gs):
    if len(gs) < 3:
        return ""
    wn = run(gs, lambda g: g["res"] == "W")
    un = run(gs, lambda g: g["res"] != "L")
    lo = run(gs, lambda g: g["res"] != "W")
    cs = run(gs, lambda g: g["ga"] == 0)
    sc = run(gs, lambda g: g["gf"] > 0)
    bits = []
    if wn >= 2:
        bits.append(f"{wn} straight wins")
    elif un >= 3:
        bits.append(f"a {un}-game unbeaten run")
    if lo >= 3:
        bits.append(f"{lo} games without a win")
    if cs >= 2:
        bits.append(f"{cs} clean sheets in a row")
    if sc >= 5:
        bits.append(f"a goal in each of their last {sc}")
    return f"Current streaks for {name}: " + ", ".join(bits) + "." if bits else ""


def last_results(gs, n=5):
    return "; ".join(
        f"{g['gf']}-{g['ga']} {'vs' if g['home'] else 'at'} {g['opp']} ({g['res']})"
        for g in gs[-n:][::-1]
    )


def form_para(name, gs, comp):
    s = summ(gs)
    if not s:
        return None
    k = len(s["form"])
    return (f"{name}'s last {k} results in the {comp}, newest first: {last_results(gs)}. "
            f"That is {fp(s['form'])} points from a possible {3 * k}.")


def venue_para(name, s, home=True):
    if not s:
        return None
    where = "at home" if home else "away from home"
    return (f"{name} have {s['w']} wins, {s['d']} draws and {s['l']} defeats {where} "
            f"({s['pts']} points from {s['n']} games, {s['ppg']} per game), scoring {s['gfpg']} "
            f"and conceding {s['gapg']} per game. They kept {plural(s['cs'], 'clean sheet')} "
            f"and failed to score in {s['fts']} of those {s['n']}.")


def leaders_line(code, tid, name):
    L = leaders(code)
    parts = [
        f"{x['name']} ({x['goals']} goals, number {x['rank']} in the scoring chart)"
        for x in [x for x in L["scorers"] if x["team_id"] == tid][:2]
    ] + [
        f"{x['name']} ({x['assists']} assists, number {x['rank']} in the assist chart)"
        for x in [x for x in L["assists"] if x["team_id"] == tid][:1]
    ]
    return f"{name}'s standout numbers: " + "; ".join(parts) + "." if parts else ""


def h2h_para(hn, an, h):
    if not h:
        return None
    last = h["last"]
    return (f"In their last {h['n']} meetings {hn} won {h['hw']}, {an} won {h['aw']} and {h['d']} "
            f"were drawn, averaging {h['avg']} goals per game. The most recent was "
            f"{last['text']} in the {last['comp']} ({last['year']}).")


def next_txt(code, tid):
    items = []
    for _, home, opp, oid in upcoming_of(code, tid, 3):
        r = row_of(code, oid)
        items.append(f"{'vs' if home else 'at'} {opp}" + (f" ({ordn(r['rank'])})" if r else ""))
    return ", ".join(items)


def edge(n1, n2, v1, v2, what, lower=False, unit=""):
    if v1 == v2:
        return f"{n1} and {n2} are level on {what} ({v1}{unit})."
    first = (v1 < v2) if lower else (v1 > v2)
    best, worst, hi, lo = (n1, n2, v1, v2) if first else (n2, n1, v2, v1)
    return f"{best} have the edge in {what}: {hi}{unit} against {lo}{unit} for {worst}."


def section(p, heading, *paras):
    paras = [x for x in paras if x]
    if paras:
        p.append(f"## {heading}")
        p.extend(paras)


def standing_para(hn, an, rh, ra, tb):
    top = tb[0]
    gap = abs(rh["points"] - ra["points"])
    hi, lo = (hn, an) if rh["rank"] < ra["rank"] else (an, hn)
    rel = (f"{hn} and {an} are level on points" if gap == 0
           else f"{hi} are {plural(gap, 'point')} ahead of {lo}")

    def behind(name, r):
        if r["rank"] == 1:
            return f"{name} lead the table"
        return f"{name} trail the leaders {top['team']['name']} by {top['points'] - r['points']}"

    return (f"{hn} are {ordn(rh['rank'])} on {rh['points']} points (goal difference "
            f"{rh.get('goalsDiff', 0):+d}) and {an} are {ordn(ra['rank'])} on {ra['points']} "
            f"({ra.get('goalsDiff', 0):+d}); {rel}. {behind(hn, rh)}, while {behind(an, ra)}.")


def outlook_para(hn, an, hh, aa):
    if not hh or not aa:
        return None
    eh = (hh["gfpg"] + aa["gapg"]) / 2
    ea = (aa["gfpg"] + hh["gapg"]) / 2
    return (f"Blending {hn}'s home scoring rate ({hh['gfpg']}) with {an}'s away conceding rate "
            f"({aa['gapg']}) gives about {eh:.1f} goals for {hn}; the reverse calculation gives "
            f"{ea:.1f} for {an}, a combined {eh + ea:.1f}. Both teams scored in {hh['btts']} of "
            f"{hn}'s {hh['n']} home games and {aa['btts']} of {an}'s {aa['n']} away games, and "
            f"over 2.5 goals appeared in {hh['o25']} and {aa['o25']} of them. These are "
            f"season-average calculations, not a forecast.")


def verdict_para(hn, an, sh, sa, hh, aa):
    fh, fa = fp(sh["form"]), fp(sa["form"])
    if fh - fa >= 4:
        lean = f"recent form favours {hn} ({fh} points from the last five against {fa})"
    elif fa - fh >= 4:
        lean = f"recent form favours {an} ({fa} points from the last five against {fh})"
    else:
        lean = f"the form lines are close ({hn} {fh} points, {an} {fa})"
    txt = f"On the numbers, {lean}."
    if hh and aa:
        diff = hh["ppg"] - aa["ppg"]
        tilt = (f"tilts the balance toward {hn}" if diff > 0.5
                else f"tilts toward {an}" if diff < -0.5 else "keeps the contest balanced")
        txt += (f" {hn} collect {hh['ppg']} points per home game while {an} take {aa['ppg']} "
                f"per away game, which {tilt}.")
    return txt


def goals_para(hn, an, ev, hgl, agl):
    if hgl + agl == 0:
        return "Neither side found the net."
    bits = []
    if ev["home"]:
        bits.append(f"{hn} scorers: " + ", ".join(ev["home"]))
    if ev["away"]:
        bits.append(f"{an} scorers: " + ", ".join(ev["away"]))
    if ev["own"]:
        bits.append("Own goals: " + ", ".join(ev["own"]))
    return ". ".join(bits) + "." if bits else None


def cards_para(hn, an, ev):
    (hy, hr), (ay, ar) = ev["cards"]["home"], ev["cards"]["away"]
    if not (hy or hr or ay or ar):
        return None
    return f"Discipline: {hn} collected {hy} yellow and {hr} red; {an} collected {ay} yellow and {ar} red."


def stats_para(hn, an, st, hgl, agl):
    if not st:
        return None
    h, a = st
    rows = [("possession", "Ball Possession", "%"), ("total shots", "Total Shots", ""),
            ("shots on target", "Shots on Goal", ""), ("corners", "Corner Kicks", ""),
            ("fouls", "Fouls", ""), ("expected goals", "expected_goals", "")]
    bits = [f"{lab} {hn} {fmt(h.get(k))}{suf} - {fmt(a.get(k))}{suf} {an}"
            for lab, k, suf in rows if h.get(k) is not None or a.get(k) is not None]
    if not bits:
        return None
    txt = "Match numbers: " + "; ".join(bits) + "."
    ph, pa = num(h.get("Ball Possession")), num(a.get("Ball Possession"))
    if ph and pa and hgl != agl:
        lead = hn if ph > pa else an
        win = hn if hgl > agl else an
        if lead != win:
            txt += (f" {lead} had more of the ball ({max(ph, pa):.0f}%) but {win} took the points, "
                    f"a reminder that possession is not the same as chances.")
    return txt


def _save(kind, key, title, summary, paras, image="", code="", obj=None):
    if obj is None:
        if AnalysisArticle.objects.filter(key=key).exists():
            return None
        return AnalysisArticle.objects.create(
            kind=kind, key=key, slug=f"{slugify(title)[:120]}-{slugify(key)[:40]}",
            title=title, summary=summary[:400], paragraphs=paras,
            image_url=image or "", league_code=code,
        )
    obj.title, obj.summary, obj.paragraphs = title, summary[:400], paras
    obj.image_url = image or obj.image_url
    obj.save()
    return obj


# ======================= MATCH (preview -> report) =======================
def match_article(m, group):
    st = m["status"]
    mode = "preview" if st in ("NS", "TBD") else ("report" if st in DONE else None)
    if not mode:
        return None

    key = f"tp-{m['id']}"
    old = AnalysisArticle.objects.filter(key=key).first()
    if old and not (mode == "report" and " vs " in old.title):
        return None

    code, comp = group["code"], group["name"]
    H, A = m["homeTeam"], m["awayTeam"]
    hn, an = H["name"], A["name"]
    gh, ga_ = games_of(code, H["id"]), games_of(code, A["id"])
    if len(gh) < 3 or len(ga_) < 3:
        return None

    sh, sa = summ(gh), summ(ga_)
    hh = summ([g for g in gh if g["home"]])
    aa = summ([g for g in ga_ if not g["home"]])
    tb = table(code)
    rh, ra = row_of(code, H["id"]), row_of(code, A["id"])
    both = bool(rh and ra and tb)
    p = []

    if mode == "preview":
        when = v.to_mecca_time(m.get("utcDate"))
        when_txt = (when.strftime("%A %d %B, %H:%M") + " (Mecca time)") if when else "today"
        intro = f"{hn} host {an} in the {comp} on {when_txt}."
        if both:
            intro += f" The hosts are {ordn(rh['rank'])} in the table and the visitors {ordn(ra['rank'])}."
        p.append(intro + f" This preview uses the season's {comp} results to compare how both sides "
                         f"score, defend and perform at home and away.")
        if both:
            section(p, "Where the two sides stand", standing_para(hn, an, rh, ra, tb))
        section(p, f"{hn} at home", venue_para(hn, hh, True), streak_line(hn, gh))
        section(p, f"{an} away from home", venue_para(an, aa, False), streak_line(an, ga_))
        section(p, "Recent form", form_para(hn, gh, comp), form_para(an, ga_, comp))
        section(p, "Key players", leaders_line(code, H["id"], hn), leaders_line(code, A["id"], an))
        section(p, "Head-to-head", h2h_para(hn, an, h2h_info(H["id"], A["id"])))
        section(p, "Goals outlook", outlook_para(hn, an, hh, aa))
        section(p, "Our read", verdict_para(hn, an, sh, sa, hh, aa))
        title = f"{hn} vs {an}: {comp} Preview, Form and Key Stats"
        summary = (f"{hn} vs {an} in the {comp}: home and away records, recent form, "
                   f"head-to-head and a data-based goal outlook.")
    else:
        hgl, agl = m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"]
        if hgl is None or agl is None:
            return None
        if hgl > agl:
            res = f"{hn} beat {an} {hgl}-{agl}"
        elif agl > hgl:
            res = f"{an} won {agl}-{hgl} away at {hn}"
        else:
            res = f"{hn} and {an} drew {hgl}-{agl}"
        intro = f"{res} in the {comp}."
        if both:
            intro += (f" The result leaves {hn} {ordn(rh['rank'])} on {rh['points']} points "
                      f"and {an} {ordn(ra['rank'])} on {ra['points']}.")
        p.append(intro)
        ev = events_of(m["id"], H["id"])
        section(p, "How the goals came", goals_para(hn, an, ev, hgl, agl), cards_para(hn, an, ev))
        section(p, "Match statistics", stats_para(hn, an, stats_of(m["id"], H["id"], A["id"]), hgl, agl))
        if both:
            section(p, "What the result means", standing_para(hn, an, rh, ra, tb),
                    streak_line(hn, gh), streak_line(an, ga_))
        nh, na = next_txt(code, H["id"]), next_txt(code, A["id"])
        section(p, "What comes next",
                f"{hn}'s next games: {nh}." if nh else "",
                f"{an}'s next games: {na}." if na else "")
        section(p, "Head-to-head", h2h_para(hn, an, h2h_info(H["id"], A["id"])))
        title = f"{hn} {hgl}-{agl} {an}: Match Analysis"
        summary = intro

    return _save("match", key, title, summary, p, H["crest"], code, obj=old)


# ======================= ROUND =======================
def round_article(code):
    league = v.LEAGUES[code]["name"]
    rounds = {}
    for f in league_fixtures(code):
        rn = f["league"].get("round") or ""
        if not rn.startswith("Regular Season"):
            continue
        try:
            rounds.setdefault(int(rn.split("-")[-1]), []).append(f)
        except ValueError:
            continue

    best = None
    for n in sorted(rounds):
        fin = [f for f in rounds[n] if f["fixture"]["status"]["short"] in DONE]
        if fin and len(fin) >= 0.8 * len(rounds[n]):
            best = n
    if best is None:
        return None

    key = f"round_{code}_{best}"
    if AnalysisArticle.objects.filter(key=key).exists():
        return None

    sc = []
    for f in rounds[best]:
        g = f["goals"]
        if f["fixture"]["status"]["short"] in DONE and g["home"] is not None and g["away"] is not None:
            t = f["teams"]
            sc.append((v.clean_team_name(t["home"]["name"]), t["home"]["id"], g["home"],
                       v.clean_team_name(t["away"]["name"]), t["away"]["id"], g["away"]))
    if not sc:
        return None

    k = len(sc)
    total = sum(x[2] + x[5] for x in sc)
    avg = total / k
    season_avg = league_avg(code)
    home_w = sum(x[2] > x[5] for x in sc)
    away_w = sum(x[5] > x[2] for x in sc)
    draws = k - home_w - away_w
    clean = sum((x[2] == 0) + (x[5] == 0) for x in sc)
    btts = sum(x[2] > 0 and x[5] > 0 for x in sc)
    o25 = sum(x[2] + x[5] > 2 for x in sc)
    big = max(sc, key=lambda x: abs(x[2] - x[5]))
    top = max(sc, key=lambda x: x[2] + x[5])
    tb = table(code)

    p = [f"Matchday {best} of the {league} brought {total} goals in {k} games, an average of "
         f"{avg:.2f} per match against a season average of {season_avg:.2f}. "
         + ("Goals ran above the usual rate." if avg > season_avg + 0.2
            else "Goals ran below the usual rate." if avg < season_avg - 0.2
            else "Scoring stayed close to the season norm.")]

    section(p, "Results", "; ".join(f"{a} {hg}-{ag} {b}" for a, _, hg, b, _, ag in sc) + ".")

    stand = []
    if big[2] != big[5]:
        stand.append(f"The widest margin was {big[0]} {big[2]}-{big[5]} {big[3]}.")
    if top[2] + top[5] >= 4:
        stand.append(f"The highest-scoring game was {top[0]} {top[2]}-{top[5]} {top[3]}.")
    ups = []
    for a, aid, hg, b, bid, ag in sc:
        ra, rb = row_of(code, aid), row_of(code, bid)
        if not (ra and rb) or hg == ag:
            continue
        w, l, wr, lr = (a, b, ra["rank"], rb["rank"]) if hg > ag else (b, a, rb["rank"], ra["rank"])
        if wr - lr >= 6:
            ups.append(f"{w} ({ordn(wr)}) beat {l} ({ordn(lr)})")
    if ups:
        stand.append("Biggest surprises by current table position: " + "; ".join(ups[:2]) + ".")
    section(p, "Standout moments", *stand)

    section(p, "Home advantage and defences",
            f"Home sides won {home_w}, away sides won {away_w} and {draws} ended level. "
            f"Teams kept {clean} clean sheets, both teams scored in {btts} of {k} games and "
            f"{o25} of them had more than 2.5 goals.")

    if len(tb) >= 3:
        lead, second, last = tb[0], tb[1], tb[-1]
        gap = lead["points"] - second["points"]
        form_best = max(tb, key=lambda r: fp(r.get("form")))
        section(p, "The table after the round",
                f"{lead['team']['name']} lead on {lead['points']} points, "
                + (f"{gap} clear of {second['team']['name']}." if gap else f"level with {second['team']['name']}.")
                + f" {last['team']['name']} are bottom on {last['points']}. "
                f"The best recent form belongs to {form_best['team']['name']} "
                f"({form_best.get('form')}: {fp(form_best.get('form'))} points from five).")

    sc_top = leaders(code)["scorers"][:3]
    if sc_top:
        section(p, "The scoring race",
                "Top scorers: " + "; ".join(f"{x['name']} ({x['team']}) {x['goals']}" for x in sc_top) + ".")

    return _save("round", key, f"{league} Matchday {best} Analysis: {total} Goals and {home_w} Home Wins",
                 p[0], p, v.LEAGUES[code]["logo"], code)


# ======================= TEAM =======================
def team_article(code, row):
    league = v.LEAGUES[code]["name"]
    t = row["team"]
    tid, name = t["id"], t["name"]
    gs = games_of(code, tid)
    n = len(gs)
    if n < 3:
        return None
    key = f"team_{tid}_{n}"
    if AnalysisArticle.objects.filter(key=key).exists():
        return None

    tb = table(code)
    s = summ(gs)
    hh = summ([g for g in gs if g["home"]])
    aa = summ([g for g in gs if not g["home"]])
    per_team = league_avg(code) / 2

    def rank_by(fn, rev):
        order = sorted(tb, key=fn, reverse=rev)
        return next((i for i, r in enumerate(order, 1) if r["team"]["id"] == tid), None)

    def goals_of(r, k):
        return ((r.get("all") or {}).get("goals") or {}).get(k, 0)

    gf_rank = rank_by(lambda r: goals_of(r, "for"), True)
    ga_rank = rank_by(lambda r: goals_of(r, "against"), False)

    p = [f"{name} are {ordn(row['rank'])} in the {league} with {row['points']} points from {n} games "
         f"({s['w']}W {s['d']}D {s['l']}L) and a goal difference of {row.get('goalsDiff', 0):+d}."]

    pct = round((s["gfpg"] / per_team - 1) * 100) if per_team else 0
    section(p, "Attack",
            f"{name} have scored {s['gf']} goals ({s['gfpg']} per game), the {ordn(gf_rank)}-best attack "
            f"in the {league}. The league average is {per_team:.2f} per team per game, so they sit "
            f"{abs(pct)}% {'above' if pct >= 0 else 'below'} it. They failed to score in {s['fts']} of {n} games.")
    section(p, "Defence",
            f"They have conceded {s['ga']} ({s['gapg']} per game), the {ordn(ga_rank)}-best defence, "
            f"with {plural(s['cs'], 'clean sheet')} in {n} games.")
    section(p, "Home and away", venue_para(name, hh, True), venue_para(name, aa, False))
    section(p, "Form and streaks", form_para(name, gs, league), streak_line(name, gs))
    section(p, "Key players", leaders_line(code, tid, name))

    ups = upcoming_of(code, tid, 3)
    if ups:
        ranks = [r["rank"] for r in (row_of(code, u[3]) for u in ups) if r]
        extra = ""
        if len(ranks) == len(ups):
            avg_rank = sum(ranks) / len(ranks)
            extra = (f" The average league position of those opponents is {avg_rank:.1f}, "
                     + ("a demanding run." if avg_rank <= 7 else "a kinder run." if avg_rank >= 13 else "a mixed run."))
        section(p, "The schedule ahead", f"Next up: {next_txt(code, tid)}.{extra}")

    total_games = 2 * (len(tb) - 1)
    section(p, "Outlook",
            f"At {s['ppg']} points per game, a full {total_games}-game season would end near "
            f"{round(s['ppg'] * total_games)} points. That is a projection from the current rate, not a prediction.")

    return _save("team", key,
                 f"{name} {league} Analysis: {ordn(row['rank'])} Place, {row['points']} Points After {n} Games",
                 p[0], p, t["logo"], code)


# ======================= COMPARE =======================
def compare_article(code, r1, r2):
    league = v.LEAGUES[code]["name"]
    t1, t2 = r1["team"], r2["team"]
    n1, n2 = t1["name"], t2["name"]
    g1, g2 = games_of(code, t1["id"]), games_of(code, t2["id"])
    if len(g1) < 3 or len(g2) < 3:
        return None
    key = f"compare_{t1['id']}_{t2['id']}_{len(g1)}"
    if AnalysisArticle.objects.filter(key=key).exists():
        return None

    s1, s2 = summ(g1), summ(g2)
    h1, a1 = summ([g for g in g1 if g["home"]]), summ([g for g in g1 if not g["home"]])
    h2, a2 = summ([g for g in g2 if g["home"]]), summ([g for g in g2 if not g["home"]])
    gap = abs(r1["points"] - r2["points"])

    p = [f"{n1} are {ordn(r1['rank'])} in the {league} with {r1['points']} points and {n2} are "
         f"{ordn(r2['rank'])} with {r2['points']}"
         + (f", a gap of {plural(gap, 'point')}." if gap else ", level on points.")]

    section(p, "Record and efficiency",
            f"{n1}: {s1['w']}W {s1['d']}D {s1['l']}L in {s1['n']} games. "
            f"{n2}: {s2['w']}W {s2['d']}D {s2['l']}L in {s2['n']} games.",
            edge(n1, n2, s1["ppg"], s2["ppg"], "points per game"))
    section(p, "Attack and defence",
            edge(n1, n2, s1["gfpg"], s2["gfpg"], "goals scored per game"),
            edge(n1, n2, s1["gapg"], s2["gapg"], "goals conceded per game", lower=True),
            edge(n1, n2, s1["cs"], s2["cs"], "clean sheets"))
    if h1 and a1 and h2 and a2:
        section(p, "Home and away",
                f"{n1} take {h1['ppg']} points per home game and {a1['ppg']} away; "
                f"{n2} take {h2['ppg']} at home and {a2['ppg']} away.")
    section(p, "Form", form_para(n1, g1, league), form_para(n2, g2, league))
    section(p, "Key players", leaders_line(code, t1["id"], n1), leaders_line(code, t2["id"], n2))
    section(p, "History between them", h2h_para(n1, n2, h2h_info(t1["id"], t2["id"])))

    if s1["ppg"] == s2["ppg"]:
        verdict = "The two are level on points per game this season."
    else:
        better = n1 if s1["ppg"] > s2["ppg"] else n2
        verdict = f"Season-long numbers favour {better} on points per game ({s1['ppg']} against {s2['ppg']})."
    section(p, "Verdict",
            f"{verdict} Recent form gives {n1} {fp(s1['form'])} points from the last five and "
            f"{n2} {fp(s2['form'])}.")

    label = "Title Race" if r1["rank"] <= 2 and r2["rank"] <= 2 else "Rivalry"
    return _save("compare", key, f"{n1} vs {n2}: {league} {label} Compared", p[0], p, t1["logo"], code)


# ======================= RUN =======================
def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        print("analysis error:", fn.__name__, repr(e))
        return None


def run_all():
    _FIX.clear()
    _TABLE.clear()
    _LEAD.clear()
    made = []

    for code in LEAGUE_CODES:
        made.append(_safe(round_article, code))
        tb = table(code)
        if len(tb) < 6:
            continue

        done = []
        picks = tb[:1] + [r for r in tb if r["team"]["id"] in PRIORITY_IDS]
        picks.append(max(tb, key=lambda r: fp(r.get("form"))))
        for r in picks:
            if r["team"]["id"] not in done:
                done.append(r["team"]["id"])
                made.append(_safe(team_article, code, r))

        made.append(_safe(compare_article, code, tb[0], tb[1]))
        if code == "PD":
            a, b = row_of(code, 529), row_of(code, 541)
            if a and b:
                made.append(_safe(compare_article, code, a, b))
        if code == "PL":
            liv = row_of(code, 40)
            if liv and liv["rank"] > 1:
                made.append(_safe(compare_article, code, liv, tb[0]))

    today = date.today()
    for offset in (0, 1):
        grouped = v.get_today_matches(today + timedelta(days=offset))
        used = 0
        for _, m, group in v.ranked_today_matches(grouped):
            if used >= 10:
                break
            ids = {m["homeTeam"]["id"], m["awayTeam"]["id"]}
            if group["code"] not in MATCH_CODES and not (ids & PRIORITY_IDS):
                continue
            made.append(_safe(match_article, m, group))
            used += 1

    return [x for x in made if x]