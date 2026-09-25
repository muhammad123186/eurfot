from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import match, team, Player, NewsArticle

# 1. خريطة الصفحات الثابتة والرئيسية
class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return [
            'matches',
            'premier_league_home',
            'standings',
            'search',
            'leaderboard',
            'news_list',
            'profile',
            'signup',
            'login',
            'privacy_policy',
            'about_us',
            'contact_us',
        ]

    def location(self, item):
        return reverse(item)


# 2. خريطة الدوريات الأساسية
class CompetitionSitemap(Sitemap):
    priority = 0.9
    changefreq = 'daily'

    def items(self):
        return ['PL', 'PD', 'SA', 'BL1', 'FL1']

    def location(self, item):
        return reverse('competition', args=[item])


# 3. خريطة الكؤوس والبطولات الأوروبية والمحلية الشاملة
class CupCompetitionSitemap(Sitemap):
    priority = 0.9
    changefreq = 'daily'

    def items(self):
        # جميع أكواد الكؤوس والبطولات المستخرجة من القاموس لدعم الأرشفة الكاملة
        return [
            'FAC', 'ELCUP', 'CDR', 'SC', 'COP', 
            'DSC', 'DFB', 'DSUP', 'CDF', 'TDC', 
            'UCL', 'UEL', 'UECL'
        ]

    def location(self, item):
        return reverse('cup_competition', args=[item])


# 4. خريطة تفاصيل المباريات
class MatchSitemap(Sitemap):
    priority = 0.9
    changefreq = 'hourly'

    def items(self):
        return match.objects.all()

    def location(self, obj):
        return reverse('match_detail', args=[obj.id])


# 5. خريطة الفرق والأندية
class TeamSitemap(Sitemap):
    priority = 0.7
    changefreq = 'weekly'

    def items(self):
        return team.objects.all()

    def location(self, obj):
        return reverse('team_detail', args=[obj.id])


# 6. خريطة اللاعبين
class PlayerSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return Player.objects.all()

    def location(self, obj):
        return reverse('player_detail', args=[obj.id])


# 7. خريطة الأخبار والمقالات
class NewsArticleSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return NewsArticle.objects.all()

    def location(self, obj):
        return reverse('news_detail', args=[obj.id])