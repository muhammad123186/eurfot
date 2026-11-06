from pitchapi import PitchAPI

with PitchAPI() as client:

    print("=== الدوريات المتاحة ===")
    leagues = client.leagues.list()
    print(leagues)

    print()
    print("=== مباريات 2026-11-01 ===")
    day = client.date.get("2026-11-01")
    for m in day.matches[:10]:
        print(m.id, "|", m.home_team.name, m.score_home, "-", m.score_away, m.away_team.name)

    if day.matches:
        mid = day.matches[0].id
        print()
        print("=== إحصائيات متقدمة للمباراة", mid, "===")
        try:
            print(client.matches.advanced(mid))
        except Exception as e:
            print("FAIL:", type(e).__name__, getattr(e, "code", ""))