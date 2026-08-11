from django.contrib import admin
from .models import team, stadium
from .models import teams, match
from .models import Standing





admin.site.register(team)
admin.site.register(stadium)
admin.site.register(teams)
admin.site.register(match)
admin.site.register(Standing)






