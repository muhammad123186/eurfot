from django.contrib.sitemaps import Sitemap
from django.urls import reverse

# 1. خريطة الصفحات الثابتة والرئيسية
class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return [
            'matches',              # الرئيسية ومباريات اليوم (today_matches.html / index.html)
            'premier_league_home',  # الدوري الإنجليزي الممتاز (premier_leauge.html)
            'standings',            # الترتيب العام (standings.html / standings_eur.html)
            'search',               # البحث (search.html)
            'leaderboard',          # لائحة المتصدرين (leaderboard.html)
            'news_list',            # الأخبار (news_list.html)
            'profile',              # الملف الشخصي (profile.html)
            'signup',               # إنشاء حساب (signup.html)
            'login',                # تسجيل الدخول (login.html)
        ]

    def location(self, item):
        return reverse(item)

# 2. خريطة صفحات الدوريات الخمس الكبرى والمسابقات الديناميكية
class CompetitionSitemap(Sitemap):
    priority = 0.9
    changefreq = 'daily'

    def items(self):
        # رموز المسابقات والدوريات (إسبانيا، إيطاليا، ألمانيا، فرنسا، الأبطال)
        return ['PD', 'SA', 'BL1', 'FL1', 'CL']

    def location(self, item):
        return reverse('competition', args=[item])