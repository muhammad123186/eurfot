from django.core.management.base import BaseCommand
from pages.models import NewsArticle
from pages.views import LEAGUES, get_standings, _fetch_top_player

CODES = ["PL", "PD", "SA", "BL1", "FL1"]


class Command(BaseCommand):
    help = "Generate data-driven articles"

    def handle(self, *args, **opts):
        for code in CODES:
            table = get_standings(code)
            if len(table) < 6:
                continue
            played = table[0]["all"]["played"]
            if played < 3:
                continue
            self.title_race(code, table, played)

    def title_race(self, code, table, played):
        league = LEAGUES[code]["name"]
        first, second = table[0], table[1]
        gap = first["points"] - second["points"]
        fname, sname = first["team"]["name"], second["team"]["name"]

        if gap > 0:
            title = f"{league}: {fname} lead by {gap} points after {played} games"
        else:
            title = f"{league}: {fname} and {sname} level at the top after {played} games"

        if NewsArticle.objects.filter(title=title).exists():
            return

        a = first["all"]
        paras = [
            f"{fname} sit top of the {league} with {first['points']} points from {played} games "
            f"({a['win']}W {a['draw']}D {a['lose']}L), scoring {a['goals']['for']} "
            f"and conceding {a['goals']['against']}. Their recent form reads {first.get('form') or 'n/a'}.",
            f"{sname} are {'level with them' if gap == 0 else str(gap) + ' points behind'} "
            f"on {second['points']} points, with a goal difference of {second['goalsDiff']:+d}.",
        ]

        top4 = table[3]
        paras.append(
            f"The race for the top four is tight: {top4['team']['name']} hold fourth "
            f"on {top4['points']} points."
        )

        bottom = table[-3:]
        paras.append(
            "At the bottom, "
            + ", ".join(f"{r['team']['name']} ({r['points']} pts)" for r in bottom)
            + " occupy the relegation places."
        )

        scorer = _fetch_top_player("topscorers", LEAGUES[code]["id"])
        if scorer:
            paras.append(
                f"In the scoring charts, {scorer['name']} ({scorer['team_name']}) "
                f"leads with {scorer['goals']} goals."
            )

        NewsArticle.objects.create(
            title=title,
            summary=paras[0],
            content="\n\n".join(paras),
            image_url=first["team"]["logo"],
            league_code=code,
        )