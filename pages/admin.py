from django.contrib import admin
from .models import team, stadium
from .models import teams, match
from .models import Standing
from .models import NewsArticle

admin.site.register(team)
admin.site.register(stadium)
admin.site.register(teams)
admin.site.register(match)
admin.site.register(Standing)


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "league_code", "team_id", "published_at")
    list_filter = ("league_code",)
    search_fields = ("title", "content")
    ordering = ("-published_at",)





