import requests
from collections import defaultdict
from django.shortcuts import render
from django.core.cache import cache
from collections import Counter
from django.contrib.auth import login
from .forms import SignUpForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Prediction
import requests
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q
from django.shortcuts import render, get_object_or_404
from .models import NewsArticle
from django.shortcuts import render, redirect, get_object_or_404
from .models import FanTeamOfWeek, FanTeamPlayer
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from .models import Player
from django.http import Http404
from datetime import datetime
from django.conf import settings
import time



from zoneinfo import ZoneInfo

MECCA_TZ = ZoneInfo("Asia/Riyadh")


def to_mecca_time(iso_date_string):
    if not iso_date_string:
        return None
    try:
        dt = datetime.fromisoformat(iso_date_string.replace("Z", "+00:00"))
        mecca_dt = dt.astimezone(MECCA_TZ)
        return mecca_dt.replace(tzinfo=None)  # نشيل معلومة المنطقة الزمنية حتى ما يعيد Django تحويلها
    except (ValueError, TypeError):
        return None


# ================= CACHE DURATION =================
# مدة موحدة افتراضية لبقية الكاش بالمشروع: 24 ساعة بالثواني
CACHE_TTL = 60 * 60 * 24


# ================= SPECIFIC CACHE TTLs (حسب طلب التحديث) =================
MATCHES_CACHE_TTL = 90                  # جدول مباريات الدوريات والكؤوس - دقيقة واحدة
TEAM_DETAIL_CACHE_TTL = 60 * 45         # صفحة تفاصيل الفريق - 45 دقيقة
PLAYER_DETAIL_CACHE_TTL = 60 * 60       # صفحة تفاصيل اللاعب - ساعة واحدة
STANDINGS_CACHE_TTL = 60 * 10           # جدول الترتيب لكل البطولات - 10 دقائق
LEAGUE_STATS_CACHE_TTL = 60 * 30        # صفحة إحصائيات كل بطولة - نصف ساعة


# ================= API =================


headers = {
    "x-apisports-key":  settings.API_SPORTS_KEY
}



SEASON = 2026



# ================= LEAGUES =================

LEAGUES = {
    # ------------------ LEAGUES ------------------
    "PL": {
        "id": 39,
        "name": "Premier League",
        "logo": "https://media.api-sports.io/football/leagues/39.png",
        "max_matchday": 38,
        "template": "pages/index.html",
        "standings_template": "pages/standings.html",
    },
    "PD": {
        "id": 140,
        "name": "La Liga",
        "logo": "https://media.api-sports.io/football/leagues/140.png",
        "max_matchday": 38,
        "template": "pages/laliga.html",
        "standings_template": "pages/standings_laliga.html",
    },
    "SA": {
        "id": 135,
        "name": "Serie A",
        "logo": "https://media.api-sports.io/football/leagues/135.png",
        "max_matchday": 38,
        "template": "pages/serie_a.html",
        "standings_template": "pages/standings_seriea.html",
    },
    "BL1": {
        "id": 78,
        "name": "Bundesliga",
        "logo": "https://media.api-sports.io/football/leagues/78.png",
        "max_matchday": 34,
        "template": "pages/bundesliga.html",
        "standings_template": "pages/standings_bundesliga.html",
    },
    "FL1": {
        "id": 61,
        "name": "Ligue 1",
        "logo": "https://media.api-sports.io/football/leagues/61.png",
        "max_matchday": 34,
        "template": "pages/ligue1.html",
        "standings_template": "pages/standings_ligue1.html",
    },

    # ------------------ CUPS ------------------
    "FAC": {
        "id": 45,
        "code": "FAC",
        "name": "FA Cup",
        "logo": "https://media.api-sports.io/football/leagues/45.png",
        "country": "England",
        "type": "cup",
        "theme": "red",
        "theme_color": "#e10600",
        "template": "pages/cup_competition.html",
    },
    "ELCUP": {
        "id": 48,
        "code": "ELCUP",
        "name": "EFL Cup",
        "logo": "https://media.api-sports.io/football/leagues/48.png",
        "country": "England",
        "type": "cup",
        "theme": "green",
        "theme_color": "#00875a",
        "template": "pages/cup_competition.html",
    },
    "CDR": {
        "id": 143,
        "code": "CDR",
        "name": "Copa del Rey",
        "logo": "https://media.api-sports.io/football/leagues/143.png",
        "theme_color": "#d4af37",
        "template": "pages/cup_competition.html",
    },
    "SC": {
        "id": 556,
        "code": "SC",
        "name": "Supercopa de España",
        "logo": "https://media.api-sports.io/football/leagues/556.png",
        "theme_color": "#0055a5",
        "template": "pages/cup_competition.html",
    },
    "COP": {
        "id": 137,
        "code": "COP",
        "name": "Coppa Italia",
        "logo": "https://media.api-sports.io/football/leagues/137.png",
        "theme_color": "#001f3f",
        "template": "pages/cup_competition.html",
    },
    "DSC": {
        "id": 547,
        "code": "DSC",
        "name": "Supercoppa Italiana",
        "logo": "https://media.api-sports.io/football/leagues/547.png",
        "theme_color": "#d4af37",
        "template": "pages/cup_competition.html",
    },
    "DFB": {
        "id": 81,
        "code": "DFB",
        "name": "DFB Pokal",
        "logo": "https://media.api-sports.io/football/leagues/81.png",
        "theme_color": "#00853e",
        "template": "pages/cup_competition.html",
    },
    "DSUP": {
        "id": 529,
        "code": "DSUP",
        "name": "DFL Super Cup",
        "logo": "https://media.api-sports.io/football/leagues/529.png",
        "theme_color": "#d00000",
        "template": "pages/cup_competition.html",
    },
    "CDF": {
        "id": 66,
        "code": "CDF",
        "name": "Coupe de France",
        "logo": "https://media.api-sports.io/football/leagues/66.png",
        "theme_color": "#051c2c",
        "template": "pages/cup_competition.html",
    },
    "TDC": {
        "id": 526,
        "code": "TDC",
        "name": "des Champions",
        "logo": "https://media.api-sports.io/football/leagues/526.png",
        "theme_color": "#00a8cc",
        "template": "pages/cup_competition.html",
    },



    "UCL": {
        "id": 2,
        "code": "UCL",
        "name": "UEFA Champions League",
        "logo": "https://media.api-sports.io/football/leagues/2.png",
        "country": "Europe",
        "type": "cup",
        "theme_color": "#0e1a78",
        "template": "pages/cup_competition_eur.html",
        "standings_template": "pages/standings_eur.html",
    },


    "UEL": {
        "id": 3,
        "code": "UEL",
        "name": "UEFA Europa League",
        "logo": "https://media.api-sports.io/football/leagues/3.png",
        "country": "Europe",
        "type": "cup",
        "theme_color": "#e96b00",
        "template": "pages/cup_competition_eur.html",
        "standings_template": "pages/standings_eur.html",
    },


    "UECL": {
        "id": 848,
        "code": "UECL",
        "name": "UEFA Europa Conference League",
        "logo": "https://media.api-sports.io/football/leagues/848.png",
        "country": "Europe",
        "type": "cup",
        "theme_color": "#00a650",
        "template": "pages/cup_competition_eur.html",
        "standings_template": "pages/standings_eur.html",
    },
}


# ================= CUP THEMES =================
CUP_THEMES = {
    "FAC": {"theme": "#6b6b6b", "color": "#6b6b6b"},
    "ELCUP": {"theme": "green", "color": "#00875a"},
    "CDR": {"theme": "gold", "color": "#d4af37"},
    "SC": {"theme": "blue", "color": "#0055a5"},
    "COP": {"theme": "navy", "color": "#001f3f"},
    "DSC": {"theme": "gold", "color": "#d4af37"},
    "DFB": {"theme": "green", "color": "#00853e"},
    "DSUP": {"theme": "red", "color": "#d00000"},
    "CDF": {"theme": "blue", "color": "#051c2c"},
    "TDC": {"theme": "cyan", "color": "#00a8cc"},
}


# ================= TROPHY LOGOS =================
TROPHY_LOGOS = {

    "Premier League":
    "https://media.api-sports.io/football/leagues/39.png",

    "FA Cup":
    "https://media.api-sports.io/football/leagues/45.png",

    "League Cup":
    "https://media.api-sports.io/football/leagues/48.png",

    "UEFA Champions League":
    "https://media.api-sports.io/football/leagues/2.png",

    "UEFA Europa League":
    "https://media.api-sports.io/football/leagues/3.png",

    "UEFA Conference League":
    "https://media.api-sports.io/football/leagues/848.png",

    "UEFA Super Cup":
    "https://media.api-sports.io/football/leagues/531.png",

    "FIFA Club World Cup":
    "https://media.api-sports.io/football/leagues/15.png",

    "UEFA Cup Winners' Cup":
    "https://media.api-sports.io/football/leagues/531.png",

    "Inter-Cities Fairs Cup":
    "https://media.api-sports.io/football/leagues/3.png",

    "La Liga":
    "https://media.api-sports.io/football/leagues/140.png",

    "Copa del Rey":
    "https://media.api-sports.io/football/leagues/143.png",

    "Supercopa de España":
    "https://media.api-sports.io/football/leagues/556.png",

    "Intercontinental Cup":
    "https://media.api-sports.io/football/leagues/15.png",

    "Intertoto Cup":
    "https://media.api-sports.io/football/leagues/531.png",

    "Serie A":
    "https://media.api-sports.io/football/leagues/135.png",

    "Coppa Italia":
    "https://media.api-sports.io/football/leagues/137.png",

    "Supercoppa Italiana":
    "https://media.api-sports.io/football/leagues/547.png",

    "UEFA Cup":
    "https://media.api-sports.io/football/leagues/3.png",

    "Bundesliga":
    "https://media.api-sports.io/football/leagues/78.png",

    "DFB-Pokal":
    "https://media.api-sports.io/football/leagues/81.png",

    "DFL-Supercup":
    "https://media.api-sports.io/football/leagues/526.png",

    "Ligue 1":
    "https://media.api-sports.io/football/leagues/61.png",

    "Coupe de France":
    "https://media.api-sports.io/football/leagues/66.png",

    "Coupe de la Ligue":
    "https://media.api-sports.io/football/leagues/65.png",

    "Trophée des Champions":
    "https://media.api-sports.io/football/leagues/67.png",

    "UEFA Intertoto Cup":
    "https://media.api-sports.io/football/leagues/531.png",

}


TEAM_TROPHIES = {

    # Manchester United
    33: {
        "Premier League": 20,
        "FA Cup": 13,
        "League Cup": 6,
        "UEFA Champions League": 3,
        "UEFA Europa League": 1,
        "UEFA Super Cup": 1,
        "FIFA Club World Cup": 1,
    },

    # Liverpool
    40: {
        "Premier League": 20,
        "FA Cup": 8,
        "League Cup": 10,
        "UEFA Champions League": 6,
        "UEFA Europa League": 3,
        "UEFA Super Cup": 4,
        "FIFA Club World Cup": 1,
    },

    # Arsenal
    42: {
        "Premier League": 13,
        "FA Cup": 14,
        "League Cup": 2,
        "UEFA Cup Winners' Cup": 1,
    },

    # Chelsea
    49: {
        "Premier League": 6,
        "FA Cup": 8,
        "League Cup": 5,
        "UEFA Champions League": 2,
        "UEFA Europa League": 2,
        "UEFA Conference League": 1,
        "UEFA Super Cup": 2,
        "FIFA Club World Cup": 1,
    },

    # Manchester City
    50: {
        "Premier League": 10,
        "FA Cup": 7,
        "League Cup": 8,
        "UEFA Champions League": 1,
        "UEFA Super Cup": 1,
        "FIFA Club World Cup": 1,
    },

    # Tottenham
    47: {
        "Premier League": 2,
        "FA Cup": 8,
        "League Cup": 4,
        "UEFA Europa League": 3,
        "UEFA Cup Winners' Cup": 1,
    },

    # Newcastle United
    34: {
        "Premier League": 4,
        "FA Cup": 6,
        "League Cup": 1,
        "Inter-Cities Fairs Cup": 1,
    },

    # Aston Villa
    66: {
        "Premier League": 7,
        "FA Cup": 7,
        "League Cup": 5,
        "UEFA Champions League": 1,
        "UEFA Super Cup": 1,
    },

    # West Ham United
    48: {
        "FA Cup": 3,
        "UEFA Conference League": 1,
        "UEFA Cup Winners' Cup": 1,
    },

    # Everton
    45: {
        "Premier League": 9,
        "FA Cup": 5,
        "UEFA Cup Winners' Cup": 1,
    },

    # Crystal Palace
    52: {
    },

    # Brighton
    51: {
    },

    # Wolverhampton Wanderers
    39: {
        "Premier League": 3,
        "FA Cup": 4,
        "League Cup": 2,
    },

    # Fulham
    36: {
    },

    # Brentford
    55: {
    },

    # Nottingham Forest
    65: {
        "Premier League": 1,
        "League Cup": 4,
        "UEFA Champions League": 2,
        "UEFA Super Cup": 1,
    },

    # Bournemouth
    35: {
    },

    # Burnley
    44: {
        "Premier League": 2,
        "FA Cup": 1,
    },

    # Leeds United
    63: {
        "Premier League": 3,
        "FA Cup": 1,
        "League Cup": 1,
        "Inter-Cities Fairs Cup": 2,
    },

    # Sunderland
    46: {
        "Premier League": 6,
        "FA Cup": 2,
    },

    40: {
        "Premier League": 20,
        "FA Cup": 8,
        "League Cup": 10,
        "UEFA Champions League": 6,
        "UEFA Europa League": 3,
        "UEFA Super Cup": 4,
        "FIFA Club World Cup": 1,
    },

    # ================= LALIGA =================

    541: {
        "La Liga": 36,
        "Copa del Rey": 20,
        "Supercopa de España": 13,
        "UEFA Champions League": 15,
        "UEFA Europa League": 2,
        "UEFA Super Cup": 6,
        "FIFA Club World Cup": 9,
    },

    529: {
        "La Liga": 28,
        "Copa del Rey": 32,
        "Supercopa de España": 15,
        "UEFA Champions League": 5,
        "UEFA Super Cup": 5,
        "FIFA Club World Cup": 3,
    },

    530: {
        "La Liga": 11,
        "Copa del Rey": 10,
        "Supercopa de España": 2,
        "UEFA Europa League": 3,
        "UEFA Super Cup": 3,
        "UEFA Cup Winners' Cup": 1,
        "Intercontinental Cup": 1,
    },

    531: {
        "La Liga": 8,
        "Copa del Rey": 25,
        "Supercopa de España": 3,
    },

    536: {
        "La Liga": 1,
        "Copa del Rey": 5,
        "Supercopa de España": 1,
        "UEFA Europa League": 7,
        "UEFA Super Cup": 1,
    },

    532: {
        "La Liga": 6,
        "Copa del Rey": 8,
        "Supercopa de España": 2,
        "UEFA Cup Winners' Cup": 1,
        "UEFA Super Cup": 2,
        "UEFA Europa League": 1,
    },

    533: {
        "UEFA Europa League": 1,
    },

    543: {
        "La Liga": 1,
        "Copa del Rey": 3,
    },

    548: {
        "La Liga": 2,
        "Copa del Rey": 3,
        "Supercopa de España": 1,
    },

    540: {
        "Copa del Rey": 4,
    },

    542: {
    },

    538: {
        "Intertoto Cup": 1,
    },

    546: {
    },

    727: {
    },

    728: {
    },

    798: {
        "Copa del Rey": 1,
        "Supercopa de España": 1,
    },

    547: {
    },

    797: {
    },

    5460: {
    },

    724: {
    },

    # ================= SERIE A =================

    496: {
        "Serie A": 36,
        "Coppa Italia": 15,
        "Supercoppa Italiana": 9,
        "UEFA Champions League": 2,
        "UEFA Europa League": 3,
        "UEFA Super Cup": 2,
        "Intercontinental Cup": 2,
    },

    505: {
        "Serie A": 20,
        "Coppa Italia": 9,
        "Supercoppa Italiana": 8,
        "UEFA Champions League": 3,
        "UEFA Europa League": 3,
        "UEFA Super Cup": 2,
        "FIFA Club World Cup": 1,
        "Intercontinental Cup": 2,
    },

    489: {
        "Serie A": 19,
        "Coppa Italia": 5,
        "Supercoppa Italiana": 8,
        "UEFA Champions League": 7,
        "UEFA Super Cup": 5,
        "FIFA Club World Cup": 1,
        "Intercontinental Cup": 3,
    },

    492: {
        "Serie A": 4,
        "Coppa Italia": 6,
        "Supercoppa Italiana": 2,
        "UEFA Cup": 1,
    },

    497: {
        "Serie A": 3,
        "Coppa Italia": 9,
        "Supercoppa Italiana": 2,
        "UEFA Conference League": 1,
        "Inter-Cities Fairs Cup": 1,
    },

    487: {
        "Serie A": 2,
        "Coppa Italia": 7,
        "Supercoppa Italiana": 5,
        "UEFA Cup Winners' Cup": 1,
        "UEFA Super Cup": 1,
    },

    502: {
        "Serie A": 2,
        "Coppa Italia": 6,
        "Supercoppa Italiana": 1,
        "UEFA Cup Winners' Cup": 1,
    },

    500: {
        "Serie A": 7,
        "Coppa Italia": 3,
        "Intertoto Cup": 1,
    },

    503: {
        "Serie A": 7,
        "Coppa Italia": 5,
    },

    523: {
        "Coppa Italia": 3,
        "UEFA Cup": 2,
        "UEFA Super Cup": 1,
        "UEFA Cup Winners' Cup": 1,
    },

    499: {
        "UEFA Europa League": 1,
        "Coppa Italia": 1,
    },

    494: {
    },

    495: {
        "Serie A": 9,
        "Coppa Italia": 1,
    },

    490: {
        "Serie A": 1,
    },

    504: {
        "Serie A": 1,
    },

    867: {
    },

    488: {
    },

    515: {
    },

    520: {
    },

    895: {
    },

    # ================= BUNDESLIGA =================

    157: {
        "Bundesliga": 34,
        "DFB-Pokal": 20,
        "DFL-Supercup": 11,
        "UEFA Champions League": 6,
        "UEFA Super Cup": 2,
        "FIFA Club World Cup": 2,
        "Intercontinental Cup": 2,
    },

    165: {
        "Bundesliga": 8,
        "DFB-Pokal": 5,
        "DFL-Supercup": 6,
        "UEFA Champions League": 1,
        "UEFA Cup Winners' Cup": 1,
        "Intercontinental Cup": 1,
    },

    168: {
        "Bundesliga": 1,
        "DFB-Pokal": 2,
        "DFL-Supercup": 1,
        "UEFA Cup": 1,
    },

    169: {
        "Bundesliga": 1,
        "DFB-Pokal": 5,
        "UEFA Europa League": 2,
        "UEFA Cup": 1,
    },

    172: {
        "Bundesliga": 5,
        "DFB-Pokal": 3,
        "DFL-Supercup": 1,
    },

    163: {
        "Bundesliga": 5,
        "DFB-Pokal": 3,
        "UEFA Cup": 2,
    },

    162: {
        "Bundesliga": 4,
        "DFB-Pokal": 6,
        "DFL-Supercup": 3,
        "UEFA Cup Winners' Cup": 1,
    },

    161: {
        "Bundesliga": 1,
        "DFB-Pokal": 1,
        "DFL-Supercup": 1,
    },

    164: {
        "Bundesliga": 6,
        "DFB-Pokal": 3,
        "UEFA Champions League": 1,
        "UEFA Cup Winners' Cup": 1,
        "Intercontinental Cup": 1,
    },

    192: {
        "Bundesliga": 3,
        "DFB-Pokal": 4,
    },

    160: {
    },

    1640: {
    },

    167: {
    },

    170: {
    },

    182: {
    },

    173: {
        "DFB-Pokal": 2,
        "DFL-Supercup": 1,
    },

    191: {
    },

    44: {
    },

    181: {
        "Bundesliga": 2,
        "DFB-Pokal": 1,
    },

    180: {
        "Bundesliga": 4,
        "DFB-Pokal": 2,
    },

    # ================= LIGUE 1 =================

    85: {
        "Ligue 1": 13,
        "Coupe de France": 16,
        "Trophée des Champions": 13,
        "Coupe de la Ligue": 9,
        "UEFA Champions League": 1,
    },

    81: {
        "Ligue 1": 10,
        "Coupe de France": 10,
        "Trophée des Champions": 3,
        "Coupe de la Ligue": 3,
        "UEFA Champions League": 1,
        "UEFA Intertoto Cup": 1,
    },

    91: {
        "Ligue 1": 8,
        "Coupe de France": 5,
        "Trophée des Champions": 4,
        "Coupe de la Ligue": 1,
    },

    80: {
        "Ligue 1": 7,
        "Coupe de France": 5,
        "Trophée des Champions": 8,
        "Coupe de la Ligue": 1,
        "UEFA Intertoto Cup": 1,
    },

    79: {
        "Ligue 1": 4,
        "Coupe de France": 6,
        "Trophée des Champions": 1,
    },

    83: {
        "Ligue 1": 8,
        "Coupe de France": 4,
        "Trophée des Champions": 3,
    },

    106: {
        "Ligue 1": 10,
        "Coupe de France": 6,
        "Coupe de la Ligue": 1,
        "Trophée des Champions": 5,
    },

    84: {
        "Ligue 1": 4,
        "Coupe de France": 3,
    },

    576: {
        "Ligue 1": 1,
        "Coupe de France": 3,
        "Coupe de la Ligue": 3,
        "UEFA Intertoto Cup": 1,
    },

    116: {
        "Ligue 1": 1,
        "Coupe de la Ligue": 2,
    },

    94: {
        "Coupe de France": 3,
        "Trophée des Champions": 1,
    },

    108: {
        "Ligue 1": 1,
        "Coupe de France": 4,
    },

    96: {
        "Coupe de France": 2,
    },

    1063: {
    },

    112: {
    },

    77: {
    },

    97: {
    },

    111: {
    },

    1041: {
    },

}


# ================= CLEAN NAMES =================

TEAM_NAMES = {

    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Tottenham": "Tottenham",
    "Arsenal": "Arsenal",
    "Liverpool": "Liverpool",
    "Chelsea": "Chelsea",
    "Paris Saint Germain": "PSG",
    "Inter": "Inter Milan",
    "Internazionale": "Inter Milan",
    "FC Barcelona": "Barcelona",
    "Real Madrid": "Real Madrid",
    "Crystal Palace": "C.Palace",
    "Nottingham Forest": "N.Forest",
    "Borussia Mönchengladbach": "M'gladbach",
    "1. FC Heidenheim": "Heidenheim",

}


countries = [


     {
        "name": "Europe",
        "flag": "https://flagcdn.com/w40/eu.png",
        "leagues": [
            {"name": "Champions League", "code": "UCL", "logo": "https://media.api-sports.io/football/leagues/2.png", "type": "cup"},
            {"name": "Europa League", "code": "UEL", "logo": "https://media.api-sports.io/football/leagues/3.png", "type": "cup"},
            {"name": "Conference League", "code": "UECL", "logo": "https://media.api-sports.io/football/leagues/848.png", "type": "cup"},
        ]
    },

    {
        "name": "England",
        "flag": "https://upload.wikimedia.org/wikipedia/en/b/be/Flag_of_England.svg",
        "leagues": [
            {"name": "Premier League", "code": "PL", "logo": "https://media.api-sports.io/football/leagues/39.png", "type": "league"},
            {"name": "FA Cup", "code": "FAC", "logo": "https://media.api-sports.io/football/leagues/45.png", "type": "cup"},
            {"name": "EFL Cup", "code": "ELCUP", "logo": "https://media.api-sports.io/football/leagues/48.png", "type": "cup"},
        ]
    },

    {
        "name": "Spain",
        "flag": "https://flagcdn.com/w40/es.png",
        "leagues": [
            {"name": "La Liga", "code": "PD", "logo": "https://media.api-sports.io/football/leagues/140.png", "type": "league"},
            {"name": "Copa del Rey", "code": "CDR", "logo": "https://media.api-sports.io/football/leagues/143.png", "type": "cup"},
            {"name": "Super Cup", "code": "SC", "logo": "https://media.api-sports.io/football/leagues/556.png", "type": "supercup"},
        ]
    },

    {
        "name": "Italy",
        "flag": "https://flagcdn.com/w40/it.png",
        "leagues": [
            {"name": "Serie A", "code": "SA", "logo": "https://media.api-sports.io/football/leagues/135.png", "type": "league"},
            {"name": "Coppa Italia", "code": "COP", "logo": "https://media.api-sports.io/football/leagues/137.png", "type": "cup"},
            {"name": "Supercoppa", "code": "DSC", "logo": "https://media.api-sports.io/football/leagues/547.png", "type": "supercup"},
        ]
    },

    {
        "name": "Germany",
        "flag": "https://flagcdn.com/w40/de.png",
        "leagues": [
            {"name": "Bundesliga", "code": "BL1", "logo": "https://media.api-sports.io/football/leagues/78.png", "type": "league"},
            {"name": "DFB Pokal", "code": "DFB", "logo": "https://media.api-sports.io/football/leagues/81.png", "type": "cup"},
            {"name": "DFL Super Cup", "code": "DSUP", "logo": "https://media.api-sports.io/football/leagues/529.png", "type": "supercup"},
        ]
    },

    {
        "name": "France",
        "flag": "https://flagcdn.com/w40/fr.png",
        "leagues": [
            {"name": "Ligue 1", "code": "FL1", "logo": "https://media.api-sports.io/football/leagues/61.png", "type": "leauge"},
            {"name": "Coupe de France", "code": "CDF", "logo": "https://media.api-sports.io/football/leagues/66.png", "type": "cup"},
            {"name": "Trophée des Champions", "code": "TDC", "logo": "https://media.api-sports.io/football/leagues/526.png", "type": "supercup"},
        ]
    },


]


def get_common_context():
    return {
        "competitions": LEAGUES,
        "countries": countries,
    }


def clean_team_name(name):
    return TEAM_NAMES.get(name, name)


# ================= HOME ===========
def matches(request, matchday=None):

    if matchday is None:
        matchday = get_current_matchday("PL")
    else:
        matchday = int(matchday)

    data, games = get_matches("PL", matchday)

    return render(
        request,
        "pages/index.html",
        {
            **get_common_context(),
            "competition": data,
            "matches": games,
            "code": "PL",
            "matchday": matchday,
            "previous_matchday": max(1, matchday - 1),
            "next_matchday": min(38, matchday + 1),
        }
    )

# ================= GET MATCHES (جدول المباريات - دقيقة واحدة) =================
def get_matches(code, matchday):

    cache_key = f"matches_v3_{code}_{SEASON}_{matchday}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    league = LEAGUES[code]["id"]

    url = "https://v3.football.api-sports.io/fixtures"

    params = {
        "league": league,
        "season": SEASON,
        "round": f"Regular Season - {matchday}"
    }

    response = requests.get(
        url,
        headers=headers,
        params=params
    )

    data = response.json()

    fixtures = data.get("response", [])

    matches = []

    for f in fixtures:

        matches.append({

            "id": f["fixture"]["id"],

            "homeTeam": {
                "id": f["teams"]["home"]["id"],
                "name": clean_team_name(f["teams"]["home"]["name"]),
                "crest": f["teams"]["home"]["logo"]
            },

            "awayTeam": {
                "id": f["teams"]["away"]["id"],
                "name": clean_team_name(f["teams"]["away"]["name"]),
                "crest": f["teams"]["away"]["logo"]
            },

            "score": {
                "fullTime": {
                    "home": f["goals"]["home"],
                    "away": f["goals"]["away"]
                }
            },

            "status": f["fixture"]["status"]["short"],
            "elapsed": f["fixture"]["status"].get("elapsed"),

            "utcDate": to_mecca_time(f["fixture"]["date"]),
        })

    competition = {
        "name": LEAGUES[code]["name"],
        "logo": LEAGUES[code]["logo"]
    }

    result = (competition, matches)

    cache.set(cache_key, result, MATCHES_CACHE_TTL)

    return result



def get_current_matchday(code):

    league_id = LEAGUES[code]["id"]

    cache_key = f"current_matchday_v1_{code}_{SEASON}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    url = "https://v3.football.api-sports.io/fixtures/rounds"

    params = {
        "league": league_id,
        "season": SEASON,
        "current": "true"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        data = response.json()
    except requests.RequestException:
        data = {}

    rounds = data.get("response", [])

    matchday = 1

    if rounds:
        round_name = rounds[0]  # مثال: "Regular Season - 5"

        try:
            matchday = int(round_name.split("-")[-1].strip())
        except (ValueError, IndexError):
            matchday = 1

    cache.set(cache_key, matchday, MATCHES_CACHE_TTL)

    return matchday


def get_team_statistics_cached(team_id, league_id):

    cache_key = f"team_statistics_{league_id}_{SEASON}_{team_id}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    url = (
        f"https://v3.football.api-sports.io/teams/statistics"
        f"?league={league_id}"
        f"&season={SEASON}"
        f"&team={team_id}"
    )

    try:
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json().get("response", {})
    except requests.RequestException:
        data = {}

    if isinstance(data, list):
        data = {}

    cache.set(cache_key, data, CACHE_TTL)

    return data







import time


def safe_api_get(url, headers, params, timeout=15, max_retries=5):
    """
    يرسل طلب GET، وإذا رجع 429 (rate limit)، ينتظر وياعيد المحاولة تلقائياً
    """
    response = None

    for attempt in range(max_retries):

        response = requests.get(url, headers=headers, params=params, timeout=timeout)

        if response.status_code == 429:
            time.sleep(3)
            continue

        return response

    return response


def match_detail(request, id):

    # ================= CACHE TTLs =================
    CORE_CACHE_TTL = 60 * 60 * 12       # Overview + Comparison + H2H - 12 ساعة
    LIVE_STATUS_CACHE_TTL = 60          # حالة ونتيجة المباراة - كل دقيقة
    LINEUPS_CACHE_TTL = 60 * 15         # Lineups - 15 دقيقة
    EVENTS_CACHE_TTL = 60 * 2           # أثناء المباراة - دقيقتين
    STATS_CACHE_TTL = 60 * 2            # أثناء المباراة - دقيقتين
    HALFTIME_CACHE_TTL = 60 * 15        # بين الشوطين - 15 دقيقة
    FINISHED_CACHE_TTL = 60 * 60 * 24   # بعد المباراة - 24 ساعة
    STATIC_CACHE_TTL = 60 * 60 * 24 * 7 # البيانات الثابتة - أسبوع
    NOT_STARTED_CACHE_TTL = 60          # المباراة لم تبدأ - دقيقة واحدة

    def get_match_ttl(status):
        if status in ["1H", "2H", "ET", "BT", "P", "LIVE"]:
            return EVENTS_CACHE_TTL
        elif status == "HT":
            return HALFTIME_CACHE_TTL
        elif status in ["FT", "AET", "PEN", "CANC", "ABD", "AWD", "WO"]:
            return FINISHED_CACHE_TTL
        elif status in ["NS", "TBD", "PST", "SUSP", "INT"]:
            return NOT_STARTED_CACHE_TTL
        return NOT_STARTED_CACHE_TTL

    def get_live_status_ttl(status):
        if status in ["FT", "AET", "PEN", "CANC", "ABD", "AWD", "WO"]:
            return FINISHED_CACHE_TTL
        return LIVE_STATUS_CACHE_TTL

    core_cache_key = f"match_core_v3_{id}"
    live_cache_key = f"match_live_v3_{id}"
    lineups_cache_key = f"match_lineups_v3_{id}"
    events_cache_key = f"match_events_v3_{id}"
    stats_cache_key = f"match_stats_v3_{id}"

    # ================= CORE (Overview + Comparison + H2H) =================

    core_data = cache.get(core_cache_key)

    if core_data is None:

        fixture_response = safe_api_get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={"id": id},
            timeout=15
        )

        fixture_data = fixture_response.json()
        fixtures = fixture_data.get("response", [])

        if not fixtures:
            return render(
                request,
                "pages/match_detail.html",
                {
                    "game": None,
                    "lineups": [],
                    "competitions": LEAGUES
                }
            )

        f = fixtures[0]

        game = {
            "id": f["fixture"]["id"],
            "home_name": clean_team_name(f["teams"]["home"]["name"]),
            "away_name": clean_team_name(f["teams"]["away"]["name"]),
            "home_logo": f["teams"]["home"]["logo"],
            "away_logo": f["teams"]["away"]["logo"],
            "home_id": f["teams"]["home"]["id"],
            "away_id": f["teams"]["away"]["id"],
            "score": {
                "fullTime": {
                    "home": f["goals"]["home"],
                    "away": f["goals"]["away"]
                }
            },
            "status": f["fixture"]["status"]["short"],
            "elapsed": f["fixture"]["status"].get("elapsed"),
            "utcDate": to_mecca_time(f["fixture"]["date"]),
            "competition": {
                "name": f["league"]["name"],
                "logo": f["league"]["logo"]
            },
            "season": f["league"]["season"],
            "round": f["league"].get("round"),
            "venue": f["fixture"]["venue"].get("name"),
            "referee": f["fixture"].get("referee")
        }

        cache.set(
            live_cache_key,
            game,
            get_live_status_ttl(game["status"])
        )

        home_id = game["home_id"]
        away_id = game["away_id"]
        league_id = f["league"]["id"]

        # ---- last matches ----

        home_last_response = safe_api_get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={
                "team": home_id,
                "season": f["league"]["season"],
                "league": league_id,
                "last": 5
            },
            timeout=15
        )

        away_last_response = safe_api_get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={
            "team": away_id,
            "season": f["league"]["season"],
            "league": league_id,
            "last": 5
            },
            timeout=15
        )
        
        home_last_matches = home_last_response.json().get("response", [])

        away_last_matches = away_last_response.json().get("response", [])

        

        # ---- comparison (season team stats) ----

        def get_team_comparison(data):
            fixtures_stats = data.get("fixtures", {})
            goals = data.get("goals", {})
            clean_sheet = data.get("clean_sheet", {})
            biggest = data.get("biggest", {})

            return {
                "played": fixtures_stats.get("played", {}).get("total", 0),
                "wins": fixtures_stats.get("wins", {}).get("total", 0),
                "draws": fixtures_stats.get("draws", {}).get("total", 0),
                "losses": fixtures_stats.get("loses", {}).get("total", 0),
                "goals_for": goals.get("for", {}).get("total", {}).get("total", 0),
                "goals_against": goals.get("against", {}).get("total", {}).get("total", 0),
                "clean_sheets": clean_sheet.get("total", 0),
                "big_chances": biggest.get("chances", {}).get("created", 0),
            }

        home_statistics = get_team_statistics_cached(home_id, league_id)
        away_statistics = get_team_statistics_cached(away_id, league_id)

        comparison = {
            "home": get_team_comparison(home_statistics),
            "away": get_team_comparison(away_statistics),
        }

        # ---- H2H ----

        h2h_response = safe_api_get(
            "https://v3.football.api-sports.io/fixtures/headtohead",
            headers=headers,
            params={"h2h": f"{home_id}-{away_id}"},
            timeout=15
        )

        h2h_json = h2h_response.json()
        h2h_matches_raw = h2h_json.get("response", [])

        h2h_matches = sorted(
            h2h_matches_raw,
            key=lambda x: x["fixture"]["date"],
            reverse=True
        )[:10]

        def build_h2h():
            matches = []
            home_wins = 0
            away_wins = 0
            draws = 0

            for m in h2h_matches:

                try:
                    m_home_id = m["teams"]["home"]["id"]
                    m_home_goals = m["goals"]["home"]
                    m_away_goals = m["goals"]["away"]
                except (KeyError, TypeError):
                    continue

                if m_home_goals is None or m_away_goals is None:
                    continue

                if m_home_goals == m_away_goals:
                    draws += 1

                elif (
                    (m_home_goals > m_away_goals and m_home_id == home_id)
                    or
                    (m_away_goals > m_home_goals and m_home_id == away_id)
                ):
                    home_wins += 1

                else:
                    away_wins += 1

                try:
                    matches.append({
                        "date": datetime.fromisoformat(
                            m["fixture"]["date"].replace("Z", "+00:00")
                        ),
                        "competition": m["league"]["name"],
                        "home_name": clean_team_name(
                            m["teams"]["home"]["name"]
                        ),
                        "away_name": clean_team_name(
                            m["teams"]["away"]["name"]
                        ),
                        "home_logo": m["teams"]["home"]["logo"],
                        "away_logo": m["teams"]["away"]["logo"],
                        "home_goals": m_home_goals,
                        "away_goals": m_away_goals,
                    })

                except (KeyError, TypeError):
                    continue

            return {
                "matches": matches,
                "home_wins": home_wins,
                "away_wins": away_wins,
                "draws": draws,
                "total": len(matches),
            }

        h2h = build_h2h()

        core_data = {
            "game": game,
            "home_last_matches": home_last_matches,
            "away_last_matches": away_last_matches,
            "comparison": comparison,
            "h2h": h2h,
        }

        cache.set(
            core_cache_key,
            core_data,
            STATIC_CACHE_TTL
        )

    # ================= LIVE MATCH STATUS (كل دقيقة) =================

    live_game = cache.get(live_cache_key)

    if live_game is None:

        live_fixture_response = safe_api_get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={"id": id},
            timeout=15
        )

        live_fixture_data = live_fixture_response.json()
        live_fixtures = live_fixture_data.get("response", [])

        if live_fixtures:

            lf = live_fixtures[0]

            live_game = {
                **core_data["game"],

                "score": {
                    "fullTime": {
                        "home": lf["goals"]["home"],
                        "away": lf["goals"]["away"]
                    }
                },

                "status": lf["fixture"]["status"]["short"],
                "elapsed": lf["fixture"]["status"].get("elapsed"),
            }

            cache.set(
                live_cache_key,
                live_game,
                get_live_status_ttl(live_game["status"])
            )

        else:
            live_game = core_data["game"]

    game = live_game

    match_status = game.get("status", "NS")

    dynamic_cache_ttl = get_match_ttl(match_status)

    home_last_matches = core_data["home_last_matches"]
    away_last_matches = core_data["away_last_matches"]

    comparison = core_data["comparison"]
    h2h = core_data["h2h"]

    home_id = game["home_id"]
    away_id = game["away_id"]

    # ================= LINEUPS (15 دقيقة) =================

    lineups_cached = cache.get(lineups_cache_key)

    if lineups_cached is None:

        def build_lines(players, reverse=False):

            rows = defaultdict(list)

            for p in players:

                grid = p.get("grid")

                if not grid:
                    continue

                row_num, col_num = grid.split(":")

                rows[int(row_num)].append({
                    **p,
                    "col": int(col_num)
                })

            lines = []

            for row_num in sorted(rows.keys()):

                line_players = sorted(
                    rows[row_num],
                    key=lambda x: x["col"],
                    reverse=reverse
                )

                lines.append({
                    "row": row_num,
                    "is_gk": row_num == 1,
                    "players": line_players
                })

            return lines

        def build_team_lineup(
            team_data,
            player_stats_map,
            is_away=False
        ):

            starting = []

            team_id = team_data["team"]["id"]

            squad_info = get_team_squad_info(team_id)

            for item in team_data.get("startXI", []):

                player = item.get("player", {})
                player_id = player.get("id")

                player_photo = squad_info.get(
                    player_id,
                    {}
                ).get("photo")

                player_rating_info = player_stats_map.get(
                    player_id,
                    {}
                )

                starting.append({
                    "id": player_id,
                    "name": player.get("name"),
                    "number": player.get("number"),
                    "position": player.get("pos"),
                    "grid": player.get("grid"),
                    "photo": player_photo,
                    "rating": player_rating_info.get("rating"),
                    "rating_class": player_rating_info.get("rating_class"),
                })

            substitutes = []

            for item in team_data.get("substitutes", []):

                player = item.get("player", {})
                player_id = player.get("id")

                player_photo = squad_info.get(
                    player_id,
                    {}
                ).get("photo")

                substitutes.append({
                    "id": player_id,
                    "name": player.get("name"),
                    "number": player.get("number"),
                    "position": player.get("pos"),
                    "photo": player_photo,
                })

            coach_data = team_data.get("coach") or {}

            return {
                "team": clean_team_name(
                    team_data["team"]["name"]
                ),

                "logo": team_data["team"]["logo"],

                "formation": team_data.get("formation"),

                "coach": coach_data.get("name"),

                "starting": starting,

                "lines": build_lines(
                    starting,
                    reverse=is_away
                ),

                "substitutes": substitutes,
            }

        def build_player_stats(players_data):

            result = {}

            for team_entry in players_data:

                for p in team_entry.get("players", []):

                    player_id = p.get("player", {}).get("id")

                    if not player_id:
                        continue

                    stats_list = p.get("statistics", [])

                    if not stats_list:
                        continue

                    s = stats_list[0]

                    games = s.get("games", {}) or {}
                    goals = s.get("goals", {}) or {}
                    shots = s.get("shots", {}) or {}
                    passes = s.get("passes", {}) or {}
                    tackles = s.get("tackles", {}) or {}
                    duels = s.get("duels", {}) or {}
                    dribbles = s.get("dribbles", {}) or {}
                    fouls = s.get("fouls", {}) or {}
                    cards = s.get("cards", {}) or {}
                    penalty = s.get("penalty", {}) or {}

                    raw_rating = games.get("rating")

                    rating_value = None
                    rating_class = None

                    if raw_rating:

                        try:

                            rating_value = round(
                                float(raw_rating),
                                1
                            )

                            if rating_value < 5:
                                rating_class = "red"

                            elif rating_value < 7:
                                rating_class = "orange"

                            elif rating_value < 9:
                                rating_class = "green"

                            else:
                                rating_class = "blue"

                        except (TypeError, ValueError):

                            rating_value = None

                    result[player_id] = {

                        "minutes": games.get("minutes"),

                        "position": games.get("position"),

                        "rating": rating_value,

                        "rating_class": rating_class,

                        "captain": games.get("captain"),

                        "goals": goals.get("total") or 0,

                        "assists": goals.get("assists") or 0,

                        "conceded": goals.get("conceded"),

                        "saves": goals.get("saves"),

                        "shots_total": shots.get("total") or 0,

                        "shots_on": shots.get("on") or 0,

                        "passes_total": passes.get("total") or 0,

                        "passes_key": passes.get("key") or 0,

                        "passes_accuracy": passes.get("accuracy"),

                        "tackles_total": tackles.get("total") or 0,

                        "blocks": tackles.get("blocks") or 0,

                        "interceptions": tackles.get("interceptions") or 0,

                        "duels_total": duels.get("total") or 0,

                        "duels_won": duels.get("won") or 0,

                        "dribbles_attempts": dribbles.get("attempts") or 0,

                        "dribbles_success": dribbles.get("success") or 0,

                        "fouls_drawn": fouls.get("drawn") or 0,

                        "fouls_committed": fouls.get("committed") or 0,

                        "yellow_cards": cards.get("yellow") or 0,

                        "red_cards": cards.get("red") or 0,

                        "penalty_scored": penalty.get("scored") or 0,

                        "penalty_missed": penalty.get("missed") or 0,

                        "penalty_saved": penalty.get("saved") or 0,
                    }

            return result

        players_response = safe_api_get(
            "https://v3.football.api-sports.io/fixtures/players",
            headers=headers,
            params={"fixture": id},
            timeout=15
        )

        players_json = players_response.json()

        players_data = players_json.get(
            "response",
            []
        )

        player_stats = build_player_stats(
            players_data
        )

        lineup_response = safe_api_get(
            "https://v3.football.api-sports.io/fixtures/lineups",
            headers=headers,
            params={"fixture": id},
            timeout=15
        )

        lineup_json = lineup_response.json()

        lineups_data_raw = lineup_json.get(
            "response",
            []
        )

        lineups = {
            "home": None,
            "away": None
        }

        if len(lineups_data_raw) >= 2:

            lineups["home"] = build_team_lineup(
                lineups_data_raw[0],
                player_stats,
                is_away=False
            )

            lineups["away"] = build_team_lineup(
                lineups_data_raw[1],
                player_stats,
                is_away=True
            )

        lineups_cached = {
            "lineups": lineups,
            "player_stats": player_stats,
        }

        cache.set(
            lineups_cache_key,
            lineups_cached,
            FINISHED_CACHE_TTL
            if match_status in [
                "FT",
                "AET",
                "PEN",
                "CANC",
                "ABD",
                "AWD",
                "WO"
            ]
            else LINEUPS_CACHE_TTL
        )

    lineups = lineups_cached["lineups"]

    player_stats = lineups_cached["player_stats"]

    # ================= EVENTS (دقيقتين) =================

    events_cached = cache.get(events_cache_key)

    if events_cached is None:

        def group_scorers(events_list, side):

            grouped = {}
            order = []

            for e in events_list:

                if (
                    e["type"] == "Goal"
                    and e.get("player")
                    and e["side"] == side
                ):

                    name = e["player"]

                    goal = {
                        "minute": e["minute"],
                        "extra": e["extra"]
                    }

                    if name not in grouped:

                        grouped[name] = {
                            "player": name,
                            "goals": [goal]
                        }

                        order.append(name)

                    else:

                        grouped[name]["goals"].append(goal)

            return [
                grouped[name]
                for name in order
            ]

        events_response = safe_api_get(
            "https://v3.football.api-sports.io/fixtures/events",
            headers=headers,
            params={"fixture": id},
            timeout=15
        )

        events_json = events_response.json()

        api_failed = (
            events_response.status_code != 200
            or events_json.get("errors")
        )

        events = []

        for event in events_json.get("response", []):

            team_id = event["team"]["id"]

            squad_info = get_team_squad_info(team_id)

            player_id = event.get("player", {}).get("id")
            assist_id = event.get("assist", {}).get("id")

            player = squad_info.get(player_id, {})
            assist = squad_info.get(assist_id, {})

            side = "home" if team_id == home_id else "away"

            events.append({

                "minute": event["time"].get("elapsed"),
                "extra": event["time"].get("extra"),

                "team": clean_team_name(event["team"]["name"]),
                "team_logo": event["team"]["logo"],

                "player": event.get("player", {}).get("name"),
                "player_photo": player.get("photo"),

                "assist": event.get("assist", {}).get("name"),

                "type": event.get("type"),
                "detail": event.get("detail"),

                "side": side,
            })

        home_scorers = group_scorers(events, "home")
        away_scorers = group_scorers(events, "away")

        events_cached = {
            "events": events,
            "home_scorers": home_scorers,
            "away_scorers": away_scorers,
        }

        if not api_failed:
            cache.set(
                events_cache_key,
                events_cached,
                dynamic_cache_ttl
            )

    events = events_cached["events"]
    home_scorers = events_cached["home_scorers"]
    away_scorers = events_cached["away_scorers"]

    # ================= STATISTICS (دقيقتين) =================

    stats_cached = cache.get(
        stats_cache_key
    )

    if stats_cached is None:

        def parse_stat_value(value):

            if value is None:
                return 0

            if isinstance(value, str):

                cleaned = value.replace(
                    "%",
                    ""
                ).strip()

                try:

                    return (
                        float(cleaned)
                        if "." in cleaned
                        else int(cleaned)
                    )

                except ValueError:

                    return 0

            return value

        def build_statistics(
            stats_data,
            home_id_,
            away_id_
        ):

            if len(stats_data) < 2:
                return None

            display_names = {
                "expected_goals": "xG",
            }

            by_id = {
                team_stats["team"]["id"]: team_stats
                for team_stats in stats_data
            }

            home_team = by_id.get(
                home_id_
            )

            away_team = by_id.get(
                away_id_
            )

            if not home_team or not away_team:
                return None

            home_stats = {
                s.get("type"): s.get("value")
                for s in home_team.get(
                    "statistics",
                    []
                )
            }

            away_stats = {
                s.get("type"): s.get("value")
                for s in away_team.get(
                    "statistics",
                    []
                )
            }

            preferred_order = [

                "Ball Possession",

                "expected_goals",

                "Total Shots",

                "Shots on Goal",

                "Shots off Goal",

                "Blocked Shots",

                "Corner Kicks",

                "Passes accurate",

                "Passes %",

                "Offsides",

                "Fouls",

                "Yellow Cards",

                "Red Cards",

                "Goalkeeper Saves",

                "Total passes",
            ]

            available_types = (
                set(home_stats.keys())
                |
                set(away_stats.keys())
            )

            stat_types = [
                stat_type
                for stat_type in preferred_order
                if stat_type in available_types
            ]

            remaining_types = [
                s.get("type")
                for s in home_team.get(
                    "statistics",
                    []
                )
                if s.get("type")
                not in stat_types
            ]

            stat_types += remaining_types

            comparison_stats = []

            for stat_type in stat_types:

                home_raw = home_stats.get(
                    stat_type
                )

                away_raw = away_stats.get(
                    stat_type
                )

                home_val = parse_stat_value(
                    home_raw
                )

                away_val = parse_stat_value(
                    away_raw
                )

                total = (
                    home_val
                    +
                    away_val
                )

                home_pct = (
                    round(
                        (home_val / total) * 100,
                        1
                    )
                    if total
                    else 50
                )

                away_pct = (
                    round(
                        100 - home_pct,
                        1
                    )
                    if total
                    else 50
                )

                comparison_stats.append({

                    "type": display_names.get(
                        stat_type,
                        stat_type
                    ),

                    "home_display": (
                        home_raw
                        if home_raw is not None
                        else "0"
                    ),

                    "away_display": (
                        away_raw
                        if away_raw is not None
                        else "0"
                    ),

                    "home_pct": home_pct,

                    "away_pct": away_pct,
                })

            return {

                "home": {

                    "team": clean_team_name(
                        home_team["team"]["name"]
                    ),

                    "logo": home_team["team"]["logo"],
                },

                "away": {

                    "team": clean_team_name(
                        away_team["team"]["name"]
                    ),

                    "logo": away_team["team"]["logo"],
                },

                "comparison": comparison_stats,
            }

        stats_response = safe_api_get(
            "https://v3.football.api-sports.io/fixtures/statistics",
            headers=headers,
            params={"fixture": id},
            timeout=15
        )

        stats_json = stats_response.json()

        api_failed = (
            stats_response.status_code != 200
            or stats_json.get("errors")
        )

        stats_data = stats_json.get("response", [])

        statistics = build_statistics(
            stats_data,
            home_id_=home_id,
            away_id_=away_id,
        )

        stats_cached = {
            "statistics": statistics
        }

        if not api_failed:
            cache.set(
                stats_cache_key,
                stats_cached,
                dynamic_cache_ttl
            )

    statistics = stats_cached["statistics"]

    # ================= CONTEXT =================

    context = {

        "game": game,

        "lineups": lineups,

        "events": events,

        "statistics": statistics,

        "competitions": LEAGUES,

        "comparison": comparison,

        "home_last_matches": home_last_matches,

        "away_last_matches": away_last_matches,

        "player_stats": player_stats,

        "home_scorers": home_scorers,

        "away_scorers": away_scorers,

        "h2h": h2h,
    }

    return render(
        request,
        "pages/match_detail.html",
        context
    )

# ================= TEAM DETAIL (تفاصيل الفريق - 45 دقيقة) =================
def team_detail(request, id):

    cache_key = f"team_detail_v3_{id}"

    cached = cache.get(cache_key)

    if cached is not None:
        return render(
            request,
            "pages/team_detail.html",
            cached
        )

    team = None
    venue = None

    try:

        team_response = requests.get(
            "https://v3.football.api-sports.io/teams",
            headers=headers,
            params={
                "id": id
            },
            timeout=15
        )

        team_data = team_response.json()

    except requests.RequestException:

        team_data = {}

    if team_data.get("response"):

        team_entry = team_data["response"][0]

        team = team_entry.get("team")
        venue = team_entry.get("venue")

        if team:

            team["name"] = clean_team_name(
                team["name"]
            )

    if team is None:
        team = {"id": int(id), "name": "Unknown Team", "logo": None}

    def fetch_fixtures(extra_params):

        try:

            response = requests.get(
                "https://v3.football.api-sports.io/fixtures",
                headers=headers,
                params={
                    "team": id,
                    "season": SEASON,
                    **extra_params
                },
                timeout=15
            )

            data = response.json()

        except requests.RequestException:

            return []

        fixtures = data.get(
            "response",
            []
        )

        for f in fixtures:

            f["teams"]["home"]["name"] = clean_team_name(
                f["teams"]["home"]["name"]
            )

            f["teams"]["away"]["name"] = clean_team_name(
                f["teams"]["away"]["name"]
            )

        return fixtures

    season_fixtures = fetch_fixtures(
        {}
    )

    season_fixtures.sort(
        key=lambda f: f["fixture"]["date"]
    )

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    finished_matches = []
    upcoming_matches = []

    for match in season_fixtures:

        match_date = datetime.fromisoformat(
            match["fixture"]["date"].replace("Z", "+00:00")
        )

        if match["fixture"]["status"]["short"] == "FT":
            finished_matches.append(match)

        elif match_date > now:
            upcoming_matches.append(match)

    last_matches = finished_matches[-5:]

    last_matches.reverse()

    scheduled_matches = upcoming_matches[:5]

    next_match = scheduled_matches[0] if scheduled_matches else None

    if next_match:
        next_match["local_date"] = to_mecca_time(next_match["fixture"]["date"])

    form = []
    wins = 0
    draws = 0
    losses = 0

    for match in last_matches:

        home = match["teams"]["home"]["id"] == int(id)

        home_goals = match["goals"]["home"]
        away_goals = match["goals"]["away"]

        if home_goals is None or away_goals is None:
            continue

        if home:
            if home_goals > away_goals:
                form.append("W")
                wins += 1
            elif home_goals == away_goals:
                form.append("D")
                draws += 1
            else:
                form.append("L")
                losses += 1

        else:
            if away_goals > home_goals:
                form.append("W")
                wins += 1
            elif away_goals == home_goals:
                form.append("D")
                draws += 1
            else:
                form.append("L")
                losses += 1

    team_statistics = {

        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,

        "goals_for": 0,
        "goals_against": 0,

        "goal_difference": 0,

        "clean_sheets": 0,

        "home_wins": 0,
        "away_wins": 0,

        "biggest_win": 0,
        "biggest_loss": 0,

    }

    for match in season_fixtures:
        if match["fixture"]["status"]["short"] != "FT":
            continue

        home_id = match["teams"]["home"]["id"]
        away_id = match["teams"]["away"]["id"]

        home_goals = match["goals"]["home"] or 0
        away_goals = match["goals"]["away"] or 0

        if home_id == int(id):
            goals_for = home_goals
            goals_against = away_goals
            is_home = True

        else:

            goals_for = away_goals
            goals_against = home_goals
            is_home = False

        team_statistics["played"] += 1

        team_statistics["goals_for"] += goals_for
        team_statistics["goals_against"] += goals_against

        if goals_against == 0:
            team_statistics["clean_sheets"] += 1

        diff = goals_for - goals_against

        if diff > team_statistics["biggest_win"]:
            team_statistics["biggest_win"] = diff

        if diff < team_statistics["biggest_loss"]:
            team_statistics["biggest_loss"] = diff

        if goals_for > goals_against:

            team_statistics["wins"] += 1

            if is_home:
                team_statistics["home_wins"] += 1
            else:
                team_statistics["away_wins"] += 1

        elif goals_for == goals_against:
            team_statistics["draws"] += 1

        else:

            team_statistics["losses"] += 1

    team_statistics["goal_difference"] = (
        team_statistics["goals_for"]
        - team_statistics["goals_against"]
    )

    if team_statistics["played"]:

        team_statistics["average_goals"] = round(
            team_statistics["goals_for"] /
            team_statistics["played"],
            2
        )

        team_statistics["win_rate"] = round(
            team_statistics["wins"] * 100 /
            team_statistics["played"],
            1
        )

    else:
        team_statistics["average_goals"] = 0
        team_statistics["win_rate"] = 0

    team_league_code = None

    if season_fixtures:

        league_ids = [
            f["league"]["id"]
            for f in season_fixtures
        ]

        most_common_league_id = Counter(
            league_ids
        ).most_common(1)[0][0]

        for league_code, league_info in LEAGUES.items():

            if league_info["id"] == most_common_league_id:

                team_league_code = league_code

                break

    standings = []

    if team_league_code:

        standings = get_standings(
            team_league_code
        )

    trophies_cache_key = f"team_trophies_{id}"

    trophies = cache.get(
        trophies_cache_key
    )

    if trophies is None:

        raw_trophies = TEAM_TROPHIES.get(
            int(id),
            {}
        )

        trophies = []

        for name, count in raw_trophies.items():

            trophies.append({

                "name": name,

                "count": count,

                "logo": TROPHY_LOGOS.get(name)

            })

        cache.set(
            trophies_cache_key,
            trophies,
            CACHE_TTL
        )

    # ================= SQUAD =================

    squad_cache_key = f"team_squad_{id}"

    squad = cache.get(
        squad_cache_key
    )

    if squad is None:

        squad = []

        try:

            squad_response = requests.get(
                "https://v3.football.api-sports.io/players/squads",
                headers=headers,
                params={
                    "team": id
                },
                timeout=15
            )

            squad_json = squad_response.json()

            if squad_json.get("response"):

                for player in squad_json["response"][0].get("players", []):

                    age = player.get("age")
                    number = player.get("number")
                    position = player.get("position")

                    if not age or not position:
                        continue

                    if age < 17:
                        continue

                    if number and number > 73:
                        continue

                    squad.append({

                        "id": player.get("id"),

                        "name": player.get("name"),

                        "age": age,

                        "number": number,

                        "position": position,

                        "photo": player.get("photo")

                    })

                squad = sorted(
                    squad,
                    key=lambda x: x["age"] or 0,
                    reverse=True
                )

        except requests.RequestException:

            squad = []

        cache.set(
            squad_cache_key,
            squad,
            CACHE_TTL
        )

    goalkeepers = []
    defenders = []
    midfielders = []
    attackers = []

    for player in squad:

        position = player.get("position")

        if position == "Goalkeeper":
            goalkeepers.append(player)

        elif position == "Defender":

            defenders.append(player)

        elif position == "Midfielder":

            midfielders.append(player)

        elif position == "Attacker":

            attackers.append(player)

    players_stats = []

    league_id = None

    if team_league_code:

        league_id = LEAGUES[team_league_code]["id"]

        players_cache_key = (
            f"players_stats_{id}_{league_id}_{SEASON}"
        )

        players_stats = cache.get(
            players_cache_key
        )

    if players_stats is None:

        players_stats = []

        if league_id:

            page = 1

            while True:

                try:

                    response = requests.get(
                        "https://v3.football.api-sports.io/players",
                        headers=headers,
                        params={
                            "team": id,
                            "league": league_id,
                            "season": SEASON,
                            "page": page
                        },
                        timeout=20
                    )

                    data = response.json()

                except requests.RequestException:

                    break

                results = data.get(
                    "response",
                    []
                )

                if not results:

                    break

                for item in results:

                    player = item.get(
                        "player",
                        {}
                    )

                    statistics_list = item.get(
                        "statistics",
                        []
                    )

                    if not statistics_list:

                        continue

                    stats = statistics_list[0]

                    players_stats.append({

                        "id": player.get("id"),

                        "name": player.get("name"),

                        "photo": player.get("photo"),

                        "age": player.get("age"),

                        "position": stats.get("games", {}).get("position"),

                        "appearances": stats.get("games", {}).get("appearences", 0),

                        "minutes": stats.get("games", {}).get("minutes", 0),

                        "rating": stats.get("games", {}).get("rating", "0"),

                        "goals": stats.get("goals", {}).get("total") or 0,

                        "assists": stats.get("goals", {}).get("assists") or 0,

                        "shots": stats.get("shots", {}).get("total") or 0,

                        "shots_on": stats.get("shots", {}).get("on") or 0,

                        "passes": stats.get("passes", {}).get("total") or 0,

                        "key_passes": stats.get("passes", {}).get("key") or 0,

                        "accuracy": stats.get("passes", {}).get("accuracy") or "0%",

                        "dribbles": stats.get("dribbles", {}).get("success") or 0,

                        "tackles": stats.get("tackles", {}).get("total") or 0,

                        "interceptions": stats.get("tackles", {}).get("interceptions") or 0,

                        "yellow": stats.get("cards", {}).get("yellow") or 0,

                        "red": stats.get("cards", {}).get("red") or 0,

                    })

                paging = data.get(
                    "paging",
                    {}
                )

                if page >= paging.get("total", 1):

                    break

                page += 1

            cache.set(
                players_cache_key,
                players_stats,
                CACHE_TTL
            )

    team_leaders = {}

    if players_stats:

        team_leaders = {

            "top_scorer": max(
                players_stats,
                key=lambda p: p.get("goals") or 0
            ),

            "top_assists": max(
                players_stats,
                key=lambda p: p.get("assists") or 0
            ),

            "highest_rating": max(
                players_stats,
                key=lambda p: float(
                    p.get("rating") or 0
                )
            ),

            "most_minutes": max(
                players_stats,
                key=lambda p: p.get("minutes") or 0
            ),

            "most_shots": max(
                players_stats,
                key=lambda p: p.get("shots") or 0
            ),

            "most_shots_on_target": max(
                players_stats,
                key=lambda p: p.get("shots_on") or 0
            ),

            "most_key_passes": max(
                players_stats,
                key=lambda p: p.get("key_passes") or 0
            ),

            "most_passes": max(
                players_stats,
                key=lambda p: p.get("passes") or 0
            ),

            "most_tackles": max(
                players_stats,
                key=lambda p: p.get("tackles") or 0
            ),

            "most_interceptions": max(
                players_stats,
                key=lambda p: p.get("interceptions") or 0
            ),

            "most_yellow_cards": max(
                players_stats,
                key=lambda p: p.get("yellow") or 0
            ),

            "most_red_cards": max(
                players_stats,
                key=lambda p: p.get("red") or 0
            ),

        }

    context = {

        "team": team,

        "venue": venue,

        "last_matches": last_matches,

        "scheduled_matches": scheduled_matches,

        "season_fixtures": season_fixtures,

        "team_league_code": team_league_code,

        "standings": standings,

        "trophies": trophies,

        "squad": squad,

        "goalkeepers": goalkeepers,

        "defenders": defenders,

        "midfielders": midfielders,

        "attackers": attackers,

        "players_statistics": players_stats,

        "team_statistics": team_statistics,

        "team_leaders": team_leaders,

        "form": form,

        "wins_last5": wins,

        "draws_last5": draws,

        "losses_last5": losses,

        "next_match": next_match,

    }

    cache.set(
        cache_key,
        context,
        TEAM_DETAIL_CACHE_TTL
    )

    return render(

        request,

        "pages/team_detail.html",

        context

    )


def get_team_stats_full(team_id, season=SEASON):

    cache_key = f"compare_team_full_v1_{team_id}_{season}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    team = None

    try:

        team_response = requests.get(
            "https://v3.football.api-sports.io/teams",
            headers=headers,
            params={"id": team_id},
            timeout=15
        )

        team_data = team_response.json()

    except requests.RequestException:

        team_data = {}

    if team_data.get("response"):

        team_entry = team_data["response"][0]

        team = team_entry.get("team")

        if team:
            team["name"] = clean_team_name(team["name"])

    if not team:

        result = {
            "id": team_id,
            "name": "Unknown Team",
            "logo": None,
            "stats": {},
        }

        cache.set(cache_key, result, CACHE_TTL)

        return result

    try:

        response = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={"team": team_id, "season": season},
            timeout=15
        )

        data = response.json()

    except requests.RequestException:

        data = {}

    fixtures = data.get("response", [])

    team_statistics = {

        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,

        "goals_for": 0,
        "goals_against": 0,

        "goal_difference": 0,

        "clean_sheets": 0,

        "home_wins": 0,
        "away_wins": 0,

        "biggest_win": 0,
        "biggest_loss": 0,

    }

    for match in fixtures:

        if match["fixture"]["status"]["short"] != "FT":
            continue

        home_id = match["teams"]["home"]["id"]

        home_goals = match["goals"]["home"] or 0
        away_goals = match["goals"]["away"] or 0

        if home_id == int(team_id):
            goals_for = home_goals
            goals_against = away_goals
            is_home = True

        else:
            goals_for = away_goals
            goals_against = home_goals
            is_home = False

        team_statistics["played"] += 1

        team_statistics["goals_for"] += goals_for
        team_statistics["goals_against"] += goals_against

        if goals_against == 0:
            team_statistics["clean_sheets"] += 1

        diff = goals_for - goals_against

        if diff > team_statistics["biggest_win"]:
            team_statistics["biggest_win"] = diff

        if diff < team_statistics["biggest_loss"]:
            team_statistics["biggest_loss"] = diff

        if goals_for > goals_against:

            team_statistics["wins"] += 1

            if is_home:
                team_statistics["home_wins"] += 1
            else:
                team_statistics["away_wins"] += 1

        elif goals_for == goals_against:
            team_statistics["draws"] += 1

        else:
            team_statistics["losses"] += 1

    team_statistics["goal_difference"] = (
        team_statistics["goals_for"] - team_statistics["goals_against"]
    )

    if team_statistics["played"]:

        team_statistics["average_goals"] = round(
            team_statistics["goals_for"] / team_statistics["played"], 2
        )

        team_statistics["win_rate"] = round(
            team_statistics["wins"] * 100 / team_statistics["played"], 1
        )

    else:
        team_statistics["average_goals"] = 0
        team_statistics["win_rate"] = 0

    result = {
        "id": team.get("id") or team_id,
        "name": team.get("name"),
        "logo": team.get("logo"),
        "stats": team_statistics,
    }

    cache.set(cache_key, result, CACHE_TTL)

    return result


def build_team_comparison_rows(team1, team2):

    fields = [
        ("played", "Matches", ""),
        ("wins", "Wins", ""),
        ("draws", "Draws", ""),
        ("losses", "Losses", ""),
        ("home_wins", "Home Wins", ""),
        ("away_wins", "Away Wins", ""),
        ("win_rate", "Win Rate", "%"),
        ("goals_for", "Goals Scored", ""),
        ("goals_against", "Goals Conceded", ""),
        ("clean_sheets", "Clean Sheet", ""),
        ("average_goals", "Avg Goals", ""),
        ("biggest_win", "Biggest Win", ""),
        ("biggest_loss", "Big Defeat", ""),
    ]

    rows = []

    for key, label, suffix in fields:

        val1 = team1["stats"].get(key, 0) if team1 else 0
        val2 = team2["stats"].get(key, 0) if team2 else 0

        rows.append({
            "label": label,
            "val1": val1,
            "val2": val2,
            "suffix": suffix,
        })

    return rows


def compare_team(request, id):

    team1 = get_team_stats_full(id)

    team2 = None

    search_results = []

    query = request.GET.get("q")

    team2_id = request.GET.get("team2_id")

    if team2_id:

        team2 = get_team_stats_full(team2_id)

    elif query:

        search_cache_key = f"team_search_{query.lower()}"

        cached_search = cache.get(search_cache_key)

        if cached_search is not None:

            search_results = cached_search

        else:

            for league_code, league_info in LEAGUES.items():

                standings = get_standings(league_code)

                for row in standings:

                    team_row = row.get("team", {})

                    team_name = team_row.get("name", "")

                    if query.lower() in team_name.lower():

                        search_results.append({
                            "id": team_row.get("id"),
                            "name": team_name,
                            "logo": team_row.get("logo"),
                            "league_name": league_info["name"],
                        })

            cache.set(search_cache_key, search_results, CACHE_TTL)

    comparison_rows = []

    if team1 and team2:

        comparison_rows = build_team_comparison_rows(team1, team2)

    context = {

        "team1": team1,
        "team2": team2,
        "search_results": search_results,
        "query": query,
        "comparison_rows": comparison_rows,

    }

    return render(
        request,
        "pages/compare_team.html",
        context
    )


# ================= STANDINGS (جدول الترتيب - 10 دقائق) =================
def get_standings(code):

    league = LEAGUES[code]["id"]

    cache_key = f"standings_v2_{code}_{SEASON}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    url = (
        "https://v3.football.api-sports.io/"
        "standings"
    )

    try:
        response = requests.get(
            url,
            headers=headers,
            params={
                "league": league,
                "season": SEASON
            },
            timeout=15
        )

        data = response.json()

    except requests.RequestException:
        return []

    try:
        table = (
            data["response"][0]
            ["league"]
            ["standings"][0]
        )

    except (KeyError, IndexError, TypeError):
        table = []

    for row in table:
        row["team"]["name"] = clean_team_name(
            row["team"]["name"]
        )

    cache.set(cache_key, table, STANDINGS_CACHE_TTL)

    return table


def competition_standings(request, code):

    if code not in LEAGUES:

        return render(
            request,
            "404.html",
            status=404
        )

    table = get_standings(code)

    context = {
        "live_table": table,
        "competition": LEAGUES[code],
        "competitions": LEAGUES,
        "code": code,
    }

    return render(
        request,
        LEAGUES[code]["standings_template"],
        context
    )


def standings(request):

    return competition_standings(
        request,
        "PL"
    )


def competition(request, code, matchday=None):

    if code not in LEAGUES:
        return render(request, "404.html")

    if matchday is None:
        matchday = get_current_matchday(code)
    else:
        matchday = int(matchday)

    data, games = get_matches(code, matchday)

    config = LEAGUES[code]

    return render(

        request,

        config["template"],

        {

            **get_common_context(),

            "competition": config,

            "matches": games,

            "code": code,

            "matchday": matchday,

            "previous_matchday": max(1, matchday - 1),

            "next_matchday": min(config["max_matchday"], matchday + 1),

        }

    )


# ================= LEAGUE STATISTICS (إحصائيات البطولة - نصف ساعة) =================
def league_statistics(request, code):

    if code not in LEAGUES:
        return render(
            request,
            "404.html",
            status=404
        )

    league_id = LEAGUES[code]["id"]

    cache_key = f"league_statistics_v2_{code}_{SEASON}"

    cached = cache.get(cache_key)

    if cached is not None:
        return render(
            request,
            "pages/league_statistics.html",
            cached
        )

    def fetch_player_leaders(endpoint):
        url = f"https://v3.football.api-sports.io/players/{endpoint}"

        try:
            response = requests.get(
                url,
                headers=headers,
                params={
                    "league": league_id,
                    "season": SEASON
                },
                timeout=15
            )

            data = response.json()

        except requests.RequestException:
            return []

        entries = data.get("response", [])

        leaders = []

        for entry in entries:
            player = entry.get("player", {})
            stats_list = entry.get("statistics", [])

            if not stats_list:
                continue

            stats = stats_list[0]
            team = stats.get("team", {})

            leaders.append({
                "player_id": player.get("id"),
                "player_name": player.get("name"),
                "player_photo": player.get("photo"),
                "team_name": clean_team_name(team.get("name", "")),
                "team_logo": team.get("logo"),
                "goals": stats.get("goals", {}).get("total") or 0,
                "assists": stats.get("goals", {}).get("assists") or 0,
                "yellow_cards": stats.get("cards", {}).get("yellow") or 0,
                "red_cards": stats.get("cards", {}).get("red") or 0,
                "appearances": stats.get("games", {}).get("appearences") or 0,
            })

        return leaders

    top_scorers = fetch_player_leaders("topscorers")

    top_assists = fetch_player_leaders("topassists")

    top_yellow_cards = fetch_player_leaders("topyellowcards")

    top_red_cards = fetch_player_leaders("topredcards")

    standings = get_standings(code)

    top_scoring_teams = sorted(
        standings,
        key=lambda row: row.get("all", {}).get("goals", {}).get("for", 0),
        reverse=True
    )[:10]

    best_defense_teams = sorted(
        standings,
        key=lambda row: row.get("all", {}).get("goals", {}).get("against", 0)
    )[:10]

    context = {

        "competition": LEAGUES[code],

        "competitions": LEAGUES,

        "code": code,

        "top_scorers": top_scorers,

        "top_assists": top_assists,

        "top_yellow_cards": top_yellow_cards,

        "top_red_cards": top_red_cards,

        "top_scoring_teams": top_scoring_teams,

        "best_defense_teams": best_defense_teams,

    }

    cache.set(cache_key, context, LEAGUE_STATS_CACHE_TTL)

    return render(

        request,

        "pages/league_statistics.html",

        context

    )


def search_teams(request):

    query = request.GET.get("q", "").strip()

    results = []

    if query:

        for league_code, league_info in LEAGUES.items():

            standings = get_standings(league_code)

            for row in standings:

                team = row.get("team", {})
                team_name = team.get("name", "")

                if query.lower() in team_name.lower():

                    results.append({
                        "id": team.get("id"),
                        "name": team_name,
                        "logo": team.get("logo"),
                        "league_name": league_info["name"],
                        "league_code": league_code,
                    })

    return render(

        request,

        "pages/search_results.html",

        {

            "query": query,

            "results": results,

            "competitions": LEAGUES,

        }

    )


def signup(request):

    if request.method == "POST":

        form = SignUpForm(request.POST)

        if form.is_valid():

            user = form.save()

            login(request, user)

            return redirect("matches")

    else:
        form = SignUpForm()

    return render(
        request,
        "registration/signup.html",
        {
            "form": form,
        }
    )


@login_required
def submit_prediction(request, match_id):

    game = None

    try:
        response = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers,
            params={"id": match_id},
            timeout=15
        )

        data = response.json()

        fixtures = data.get("response", [])

        if fixtures:
            f = fixtures[0]

            game = {
                "home_name": f["teams"]["home"]["name"],
                "home_logo": f["teams"]["home"]["logo"],
                "away_name": f["teams"]["away"]["name"],
                "away_logo": f["teams"]["away"]["logo"],
                "competition_name": f["league"]["name"],
                "competition_logo": f["league"]["logo"],
                "date": f["fixture"]["date"],
            }

    except requests.RequestException:
        game = None

    existing_prediction = Prediction.objects.filter(
        user=request.user,
        match_id=match_id
    ).first()

    if request.method == "POST":

        home_score = request.POST.get("home_score")
        away_score = request.POST.get("away_score")

        try:
            home_score = int(home_score)
            away_score = int(away_score)

            if home_score < 0 or away_score < 0:
                raise ValueError

        except (TypeError, ValueError):

            return render(
                request,
                "pages/predict_error.html",
                {
                    "message": "الرجاء إدخال أرقام صحيحة وموجبة للنتيجة",
                }
            )

        Prediction.objects.update_or_create(
            user=request.user,
            match_id=match_id,
            defaults={
                "predicted_home_score": home_score,
                "predicted_away_score": away_score,
            }
        )

        return redirect("match_detail", id=match_id)

    return render(
        request,
        "pages/predict_form.html",
        {
            "match_id": match_id,
            "game": game,
            "existing_prediction": existing_prediction,
        }
    )



def predictions_page(request, code, matchday=None):

    if code not in LEAGUES:
        return render(request, "404.html", status=404)

    if matchday is None:
        matchday = get_current_matchday(code)
    else:
        matchday = int(matchday)

    user_stats = None

    if request.user.is_authenticated:
        all_users = (
            User.objects
            .annotate(total_points=Sum("predictions__points_earned"))
            .order_by("-total_points")
        )

        rank = 1

        for u in all_users:
            if u.id == request.user.id:
                break
            rank += 1

        predictions = Prediction.objects.filter(user=request.user)

        user_stats = {
            "rank": rank,
            "points": sum(p.points_earned or 0 for p in predictions),
            "predictions": predictions.count(),
        }


    competition, matches = get_matches(code, matchday)

    if request.user.is_authenticated:
        match_ids = [m["id"] for m in matches]

        user_predictions = {
            p.match_id: p
            for p in Prediction.objects.filter(
                user=request.user,
                match_id__in=match_ids
            )
        }

        for m in matches:
            m["prediction"] = user_predictions.get(m["id"])

    else:
        for m in matches:
            m["prediction"] = None

    max_matchday = LEAGUES[code]["max_matchday"]

    previous_matchday = matchday - 1 if matchday > 1 else None
    next_matchday = matchday + 1 if matchday < max_matchday else None

    context = {

        **get_common_context(),

        "code": code,

        "competition": competition,

        "matches": matches,

        "matchday": matchday,

        "previous_matchday": previous_matchday,

        "next_matchday": next_matchday,

        "user_stats": user_stats,

    }

    return render(request, "pages/predictions.html", context)


def leaderboard(request):

    users = (
        User.objects
        .annotate(
            total_points=Sum("predictions__points_earned"),
            total_predictions=Count(
                "predictions",
                filter=Q(predictions__points_earned__isnull=False)
            ),
        )
        .exclude(total_points__isnull=True)
        .order_by("-total_points")
    )

    return render(
        request,
        "pages/leaderboard.html",
        {
            "users": users,
        }
    )


def news_list(request, code=None):

    articles = NewsArticle.objects.all()

    if code:
        articles = articles.filter(league_code=code)

    return render(
        request,
        "pages/news_list.html",
        {
            "articles": articles,
            "code": code,
            "competitions": LEAGUES,
        }
    )


def news_detail(request, id):

    article = get_object_or_404(NewsArticle, id=id)

    return render(
        request,
        "pages/news_detail.html",
        {
            "article": article,
        }
    )


def get_team_squad_positions(team_id):

    cache_key = f"squad_positions_{team_id}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    try:
        response = requests.get(
            "https://v3.football.api-sports.io/players/squads",
            headers=headers,
            params={"team": team_id},
            timeout=15
        )

        data = response.json()

    except requests.RequestException:
        return {}

    squads = data.get("response", [])

    if not squads:
        return {}

    positions = {}

    for p in squads[0].get("players", []):
        positions[p["id"]] = p.get("position")

    cache.set(cache_key, positions, CACHE_TTL)

    return positions


def get_team_squad_info(team_id):

    cache_key = f"squad_info_{team_id}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    try:
        response = requests.get(
            "https://v3.football.api-sports.io/players/squads",
            headers=headers,
            params={"team": team_id},
            timeout=15
        )

        data = response.json()

    except requests.RequestException:
        return {}

    squads = data.get("response", [])

    if not squads:
        return {}

    squad_info = {}

    for p in squads[0].get("players", []):
        squad_info[p["id"]] = {
            "position": p.get("position"),
            "photo": p.get("photo"),
        }

    cache.set(cache_key, squad_info, CACHE_TTL)

    return squad_info


def get_matchday_players(code, matchday):

    cache_key = f"matchday_players_{code}_{SEASON}_{matchday}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    competition, matches = get_matches(code, matchday)

    all_players = []

    position_map = {
        "Goalkeeper": "حراسة",
        "Defender": "دفاع",
        "Midfielder": "وسط",
        "Attacker": "هجوم",
    }

    for match in matches:

        try:
            response = requests.get(
                "https://v3.football.api-sports.io/fixtures/lineups",
                headers=headers,
                params={"fixture": match["id"]},
                timeout=15
            )

            data = response.json()

        except requests.RequestException:
            continue

        for team_data in data.get("response", []):

            team_name = clean_team_name(team_data["team"]["name"])
            team_logo = team_data["team"]["logo"]
            team_id = team_data["team"]["id"]

            squad_info = get_team_squad_info(team_id)

            for item in team_data.get("startXI", []):

                player = item.get("player", {})
                player_id = player.get("id")

                player_squad_info = squad_info.get(player_id, {})

                english_position = player_squad_info.get("position")
                player_photo = player_squad_info.get("photo")

                if english_position:
                    position_group = position_map.get(english_position, "غير محدد")
                else:
                    fallback_map = {
                        "G": "حراسة",
                        "D": "دفاع",
                        "M": "وسط",
                        "F": "هجوم",
                    }
                    position_group = fallback_map.get(player.get("pos"), "غير محدد")

                all_players.append({
                    "id": player_id,
                    "name": player.get("name"),
                    "number": player.get("number"),
                    "photo": player_photo,
                    "team_name": team_name,
                    "team_logo": team_logo,
                    "position_group": position_group,
                })

    cache.set(cache_key, all_players, CACHE_TTL)

    return all_players


@login_required
def team_of_week_form(request, code, matchday):

    if code not in LEAGUES:
        return render(
            request,
            "404.html",
            status=404
        )

    eligible_players = get_matchday_players(code, matchday)

    existing_team = FanTeamOfWeek.objects.filter(
        user=request.user,
        league_code=code,
        matchday=matchday
    ).first()

    existing_player_ids = set()

    if existing_team:
        existing_player_ids = set(
            existing_team.players.values_list("player_id", flat=True)
        )

    if request.method == "POST":

        selected_ids = request.POST.getlist("players")

        if len(selected_ids) != 11:

            return render(
                request,
                "pages/predict_error.html",
                {
                    "message": "لازم تختار ١١ لاعب بالضبط، لا أكثر ولا أقل",
                }
            )

        selected_ids = [int(pid) for pid in selected_ids]

        players_by_id = {p["id"]: p for p in eligible_players}

        fan_team, _ = FanTeamOfWeek.objects.get_or_create(
            user=request.user,
            league_code=code,
            matchday=matchday
        )

        fan_team.players.all().delete()

        for pid in selected_ids:

            player = players_by_id.get(pid)

            if not player:
                continue

            FanTeamPlayer.objects.create(
                fan_team=fan_team,
                player_id=player["id"],
                player_name=player["name"],
                team_name=player["team_name"],
                team_logo=player["team_logo"],
                position_group=player["position_group"],
            )

        return redirect(
            "team_of_week_view",
            code=code,
            matchday=matchday,
        )

    return render(
        request,
        "pages/team_of_week_form.html",
        {
            "code": code,
            "matchday": matchday,
            "eligible_players": eligible_players,
            "existing_player_ids": list(existing_player_ids),
        }
    )


def team_of_week_view(request, code, matchday, user_id):

    fan_team = get_object_or_404(
        FanTeamOfWeek,
        league_code=code,
        matchday=matchday,
        user=request.user
    )

    return render(
        request,
        "pages/team_of_week_view.html",
        {
            "fan_team": fan_team,
            "players": fan_team.players.all(),
            "code": code,
            "matchday": matchday,
        }
    )


@login_required
def profile(request):

    user = request.user

    total_predictions = user.predictions.count()

    total_points = (
        user.predictions
        .aggregate(
            total=Sum("points_earned")
        )
        ["total"]
        or 0
    )

    correct_predictions = (
        user.predictions
        .filter(
            points_earned__gt=0
        )
        .count()
    )

    accuracy = 0

    if total_predictions:
        accuracy = round(
            (correct_predictions / total_predictions) * 100
        )

    users = (
        User.objects
        .annotate(
            ranking_points=Sum(
                "predictions__points_earned"
            )
        )
        .order_by(
            "-ranking_points"
        )
    )

    rank = None

    for index, u in enumerate(users, start=1):

        if u.id == user.id:
            rank = index
            break

    return render(
        request,
        "pages/profile.html",
        {
            "total_predictions": total_predictions,
            "total_points": total_points,
            "correct_predictions": correct_predictions,
            "accuracy": accuracy,
            "rank": rank,
        }
    )


# ================= PLAYER DETAIL (تفاصيل اللاعب - ساعة واحدة) =================
def player_detail(request, id):

    cache_key = f"player_detail_v3_{id}"

    cached = cache.get(cache_key)

    if cached is not None:
        return render(
            request,
            "pages/player_detail.html",
            cached
        )

    player_response = requests.get(

        "https://v3.football.api-sports.io/players",

        headers=headers,

        params={
            "id": id,
            "season": SEASON
        },

        timeout=15

    )

    player_json = player_response.json()

    if not player_json.get("response"):

        return render(
            request,
            "pages/player_detail.html",
            {
                "error": "Player data unavailable",
                "player": {"id": id},
            }
        )

    player_data = player_json["response"][0]

    player_info = player_data["player"]

    statistics = player_data.get("statistics", [])

    competition_stats = []

    for stat in statistics:
        league = stat.get("league", {})

        games = stat.get("games", {})
        goals = stat.get("goals", {})
        passes = stat.get("passes", {})
        shots = stat.get("shots", {})
        cards = stat.get("cards", {})

        competition_stats.append({

            "league_name": league.get("name"),

            "league_logo": league.get("logo"),

            "team_name": stat.get("team", {}).get("name"),

            "appearances": games.get("appearences") or 0,

            "minutes": games.get("minutes") or 0,

            "rating": games.get("rating") or 0,

            "goals": goals.get("total") or 0,

            "assists": goals.get("assists") or 0,

            "shots": shots.get("total") or 0,

            "shots_on": shots.get("on") or 0,

            "passes": passes.get("total") or 0,

            "pass_accuracy": passes.get("accuracy") or 0,

            "key_passes": passes.get("key") or 0,

            "yellow": cards.get("yellow") or 0,

            "red": cards.get("red") or 0,

        })

    defense_competition_stats = []

    defense_total = {
        "tackles": 0,
        "blocks": 0,
        "interceptions": 0,
        "duels_total": 0,
        "duels_won": 0,
        "fouls_committed": 0,
        "fouls_drawn": 0,
        "penalty_committed": 0,
        "saves": 0,
        "goals_conceded": 0,
    }

    for stat in statistics:

        league = stat.get("league", {})

        tackles = stat.get("tackles", {})
        duels = stat.get("duels", {})
        fouls = stat.get("fouls", {})
        penalty = stat.get("penalty", {})
        goals = stat.get("goals", {})

        defense_total["tackles"] += (tackles.get("total") or 0)

        defense_total["blocks"] += (tackles.get("blocks") or 0)

        defense_total["interceptions"] += (tackles.get("interceptions") or 0)

        defense_total["duels_total"] += (duels.get("total") or 0)

        defense_total["duels_won"] += (duels.get("won") or 0)

        defense_total["fouls_committed"] += (fouls.get("committed") or 0)

        defense_total["fouls_drawn"] += (fouls.get("drawn") or 0)

        defense_total["penalty_committed"] += (penalty.get("committed") or 0)

        defense_total["saves"] += (goals.get("saves") or 0)

        defense_total["goals_conceded"] += (goals.get("conceded") or 0)

        defense_competition_stats.append({

            "league_name": league.get("name"),

            "league_logo": league.get("logo"),

            "tackles": tackles.get("total") or 0,

            "blocks": tackles.get("blocks") or 0,

            "interceptions": tackles.get("interceptions") or 0,

            "duels_total": duels.get("total") or 0,

            "duels_won": duels.get("won") or 0,

            "fouls_committed": fouls.get("committed") or 0,

        })

    defense_stats = defense_total

    goalkeeper_competition_stats = []

    goalkeeper_total = {
        "appearances": 0,
        "saves": 0,
        "goals_conceded": 0,
        "clean_sheets": 0,
        "penalty_saved": 0,
        "save_percentage_values": [],
    }

    for stat in statistics:

        league = stat.get("league", {})

        games = stat.get("games", {})

        goals = stat.get("goals", {})

        penalty = stat.get("penalty", {})

        saves = goals.get("saves") or 0

        conceded = goals.get("conceded") or 0

        shots_faced = saves + conceded

        save_percentage = 0

        if shots_faced > 0:
            save_percentage = round(
                (saves / shots_faced) * 100
            )

        goalkeeper_total["appearances"] += (games.get("appearences") or 0)

        goalkeeper_total["saves"] += saves

        goalkeeper_total["goals_conceded"] += conceded

        goalkeeper_total["clean_sheets"] += (
            stat.get("clean_sheet", {}).get("total") or 0
        )

        goalkeeper_total["penalty_saved"] += (penalty.get("saved") or 0)

        if save_percentage:
            goalkeeper_total["save_percentage_values"].append(
                save_percentage
            )

        goalkeeper_competition_stats.append({
            "league_name": league.get("name"),

            "league_logo": league.get("logo"),

            "appearances": games.get("appearences") or 0,

            "saves": saves,

            "goals_conceded": conceded,

            "save_percentage": save_percentage,

            "clean_sheets": stat.get("clean_sheet", {}).get("total") or 0,

            "penalty_saved": penalty.get("saved") or 0,

        })

    goalkeeper_stats = {
        "appearances": goalkeeper_total["appearances"],

        "saves": goalkeeper_total["saves"],

        "goals_conceded": goalkeeper_total["goals_conceded"],

        "clean_sheets": goalkeeper_total["clean_sheets"],

        "penalty_saved": goalkeeper_total["penalty_saved"],

        "save_percentage":
            round(
                sum(goalkeeper_total["save_percentage_values"]) /
                len(goalkeeper_total["save_percentage_values"]),
                2
            )
            if goalkeeper_total["save_percentage_values"]
            else 0,

    }

    player = {

        "id": player_info.get("id") or id,

        "name": player_info.get("name"),

        "photo": player_info.get("photo"),

        "age": player_info.get("age"),

        "nationality": player_info.get("nationality"),

        "height": player_info.get("height"),

        "weight": player_info.get("weight"),

    }

    player_stats = {}

    if statistics:

        stat = statistics[0]

        player["team"] = {
            "name": stat["team"]["name"],
            "logo": stat["team"]["logo"],
        }

        player["position"] = stat.get("games", {}).get("position")

        total = {
            "appearances": 0,
            "goals": 0,
            "assists": 0,
            "shots": 0,
            "shots_on": 0,
            "key_passes": 0,
            "dribbles": 0,
            "passes": 0,
            "ratings": [],
        }

        for stat in statistics:

            total["appearances"] += (stat.get("games", {}).get("appearences") or 0)

            total["goals"] += (stat.get("goals", {}).get("total") or 0)

            total["assists"] += (stat.get("goals", {}).get("assists") or 0)

            total["shots"] += (stat.get("shots", {}).get("total") or 0)

            total["shots_on"] += (stat.get("shots", {}).get("on") or 0)

            total["key_passes"] += (stat.get("passes", {}).get("key") or 0)

            total["dribbles"] += (stat.get("dribbles", {}).get("success") or 0)

            total["passes"] += (stat.get("passes", {}).get("total") or 0)

            rating = stat.get("games", {}).get("rating")

            if rating:

                total["ratings"].append(
                    float(rating)
                )

        player_stats = {

            "appearances": total["appearances"],

            "goals": total["goals"],

            "assists": total["assists"],

            "rating":
                round(
                    sum(total["ratings"]) / len(total["ratings"]),
                    2
                )
                if total["ratings"] else 0,

            "shots": total["shots"],

            "shots_on": total["shots_on"],

            "key_passes": total["key_passes"],

            "dribbles": total["dribbles"],

            "passes": total["passes"],

            "pass_accuracy": stat.get("passes", {}).get("accuracy", 0),

        }

    context = {

        "player": player,

        "player_stats": player_stats,

        "defense_stats": defense_stats,

        "goalkeeper_stats": goalkeeper_stats,

        "competition_stats": competition_stats,

        "defense_competition_stats": defense_competition_stats,

        "goalkeeper_competition_stats": goalkeeper_competition_stats,

    }

    cache.set(cache_key, context, PLAYER_DETAIL_CACHE_TTL)

    return render(

        request,

        "pages/player_detail.html",

        context

    )


def search(request):

    query = request.GET.get("q")

    results = []

    if query:

        teams_response = requests.get(

            "https://v3.football.api-sports.io/teams",

            headers=headers,

            params={
                "search": query
            },

            timeout=15

        )

        teams_json = teams_response.json()

        for item in teams_json.get("response", []):

            team = item["team"]

            results.append({

                "type": "team",

                "id": team["id"],

                "name": team["name"],

                "logo": team["logo"]

            })

        players_response = requests.get(

            "https://v3.football.api-sports.io/players",

            headers=headers,

            params={
                "search": query
            },

            timeout=15

        )

        players_json = players_response.json()

        for item in players_json.get("response", []):

            player = item["player"]

            results.append({
                "type": "player",

                "id": player["id"],

                "name": player["name"],

                "photo": player.get("photo")

            })

    context = {

        "query": query,

        "results": results

    }

    return render(

        request,

        "pages/search.html",

        context

    )


POSITION_CATEGORY = {
    "Goalkeeper": "goalkeeping",
    "Defender": "defense",
    "Midfielder": "attack",
    "Attacker": "attack",
}


def get_player_full(player_id, season=SEASON):

    cache_key = f"compare_player_full_v2_{player_id}_{season}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    try:
        response = requests.get(
            "https://v3.football.api-sports.io/players",
            headers=headers,
            params={"id": player_id, "season": season},
            timeout=15
        )

        data = response.json()

    except requests.RequestException:
        return {
            "id": player_id,
            "name": "Unknown Player",
            "photo": None,
            "position": None,
            "team_name": "",
            "team_logo": None,
            "stats": {},
        }

    results = data.get("response", [])

    if not results:
        result = {
            "id": player_id,
            "name": "Unknown Player",
            "photo": None,
            "position": None,
            "team_name": "",
            "team_logo": None,
            "stats": {},
        }

        cache.set(cache_key, result, CACHE_TTL)

        return result

    entry = results[0]

    player_info = entry.get("player", {})

    statistics_list = entry.get("statistics", [])

    for stat in statistics_list:

        league = stat.get("league", {}) or {}

        league_type = (league.get("type") or "").strip().lower()

        league_name = (league.get("name") or "").strip().lower()

        if league_type == "friendlies" or "friendlies" in league_name:
            continue

        games = stat.get("games", {}) or {}

    first_stat = statistics_list[0] if statistics_list else {}

    position = first_stat.get("games", {}).get("position")

    team = first_stat.get("team", {}) or {}

    total = {
        "appearances": 0,
        "minutes": 0,
        "ratings": [],

        "goals": 0,
        "assists": 0,
        "shots": 0,
        "shots_on": 0,
        "passes": 0,
        "key_passes": 0,
        "dribbles": 0,
        "pass_accuracy_values": [],

        "tackles": 0,
        "blocks": 0,
        "interceptions": 0,
        "duels_won": 0,
        "duels_total": 0,
        "fouls_committed": 0,
        "fouls_drawn": 0,

        "saves": 0,
        "goals_conceded": 0,
        "penalty_saved": 0,

        "yellow": 0,
        "red": 0,
    }

    for stat in statistics_list:

        games = stat.get("games", {}) or {}
        goals = stat.get("goals", {}) or {}
        shots = stat.get("shots", {}) or {}
        passes = stat.get("passes", {}) or {}
        dribbles = stat.get("dribbles", {}) or {}
        tackles = stat.get("tackles", {}) or {}
        duels = stat.get("duels", {}) or {}
        fouls = stat.get("fouls", {}) or {}
        penalty = stat.get("penalty", {}) or {}
        cards = stat.get("cards", {}) or {}

        total["appearances"] += games.get("appearences") or 0
        total["minutes"] += games.get("minutes") or 0

        rating = games.get("rating")
        if rating:
            try:
                total["ratings"].append(float(rating))
            except (TypeError, ValueError):
                pass

        total["goals"] += goals.get("total") or 0
        total["assists"] += goals.get("assists") or 0
        total["shots"] += shots.get("total") or 0
        total["shots_on"] += shots.get("on") or 0
        total["passes"] += passes.get("total") or 0
        total["key_passes"] += passes.get("key") or 0
        total["dribbles"] += dribbles.get("success") or 0

        pass_acc = passes.get("accuracy")
        if pass_acc:
            try:
                total["pass_accuracy_values"].append(float(pass_acc))
            except (TypeError, ValueError):
                pass

        total["tackles"] += tackles.get("total") or 0
        total["blocks"] += tackles.get("blocks") or 0
        total["interceptions"] += tackles.get("interceptions") or 0
        total["duels_won"] += duels.get("won") or 0
        total["duels_total"] += duels.get("total") or 0
        total["fouls_committed"] += fouls.get("committed") or 0
        total["fouls_drawn"] += fouls.get("drawn") or 0

        total["saves"] += goals.get("saves") or 0
        total["goals_conceded"] += goals.get("conceded") or 0
        total["penalty_saved"] += penalty.get("saved") or 0

        total["yellow"] += cards.get("yellow") or 0
        total["red"] += cards.get("red") or 0

    parsed_stats = {

        "appearances": total["appearances"],
        "minutes": total["minutes"],
        "rating": round(sum(total["ratings"]) / len(total["ratings"]), 2) if total["ratings"] else 0,

        "goals": total["goals"],
        "assists": total["assists"],
        "shots": total["shots"],
        "shots_on": total["shots_on"],
        "passes": total["passes"],
        "key_passes": total["key_passes"],
        "dribbles": total["dribbles"],
        "pass_accuracy": round(sum(total["pass_accuracy_values"]) / len(total["pass_accuracy_values"]), 1) if total["pass_accuracy_values"] else 0,

        "tackles": total["tackles"],
        "blocks": total["blocks"],
        "interceptions": total["interceptions"],
        "duels_won": total["duels_won"],
        "duels_total": total["duels_total"],
        "fouls_committed": total["fouls_committed"],
        "fouls_drawn": total["fouls_drawn"],

        "saves": total["saves"],
        "goals_conceded": total["goals_conceded"],
        "penalty_saved": total["penalty_saved"],

        "yellow": total["yellow"],
        "red": total["red"],

    }

    result = {
        "id": player_info.get("id") or player_id,
        "name": player_info.get("name"),
        "photo": player_info.get("photo"),
        "age": player_info.get("age"),
        "nationality": player_info.get("nationality"),
        "position": position,
        "team_name": clean_team_name(team.get("name", "")) if team else "",
        "team_logo": team.get("logo"),
        "stats": parsed_stats,
    }

    cache.set(cache_key, result, CACHE_TTL)

    return result


def build_comparison_rows(player1, player2, comparison_type):

    field_map = {

        "attack": [
            ("rating", "Rating", ""),
            ("goals", "Goals", ""),
            ("assists", "Assists", ""),
            ("shots", "Shots", ""),
            ("shots_on", "Shots On Target", ""),
            ("key_passes", "Key Passes", ""),
            ("dribbles", "Dribbles", ""),
            ("passes", "Total Passes", ""),
            ("pass_accuracy", "Pass Accuracy", "%"),
            
        ],

        "defense": [
            ("rating", "Rating", ""),
            ("tackles", "Tackles", ""),
            ("blocks", "Blocks", ""),
            ("interceptions", "Interceptions", ""),
            ("duels_won", "Duels Won", ""),
            ("duels_total", "Total Duels", ""),
            ("fouls_committed", "Fouls Committed", ""),
            ("fouls_drawn", "Fouls Drawn", ""),
            
        ],

        "goalkeeping": [
            ("rating", "Rating", ""),
            ("saves", "Saves", ""),
            ("goals_conceded", "Goals Conceded", ""),
            ("penalty_saved", "Penalty Saves", ""),
            ("appearances", "Appearances", ""),
            
        ],

    }

    fields = field_map.get(comparison_type, field_map["attack"])

    rows = []

    for key, label, suffix in fields:

        val1 = player1["stats"].get(key, 0) if player1 else 0
        val2 = player2["stats"].get(key, 0) if player2 else 0

        rows.append({
            "label": label,
            "val1": val1,
            "val2": val2,
            "suffix": suffix,
        })

    return rows


def compare_player(request, id):

    player1 = get_player_full(id)

    player2 = None

    search_results = []

    query = request.GET.get("q")

    player2_id = request.GET.get("player2_id")

    if player2_id:

        player2 = get_player_full(player2_id)

    elif query:

        search_cache_key = f"player_search_{query.lower()}_{SEASON}"

        cached_search = cache.get(search_cache_key)

        if cached_search is not None:

            search_results = cached_search

        else:

            search_json_response = []

            BIG_FIVE_CODES = ["PL", "PD", "SA", "BL1", "FL1"]

            existing_ids = set()

            for league_code in BIG_FIVE_CODES:

                league_info = LEAGUES.get(league_code)

                if not league_info or "id" not in league_info:
                    continue

                league_id = league_info["id"]

                try:

                    search_response = requests.get(

                        "https://v3.football.api-sports.io/players",

                        headers=headers,

                        params={
                            "search": query,
                            "league": league_id,
                            "season": SEASON,
                        },

                        timeout=15

                    )

                    temp_json = search_response.json()

                except requests.RequestException:

                    continue

                results = temp_json.get("response", [])

                for item in results:

                    player_id = item.get("player", {}).get("id")

                    if player_id and player_id not in existing_ids:

                        search_json_response.append(item)
                        existing_ids.add(player_id)

            for item in search_json_response:

                player = item.get("player", {})

                statistics_list = item.get("statistics", [])

                stats = statistics_list[0] if statistics_list else {}

                team = stats.get("team", {}) or {}

                search_results.append({

                    "id": player.get("id"),
                    "name": player.get("name"),
                    "photo": player.get("photo"),
                    "position": stats.get("games", {}).get("position"),
                    "team_name": clean_team_name(team.get("name", "")) if team else "",

                })

            cache.set(search_cache_key, search_results, CACHE_TTL)

    comparison_type = "attack"

    if player1:

        comparison_type = POSITION_CATEGORY.get(
            player1.get("position"),
            "attack"
        )

    comparison_rows = []

    if player1 and player2:

        comparison_rows = build_comparison_rows(
            player1,
            player2,
            comparison_type
        )

    context = {

        "player1": player1,
        "player2": player2,
        "search_results": search_results,
        "query": query,
        "comparison_type": comparison_type,
        "comparison_rows": comparison_rows,

    }

    return render(
        request,
        "pages/compare_player.html",
        context
    )


def team_statistics(request, id):

    cache_key = f"team_statistics_{id}"

    cached = cache.get(cache_key)

    if cached is not None:
        return render(
            request,
            "pages/team_statistics.html",
            cached
        )

    team = None

    try:

        team_response = requests.get(
            "https://v3.football.api-sports.io/teams",
            headers=headers,
            params={
                "id": id
            },
            timeout=15
        )

        team_json = team_response.json()

        if team_json.get("response"):

            team = team_json["response"][0]["team"]

            team["name"] = clean_team_name(
                team["name"]
            )

    except requests.RequestException:
        pass

    statistics = {}

    try:

        response = requests.get(
            "https://v3.football.api-sports.io/teams/statistics",
            headers=headers,
            params={
                "team": id,
                "season": SEASON,
                "league": LEAGUES["PL"]["id"]
            },
            timeout=20
        )

        data = response.json()

        if data.get("response"):

            statistics = data["response"]

    except requests.RequestException:
        pass

    players_stats = []

    page = 1

    while True:

        try:

            response = requests.get(
                "https://v3.football.api-sports.io/players",
                headers=headers,
                params={
                    "team": id,
                    "season": SEASON,
                    "league": LEAGUES["PL"]["id"],
                    "page": page
                },
                timeout=20
            )

            data = response.json()

        except requests.RequestException:
            break

        players_stats.extend(
            data.get("response", [])
        )

        paging = data.get("paging", {})

        if paging.get("current") >= paging.get("total"):
            break

        page += 1

    context = {

        "team": team,
        "statistics": statistics,
        "players_stats": players_stats

    }

    cache.set(
        cache_key,
        context,
        CACHE_TTL
    )

    return render(
        request,
        "pages/team_statistics.html",
        context
    )


# ================= CUP MATCHES (BY ROUND - جدول مباريات الكؤوس - دقيقة واحدة) =================
def get_cup_rounds(code):

    league_info = LEAGUES.get(code)

    if not league_info or "id" not in league_info:
        return []

    league_id = league_info["id"]

    cache_key = f"cup_rounds_v2_{code}_{SEASON}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    url = "https://v3.football.api-sports.io/fixtures"

    params = {
        "league": league_id,
        "season": SEASON,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        data = response.json()
    except requests.RequestException:
        return []

    fixtures = data.get("response", [])

    rounds = defaultdict(list)

    for f in fixtures:

        round_name = f["league"].get("round") or "غير محدد"

        rounds[round_name].append({

            "id": f["fixture"]["id"],

            "homeTeam": {
                "id": f["teams"]["home"]["id"],
                "name": clean_team_name(f["teams"]["home"]["name"]),
                "crest": f["teams"]["home"]["logo"],
            },

            "awayTeam": {
                "id": f["teams"]["away"]["id"],
                "name": clean_team_name(f["teams"]["away"]["name"]),
                "crest": f["teams"]["away"]["logo"],
            },

            "score": {
                "fullTime": {
                    "home": f["goals"]["home"],
                    "away": f["goals"]["away"],
                }
            },

            "status": f["fixture"]["status"]["short"],

            "utcDate": to_mecca_time(f["fixture"]["date"]),
        })

    ordered_rounds = [
        {"round": name, "matches": matches}
        for name, matches in rounds.items()
    ]

    cache.set(cache_key, ordered_rounds, MATCHES_CACHE_TTL)

    return ordered_rounds





def cup_competition(request, code):

    competition = LEAGUES.get(code)

    if competition is None:
        raise Http404("Competition not found")

    competition = competition.copy()
    competition["theme_color"] = competition.get("theme_color", "#dc2626")

    rounds = get_cup_rounds(code)

    context = {

        "competition": competition,
        "competitions": LEAGUES,
        "countries": countries,
        "code": code,
        "cup_code": code,
        "rounds": rounds,
    }

    template_name = LEAGUES[code].get("template", "pages/cup_competition.html")

    return render(request, template_name, context)




from datetime import date as date_cls


from datetime import date as date_cls


def get_today_matches():

    today_str = date_cls.today().isoformat()

    cache_key = f"today_matches_v4_{today_str}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    league_ids = {
        info["id"]: code
        for code, info in LEAGUES.items()
    }

    grouped = []

    for code, info in LEAGUES.items():

        league_id = info["id"]

        url = "https://v3.football.api-sports.io/fixtures"

        params = {
            "league": league_id,
            "season": SEASON,
            "date": today_str,
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            data = response.json()
        except requests.RequestException:
            continue

        fixtures = data.get("response", [])

        if not isinstance(fixtures, list) or not fixtures:
            continue

        matches = []

        for f in fixtures:

            matches.append({

                "id": f["fixture"]["id"],

                "homeTeam": {
                    "id": f["teams"]["home"]["id"],
                    "name": clean_team_name(f["teams"]["home"]["name"]),
                    "crest": f["teams"]["home"]["logo"],
                },

                "awayTeam": {
                    "id": f["teams"]["away"]["id"],
                    "name": clean_team_name(f["teams"]["away"]["name"]),
                    "crest": f["teams"]["away"]["logo"],
                },

                "score": {
                    "fullTime": {
                        "home": f["goals"]["home"],
                        "away": f["goals"]["away"],
                    }
                },

                "status": f["fixture"]["status"]["short"],
                "elapsed": f["fixture"]["status"].get("elapsed"),
                "utcDate": to_mecca_time(f["fixture"]["date"]),

            })

        grouped.append({
            "code": code,
            "name": info["name"],
            "logo": info["logo"],
            "matches": matches,
        })

    cache.set(cache_key, grouped, MATCHES_CACHE_TTL)

    return grouped


def today_matches_view(request):

    grouped_matches = get_today_matches()

    context = {
        **get_common_context(),
        "grouped_matches": grouped_matches,
        "today": date_cls.today(),
    }

    return render(
        request,
        "pages/today_matches.html",
        context
    )