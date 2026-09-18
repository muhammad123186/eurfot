from .views import countries, LEAGUES


def sidebar_context(request):
    return {
        'countries': countries,
        'competitions': LEAGUES,
    }

    