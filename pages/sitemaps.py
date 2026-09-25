from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import match, team, Player, NewsArticle

# 1. خريطة الصفحات الثابتة والرئيسية
class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return [
            'matches',              # الرئيسية ومباريات اليوم
            'premier_league_home',  # الدوري الإنجليزي
            'standings',            # الترتيب العام
            'search',               # البحث
            'leaderboard',          # لائحة المتصدرين
            'news_list',            # قائمة الأخبار
            'profile',              # الملف الشخصي
            'signup',               # إنشاء حساب
            'login',                # تسجيل الدخول
            'privacy_policy',       # سياسة الخصوصية
            'about_us',             # من نحن
            'contact_us',           # اتصل بنا
        ]

    def location(self, item):
        return reverse(item)


# 2. خريطة صفحات الدوريات والمسابقات الديناميكية
class CompetitionSitemap(Sitemap):
    priority = 0.9
    changefreq = 'daily'

    def items(self):
        # رموز المسابقات والدوريات التي تستخدمها في موقعك
        return ['PL', 'PD', 'SA', 'BL1', 'FL1', 'CL']

    def location(self, item):
        return reverse('competition', args=[item])


# 3. خريطة تفاصيل المباريات (Match Details) الديناميكية
class MatchSitemap(Sitemap):
    priority = 0.9
    changefreq = 'hourly'

    def items(self):
        return match.objects.all()

    def location(self, obj):
        return reverse('match_detail', args=[obj.id])


# 4. خريطة الفرق والأندية (Teams)
class TeamSitemap(Sitemap):
    priority = 0.7
    changefreq = 'weekly'

    def items(self):
        return team.objects.all()

    def location(self, obj):
        return reverse('team_detail', args=[obj.id])


# 5. خريطة اللاعبين (Players)
class PlayerSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return Player.objects.all()

    def location(self, obj):
        return reverse('player_detail', args=[obj.id])


# 6. خريطة الأخبار والمقالات (News Articles)
class NewsArticleSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return NewsArticle.objects.all()

    def location(self, obj):
        return reverse('news_detail', args=[obj.id])