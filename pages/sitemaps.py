from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        # أسماء الـ name الموجودة في ملف urls.py للصفحات التي تريد أرشفتها
        return ['matches', 'standings', 'news_list', 'leaderboard']

    def location(self, item):
        return reverse(item)