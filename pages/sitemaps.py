from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.core.cache import cache

from .models import NewsArticle
from .views import (
    LEAGUES,
    get_matches,
    get_current_matchday,
    get_cup_rounds,
    get_current_round_index,
    get_standings
)


# =========================================================
# المنافسات
# =========================================================

MAJOR_LEAGUES = [
    "PL",
    "PD",
    "SA",
    "BL1",
    "FL1",
]

DOMESTIC_CUPS = [
    "FAC",
    "ELCUP",
    "CDR",
    "SC",
    "COP",
    "DSC",
    "DFB",
    "DSUP",
    "CDF",
    "TDC",
]

EUROPEAN_CUPS = [
    "UCL",
    "UEL",
    "UECL",
]

ALL_CUPS = DOMESTIC_CUPS + EUROPEAN_CUPS

ALL_COMPETITIONS = MAJOR_LEAGUES + ALL_CUPS


# =========================================================
# الصفحات الثابتة
# =========================================================

class StaticViewSitemap(Sitemap):

    priority = 0.8
    changefreq = "daily"

    def items(self):
        return [
            "matches",
            "premier_league_home",
            "standings",
            "leaderboard",
            "news_list",
            "privacy_policy",
            "about_us",
            "contact_us",
        ]

    def location(self, item):
        return reverse(item)


# =========================================================
# صفحات البطولات - الدوريات الخمسة
# =========================================================

class CompetitionSitemap(Sitemap):

    priority = 0.9
    changefreq = "daily"

    def items(self):
        return MAJOR_LEAGUES

    def location(self, item):
        return reverse("competition", args=[item])


# =========================================================
# صفحات الكؤوس والبطولات الأوروبية
# =========================================================

class CupCompetitionSitemap(Sitemap):

    priority = 0.9
    changefreq = "daily"

    def items(self):
        return ALL_CUPS

    def location(self, item):
        return reverse("cup_competition", args=[item])


# =========================================================
# مباريات الدوريات الخمسة
#
# من الجولة 1
# إلى الجولة الحالية + جولتين قادمتين
# =========================================================

class LeagueMatchSitemap(Sitemap):

    priority = 0.9
    changefreq = "hourly"

    def items(self):

        match_ids = []

        for code in MAJOR_LEAGUES:

            cache_key = f"sitemap_matches_{code}"

            cached_ids = cache.get(cache_key)

            if cached_ids is not None:
                match_ids.extend(cached_ids)
                continue

            code_ids = []

            try:
                current_matchday = get_current_matchday(code)
            except Exception:
                current_matchday = 1

            # الجولة الحالية + جولتين قادمتين
            end_matchday = current_matchday + 2

            for matchday in range(1, end_matchday + 1):

                if matchday < 1:
                    continue

                try:
                    competition, matches = get_matches(
                        code,
                        matchday
                    )

                    code_ids.extend(
                        match["id"]
                        for match in matches
                    )

                except Exception:
                    continue

            # كاش لمدة 6 ساعات
            cache.set(
                cache_key,
                code_ids,
                60 * 60 * 6
            )

            match_ids.extend(code_ids)

        return match_ids

    def location(self, item):
        return reverse(
            "match_detail",
            args=[item]
        )


# =========================================================
# مباريات الكؤوس والبطولات الأوروبية
#
# من أول دور موجود
# إلى الدور الحالي + دورين قادمين
# =========================================================

class CupMatchSitemap(Sitemap):

    priority = 0.9
    changefreq = "hourly"

    def items(self):

        match_ids = []

        for code in ALL_CUPS:

            cache_key = f"sitemap_cup_matches_{code}"

            cached_ids = cache.get(cache_key)

            if cached_ids is not None:
                match_ids.extend(cached_ids)
                continue

            code_ids = []

            try:
                rounds = get_cup_rounds(code)

                if not rounds:
                    continue

                current_round_index = get_current_round_index(
                    rounds
                )

                # نضمن عدم الخروج عن حدود القائمة
                if current_round_index < 0:
                    current_round_index = 0

                # أول دور
                # حتى الحالي + دورين قادمين
                end_index = min(
                    current_round_index + 3,
                    len(rounds)
                )

                selected_rounds = rounds[:end_index]

                for round_data in selected_rounds:

                    matches = round_data.get(
                        "matches",
                        []
                    )

                    for match in matches:

                        match_id = match.get("id")

                        if match_id:
                            code_ids.append(match_id)

            except Exception:
                continue

            # منع التكرار
            code_ids = list(dict.fromkeys(code_ids))

            # كاش لمدة 6 ساعات
            cache.set(
                cache_key,
                code_ids,
                60 * 60 * 6
            )

            match_ids.extend(code_ids)

        # منع أي تكرار بين المنافسات
        return list(dict.fromkeys(match_ids))

    def location(self, item):
        return reverse(
            "match_detail",
            args=[item]
        )


# =========================================================
# ترتيب الدوريات الخمسة
# =========================================================

class LeagueStandingsSitemap(Sitemap):

    priority = 0.85
    changefreq = "daily"

    def items(self):
        return MAJOR_LEAGUES

    def location(self, item):
        return reverse(
            "competition_standings",
            args=[item]
        )


# =========================================================
# ترتيب دوري أبطال أوروبا + الدوري الأوروبي
# + دوري المؤتمر
# =========================================================

class EuropeanStandingsSitemap(Sitemap):

    priority = 0.85
    changefreq = "daily"

    def items(self):
        return EUROPEAN_CUPS

    def location(self, item):
        return reverse(
            "competition_standings",
            args=[item]
        )


# =========================================================
# إحصائيات جميع المنافسات الـ 18
# =========================================================

class CompetitionStatisticsSitemap(Sitemap):

    priority = 0.8
    changefreq = "daily"

    def items(self):
        return ALL_COMPETITIONS

    def location(self, item):
        return reverse(
            "league_statistics",
            args=[item]
        )


# =========================================================
# تاريخ الدوريات الخمسة
# =========================================================

class CompetitionHistorySitemap(Sitemap):

    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return MAJOR_LEAGUES

    def location(self, item):
        return reverse(
            "league_history",
            args=[item]
        )


# =========================================================
# أخبار الموقع
# =========================================================

class NewsArticleSitemap(Sitemap):

    priority = 0.8
    changefreq = "daily"

    def items(self):
        return NewsArticle.objects.all()

    def location(self, obj):
        return reverse(
            "news_detail",
            args=[obj.id]
        )


class TeamSitemap(Sitemap):

    priority = 0.8
    changefreq = "daily"

    def items(self):

        team_ids = []

        for code in MAJOR_LEAGUES:

            try:
                table = get_standings(code)

                for row in table:

                    team = row.get("team", {})
                    team_id = team.get("id")

                    if team_id:
                        team_ids.append(team_id)

            except Exception:
                continue

        return list(dict.fromkeys(team_ids))

    def location(self, item):
        return reverse(
            "team_detail",
            args=[item]
        )