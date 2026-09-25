from django.urls import path
from .import views
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from .sitemaps import (
    StaticViewSitemap,
    CompetitionSitemap,
    CupCompetitionSitemap,
    MatchSitemap,
    TeamSitemap,
    PlayerSitemap,
    NewsArticleSitemap
)

# تجميع خرائط الموقع في قاموس واحد
sitemaps = {
    'static': StaticViewSitemap,
    'competitions': CompetitionSitemap,
    'cups': CupCompetitionSitemap,
    'matches': MatchSitemap,
    'teams': TeamSitemap,
    'players': PlayerSitemap,
    'news': NewsArticleSitemap,
}


urlpatterns = [



    path("", views.today_matches_view, name="matches"),

    path("premier-league/", views.matches, name="premier_league_home"),

    path(
        "matches/<int:matchday>/",
        views.matches,
        name="matchday"
    ),

    path(
        "match/<int:id>/",
        views.match_detail,
        name="match_detail"
    ),

    path(
        "team/<int:id>/",
        views.team_detail,
        name="team_detail"
    ),

    path(
        "standings/",
        views.standings,
        name="standings"
    ),

    path(
        "competition/<str:code>/",
        views.competition,
        name="competition"
    ),

    path(
        "competition/<str:code>/<int:matchday>/",
        views.competition,
        name="competition_matchday"
    ),

    path(
        "competition/<str:code>/standings/",
        views.competition_standings,
        name="competition_standings"
    ),

    path(
        "competition/<str:code>/statistics/",
        views.league_statistics,
        name="league_statistics"
    ),


    path(
    "search/",
    views.search,
    name="search"
    ),

  
    path(
    "signup/",
    views.signup,
    name="signup"
    ),

    path(
    "login/",
    auth_views.LoginView.as_view(
        template_name="registration/login.html"
    ),
    name="login"
    ),

    path(
    "logout/",
    auth_views.LogoutView.as_view(
        template_name="registration/logout.html"
    ),
    name="logout"
    ),

    
    path(
    "predict/<int:match_id>/",
    views.submit_prediction,
    name="submit_prediction"
    ),

    path(
    "competition/<str:code>/predictions/<int:matchday>/",
    views.predictions_page,
    name="predictions_page"
    ),


    path(
    "leaderboard/",
    views.leaderboard,
    name="leaderboard"
    ),

    path(
    "news/",
    views.news_list,
    name="news_list"
    ),

    path(
    "news/<str:code>/",
    views.news_list,
    name="news_list_by_league"
    ),

    path(
    "news/article/<int:id>/",
    views.news_detail,
    name="news_detail"
    ),



    path(
    "competition/<str:code>/team-of-week/<int:matchday>/",
    views.team_of_week_form,
    name="team_of_week_form"
    ),

    path(
    "competition/<str:code>/team-of-week/<int:matchday>/",
    views.team_of_week_view,
    name="team_of_week_view"
    ),

    path(
    "profile/",
    views.profile,
    name="profile"
    ),


    path(
    "player/<int:id>/",
    views.player_detail,
    name="player_detail"
    ),

    path(
    "player/<int:id>/compare/",
    views.compare_player,
    name="compare_player"
    ),





    path(
    'cup/<str:code>/',
    views.cup_competition, 
    name='cup_competition'
    ),
    



    path('team/<int:id>/compare/', views.compare_team, name='compare_team'),


    path('google0648db8e851360e4.html', TemplateView.as_view(template_name="google0648db8e851360e4.html")),
    
    # مسار خريطة الموقع الشاملة
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),



    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('about-us/', views.about_us_view, name='about_us'),
    path('contact-us/', views.contact_us_view, name='contact_us'),
    path('google6bddb656cf72235a.html', TemplateView.as_view(template_name='google6bddb656cf72235a.html')),


]




